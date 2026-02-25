
from trading212 import Trading212
from settings import settings
from utils import generate_uuid
from instruments import Instruments
from executor import Executor
from coinmate import Coinmate
from log import log
from typing import Dict


#----- Initialization -----

t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
executor = Executor(t212, coinmate, settings.portfolio)

#----- Main program logic -----

log.info("Starting auto-investment process")

calculated_investment: Dict[str, Dict[str, float]] = instruments.distribute_cash()
cash_distribution = calculated_investment["cash_distribution"]
multipliers = calculated_investment["multipliers"]
print(f"CAHS_DISTRIBUTION: {cash_distribution}, MULTIPLIERS: {multipliers}")
executor.place_orders(cash_distribution, multipliers)

log.info("Auto-investment process completed successfully")

