# Standard library
from datetime import datetime, timezone
from typing import Dict, List

# Local
from coinmate import Coinmate
from db.orders import Order
from db.runs import Run, RunUpdate
from executor import Executor
from instruments import Instruments
from log import log
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

    except Exception as e:
        log.error(f"Investment run failed: {e}")
        try:
            run.update_in_db(RunUpdate(status="FAILED", error=str(e)))
        except Exception as db_err:
            log.error(f"Also failed to mark run as FAILED in DB: {db_err}")
else:
    log.info("No investments / orders were supposed to be made in this run")
