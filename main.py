
from trading212 import Trading212
from settings import settings
from instruments import Instruments
from executor import Executor
from coinmate import Coinmate
from log import log
from typing import Dict, List
from db.runs import Run, RunUpdate
from db.orders import Order
from utils import is_now_cron_time
from datetime import datetime


#----- Start counting time for a run -----
run_start = datetime.utcnow()

#----- Initialization -----

t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
executor = Executor(t212, coinmate, settings.portfolio)

#----- Main program logic -----

# Update values in db based on current state - Do as often as possible = on every script run
Order.update_orders(t212, coinmate)
Run.update_runs()

# Create new orders
if is_now_cron_time(settings.portfolio.invest_interval):

    # Init new run
    run = Run.create_run(run_start)
    assert run.id is not None

    # Actually create the orders
    calculated_investment: Dict[str, Dict[str, float]] = instruments.distribute_cash()
    cash_distribution = calculated_investment["cash_distribution"]
    multipliers = calculated_investment["multipliers"]
    orders: List[Order] = executor.place_orders(cash_distribution, multipliers, run_id=run.id)

    # Update the run data with info about the orders
    run_data_for_update: RunUpdate = run.process_new_run_data(orders)
    try:
        run.update_in_db(run_data_for_update)
    except Exception as e:
        log.error(f"Failed to update the db, error: {e}")



