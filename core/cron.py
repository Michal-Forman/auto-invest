# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

# Local
from core.coinmate import Coinmate
from core.db.mails import Mail
from core.db.orders import Order
from core.db.runs import Run, RunUpdate
from core.db.users import UserRecord
from core.executor import Executor
from core.funding import (
    ExchangeFunding,
    InsufficientFundsError,
    funding_status,
    should_send_alert,
    should_send_recovery,
)
from core.instruments import Instruments
from core.log import log
from core.mailer import Mailer
from core.precision import to_decimal
from core.settings import UserSettings
from core.trading212 import Trading212
from core.utils import is_now_cron_time, runs_in_next_days


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

    investing_today: bool = is_now_cron_time(
        user_settings.portfolio.invest_interval
    ) and not Run.run_exists_today(user_id=user_id)

    # --- Warn ahead of time if an exchange cannot cover the next run ---
    # Skipped on investment days: the run itself reports the authoritative outcome,
    # so this would only duplicate it.
    if not investing_today:
        try:
            upcoming: Dict[str, Decimal] = instruments.distribute_cash()[
                "cash_distribution"
            ]
            # Warn on the user's wide buffer over their alert window, well before the
            # tight EXECUTION_MARGIN gate would actually abort a run.
            statuses: List[ExchangeFunding] = funding_status(
                upcoming,
                t212,
                coinmate,
                runs=runs_in_next_days(
                    user_settings.portfolio.invest_interval,
                    user_settings.portfolio.balance_alert_days,
                ),
                margin=to_decimal(user_settings.portfolio.balance_buffer),
            )
            short: List[ExchangeFunding] = [f for f in statuses if f.is_short]
            short_exchanges = {f.exchange for f in short}

            last_alert: Optional[Mail] = Mail.last_balance_alert(user_id=user_id)
            last_exchanges = Mail.parse_alert_period(
                last_alert.period if last_alert else None
            )
            last_sent_at = last_alert.sent_at if last_alert else None

            if mailer and should_send_alert(
                short_exchanges, last_sent_at, last_exchanges, run_start
            ):
                log.warning(f"Funds short on {', '.join(sorted(short_exchanges))}")
                mailer.send_funding_alert(short, event="low")
            elif mailer and should_send_recovery(short_exchanges, last_exchanges):
                log.info("Funding recovered on all exchanges")
                mailer.send_funding_alert(statuses, event="recovered")
        except Exception as e:
            log.warning(f"Funding check skipped (non-critical): {e}")

    # --- Create new orders if they should be made today AND they have not yet been ---
    if investing_today:
        log.info("Starting investment process")

        run: Optional[Run] = None
        try:
            run = Run.create_run(run_start, user_settings.portfolio, user_id=user_id)
            assert run.id is not None

            calculated_investment: Dict[str, Dict[str, Decimal]] = (
                instruments.distribute_cash()
            )
            cash_distribution: Dict[str, Decimal] = calculated_investment[
                "cash_distribution"
            ]
            multipliers: Dict[str, Decimal] = calculated_investment["multipliers"]

            # Nothing is placed unless every exchange can cover its whole share, so a
            # run never ends up half-invested with the tail orders rejected.
            underfunded: List[ExchangeFunding] = [
                f
                for f in funding_status(cash_distribution, t212, coinmate)
                if f.is_short
            ]
            if underfunded:
                raise InsufficientFundsError(underfunded)

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

        except InsufficientFundsError as e:
            log.error(f"Investment skipped for {user_id}: {e}")
            if run is not None:
                run.update_in_db(
                    RunUpdate(
                        status="FAILED",
                        error=str(e),
                        finished_at=datetime.now(timezone.utc),
                        planned_total_czk=sum(cash_distribution.values(), Decimal("0")),
                        distribution=dict(cash_distribution),
                    )
                )
            if mailer:
                mailer.send_funding_alert(e.shortfalls, event="skipped")

        except Exception as e:
            log.error(f"Investment run failed for {user_id}: {e}")
            if mailer:
                mailer.send_error_alert(e, run)
            if run is not None:
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
