# Standard library
from datetime import datetime, timezone
from typing import Dict, List

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
from utils import is_now_cron_time

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
instruments: Instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
executor: Executor = Executor(t212, coinmate, settings.portfolio)
mailer: Mailer = Mailer()

# ----- Main program logic -----

# Update values in db based on current state - Do as often as possible = on every script run
log.info("Start updating old Orders and Runs")
Order.update_orders(t212, coinmate)
Run.update_runs()
log.info("Finished updating old Orders and Runs")

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
    if last_month_runs:
        run_ids: List[str] = [str(r.id) for r in last_month_runs]
        last_month_orders: List[Order] = Order.get_orders_for_runs(run_ids)
        mailer.send_monthly_summary(last_month_runs, last_month_orders)
