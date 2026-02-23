
from trading212 import Trading212
from settings import settings
from utils import generate_uuid
from instruments import Instruments
from executor import Executor
from coinmate import Coinmate
from log import log


#----- Initialization -----

t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
executor = Executor(t212, coinmate, settings.portfolio)

#----- Main program logic -----

log.info("Starting auto-investment process")

run_id: str = generate_uuid()

cash_distribution = instruments.distribute_cash()
executor.place_orders(cash_distribution, run_id)

log.info("Auto-investment process completed successfully")

