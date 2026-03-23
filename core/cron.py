# Standard library
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Local
from core.coinmate import Coinmate
from core.db.mails import Mail
from core.db.orders import Order
from core.db.runs import Run, RunUpdate
from core.db.users import UserRecord
from core.executor import Executor
from core.instruments import Instruments
from core.log import log
from core.mailer import Mailer
from core.settings import UserSettings
from core.trading212 import Trading212
from core.utils import find_balance_exhaustion_date, is_now_cron_time


def run_for_user(user: UserRecord) -> None:
    """Run one full investment cycle for a single user."""
    user_settings: UserSettings = UserSettings.from_user(user)
    user_id: str = user.id

    log.info(f"Starting run for user {user_id}")
    run_start: datetime = datetime.now(timezone.utc)

    # ----- Initialization -----
    t212: Trading212 = Trading212(
        api_id_key=user_settings.t212_id_key,
        api_private_key=user_settings.t212_private_key,
        env=user_settings.env,
    )
    coinmate: Coinmate = Coinmate(
        user_settings.coinmate_client_id or 0,
        user_settings.coinmate_public_key,
        user_settings.coinmate_private_key,
    )
    instruments: Instruments = Instruments(
        t212=t212, coinmate=coinmate, portfolio_settings=user_settings.portfolio
    )
    executor: Executor = Executor(
        t212,
        coinmate,
        btc_external_adress=user_settings.btc_external_adress,
        user_id=user_id,
    )
    mailer: Optional[Mailer] = (
        Mailer(user_settings) if user.notifications_enabled else None
    )

    # --- Check if BTC-Withdrawal should be made and if so, make one
    try:
        btc_threshold_exceeded = instruments.is_btc_withdrawal_treshold_exceeded()
    except Exception as e:
        log.error(f"Failed to check BTC balance threshold for {user_id}: {e}")
        if mailer:
            mailer.send_error_alert(e)
        btc_threshold_exceeded = False

    if btc_threshold_exceeded:
        try:
            withdrawal = executor.withdraw_btc()
            if mailer:
                mailer.send_btc_withdrawal_confirmation(withdrawal)
        except Exception as e:
            log.error(f"Failed to withdraw BTC for {user_id}: {e}")
            if mailer:
                mailer.send_error_alert(e)
    else:
        log.info("No BTC Withdrawal should take place")

    # --- Update old investment data in db ---
    log.info("Start updating old Orders and Runs")
    Order.update_orders(t212, coinmate, user_id=user_id)
    Run.update_runs(user_id=user_id)
    log.info("Finished updating old Orders and Runs")

    # --- Check balances and alert if running low ---
    if not Mail.balance_alert_sent_today(user_id=user_id):
        try:
            adjusted_ratios = instruments.get_adjusted_ratios()
            total_adj = sum(v["adjusted_value"] for v in adjusted_ratios.values())
            t212_adj = sum(
                v["adjusted_value"] for k, v in adjusted_ratios.items() if k != "BTC"
            )
            btc_adj = adjusted_ratios.get("BTC", {}).get("adjusted_value", 0.0)
            invest = user_settings.portfolio.invest_amount
            cron = user_settings.portfolio.invest_interval

            BUFFER: float = user_settings.portfolio.balance_buffer
            ALERT_DAYS: int = user_settings.portfolio.balance_alert_days

            alerts: List[Dict[str, Any]] = []
            for exchange, adj, get_bal in [
                ("T212", t212_adj, t212.balance),
                ("COINMATE", btc_adj, coinmate.balance),
            ]:
                spend_per_run = (adj / total_adj) * invest
                bal = get_bal()
                runs_out_on = find_balance_exhaustion_date(
                    cron, spend_per_run, bal, BUFFER
                )
                if runs_out_on and (runs_out_on - run_start).days <= ALERT_DAYS:
                    alerts.append(
                        {
                            "exchange": exchange,
                            "balance": bal,
                            "spend_per_run": spend_per_run,
                            "runs_out_on": runs_out_on,
                            "days_until_broke": (runs_out_on - run_start).days,
                        }
                    )

            if alerts and mailer:
                mailer.send_balance_alert(alerts)
        except Exception as e:
            log.warning(f"Balance check skipped (non-critical): {e}")

    # --- Create new orders if they should be made today AND they have not yet been ---
    if is_now_cron_time(
        user_settings.portfolio.invest_interval
    ) and not Run.run_exists_today(user_id=user_id):
        log.info("Starting investment process")

        run: Run = Run.create_run(run_start, user_settings.portfolio, user_id=user_id)
        assert run.id is not None

        try:
            calculated_investment: Dict[str, Dict[str, float]] = (
                instruments.distribute_cash()
            )
            cash_distribution: Dict[str, float] = calculated_investment[
                "cash_distribution"
            ]
            multipliers: Dict[str, float] = calculated_investment["multipliers"]
            orders: List[Order] = executor.place_orders(
                cash_distribution, multipliers, run_id=run.id, investment_type="dca"
            )
            log.info("Investment process finished")

            run_data_for_update: RunUpdate = Run.process_new_run_data(orders)
            run.update_in_db(run_data_for_update)
            log.info("Run data updated successfully")

            if mailer:
                mailer.send_investment_confirmation(
                    run, orders, cash_distribution, multipliers
                )

        except Exception as e:
            log.error(f"Investment run failed for {user_id}: {e}")
            if mailer:
                mailer.send_error_alert(e, run)
            try:
                run.update_in_db(RunUpdate(status="FAILED", error=str(e)))
            except Exception as db_err:
                log.error(
                    f"Also failed to mark run as FAILED in DB for {user_id}: {db_err}"
                )
    else:
        log.info("No investments / orders were supposed to be made in this run")

    # --- Send monthly summary for the previous month if not yet sent ---
    prev_year = run_start.year if run_start.month > 1 else run_start.year - 1
    prev_month = run_start.month - 1 if run_start.month > 1 else 12
    period = f"{prev_year}-{prev_month:02d}"
    if not Mail.summary_sent_for_period(period, user_id=user_id):
        try:
            last_month_runs: List[Run] = Run.get_runs_for_period(
                prev_year, prev_month, user_id=user_id
            )
            last_month_failed_runs: List[Run] = Run.get_failed_runs_for_period(
                prev_year, prev_month, user_id=user_id
            )
            if last_month_runs or last_month_failed_runs:
                run_ids: List[str] = [str(r.id) for r in last_month_runs]
                last_month_orders: List[Order] = Order.get_orders_for_runs(
                    run_ids, user_id=user_id
                )
                if mailer:
                    mailer.send_monthly_summary(
                        last_month_runs, last_month_orders, last_month_failed_runs
                    )
        except Exception as e:
            log.error(f"Failed to send monthly summary for {user_id}: {e}")
            if mailer:
                mailer.send_error_alert(e)


def main() -> None:
    """Run investment cycle for all cron-enabled users."""
    log.info("Starting Main script")
    users: List[UserRecord] = UserRecord.get_cron_users()
    log.info(f"Found {len(users)} cron-enabled user(s)")

    for user in users:
        try:
            run_for_user(user)
        except Exception as e:
            log.error(f"Cron failed for user {user.id}: {e}")

    log.info("Main script finished")


if __name__ == "__main__":
    main()
