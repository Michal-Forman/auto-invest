# Standard library
from datetime import datetime, timezone
from typing import Any, Dict, List

# Local
from coinmate import Coinmate
from db.mails import Mail
from db.orders import Order
from db.runs import Run, RunUpdate
from executor import Executor
from instruments import Instruments
from log import log
from mailer import Mailer
from settings import settings
from trading212 import Trading212
from utils import find_balance_exhaustion_date, is_now_cron_time

# ----- Start counting time for a run -----
log.info("Starting Main script")
run_start: datetime = datetime.now(timezone.utc)

# ----- Initialization -----

log.info("Initializing all classes")
t212: Trading212 = Trading212(
    api_id_key=settings.t212_id_key,
    api_private_key=settings.t212_private_key,
    env=settings.env,
)
coinmate: Coinmate = Coinmate(
    settings.coinmate_client_id,
    settings.coinmate_public_key,
    settings.coinmate_private_key,
)
instruments: Instruments = Instruments(t212=t212, coinmate=coinmate, portfolio_settings=settings.portfolio)
executor: Executor = Executor(t212, coinmate, settings.portfolio)
mailer: Mailer = Mailer()

# --- Check if BTC-Withdrawal should be made and if so, make one

try:
    if instruments.is_btc_withdrawal_treshold_exceeded():
        print("it is exceeded")
        pass
    else:
        print("it is not")
        pass
except Exception as e:
    log.error(f"Failed to get the state of BTC balance on coinmate: {e}")

# --- Upate old investment data in db ---
log.info("Start updating old Orders and Runs")
Order.update_orders(t212, coinmate)
Run.update_runs()
log.info("Finished updating old Orders and Runs")

# --- Check balances and alert if running low ---
if not Mail.balance_alert_sent_today():
    try:
        adjusted_ratios = instruments.get_adjusted_ratios()
        total_adj = sum(v["adjusted_value"] for v in adjusted_ratios.values())
        t212_adj = sum(
            v["adjusted_value"] for k, v in adjusted_ratios.items() if k != "BTC"
        )
        btc_adj = adjusted_ratios.get("BTC", {}).get("adjusted_value", 0.0)
        invest = settings.portfolio.invest_amount
        cron = settings.portfolio.invest_interval

        BUFFER: float = settings.portfolio.balance_buffer
        ALERT_DAYS: int = settings.portfolio.balance_alert_days

        alerts: List[Dict[str, Any]] = []
        for exchange, adj, get_bal in [
            ("T212", t212_adj, t212.balance),
            ("COINMATE", btc_adj, coinmate.balance),
        ]:
            spend_per_run = (adj / total_adj) * invest
            bal = get_bal()
            runs_out_on = find_balance_exhaustion_date(cron, spend_per_run, bal, BUFFER)
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

        if alerts:
            mailer.send_balance_alert(alerts)
    except Exception as e:
        log.warning(f"Balance check skipped (non-critical): {e}")

# Create new orders if they should be made today AND they have not yet been
if is_now_cron_time(settings.portfolio.invest_interval) and not Run.run_exists_today():
    log.info("Starting investment process")

    # Init new run
    run: Run = Run.create_run(run_start)
    assert run.id is not None

    try:
        # Actually create the orders
        calculated_investment: Dict[str, Dict[str, float]] = (
            instruments.distribute_cash()
        )
        cash_distribution: Dict[str, float] = calculated_investment["cash_distribution"]
        multipliers: Dict[str, float] = calculated_investment["multipliers"]
        orders: List[Order] = executor.place_orders(
            cash_distribution, multipliers, run_id=run.id
        )
        log.info("Investment process finished")

        # Update the run data with info about the orders
        run_data_for_update: RunUpdate = Run.process_new_run_data(orders)
        run.update_in_db(run_data_for_update)
        log.info("Run data updated successfully")

        # Send investment confirmation email
        mailer.send_investment_confirmation(run, orders, cash_distribution, multipliers)

    except Exception as e:
        log.error(f"Investment run failed: {e}")
        mailer.send_error_alert(e, run)
        try:
            run.update_in_db(RunUpdate(status="FAILED", error=str(e)))
        except Exception as db_err:
            log.error(f"Also failed to mark run as FAILED in DB: {db_err}")
else:
    log.info("No investments / orders were supposed to be made in this run")

# Send monthly summary for the previous month if not yet sent
prev_year = run_start.year if run_start.month > 1 else run_start.year - 1
prev_month = run_start.month - 1 if run_start.month > 1 else 12
period = f"{prev_year}-{prev_month:02d}"
if not Mail.summary_sent_for_period(period):
    last_month_runs: List[Run] = Run.get_runs_for_period(prev_year, prev_month)
    last_month_failed_runs: List[Run] = Run.get_failed_runs_for_period(
        prev_year, prev_month
    )
    if last_month_runs or last_month_failed_runs:
        run_ids: List[str] = [str(r.id) for r in last_month_runs]
        last_month_orders: List[Order] = Order.get_orders_for_runs(run_ids)
        mailer.send_monthly_summary(
            last_month_runs, last_month_orders, last_month_failed_runs
        )
