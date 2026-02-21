
from trading212 import Trading212
from settings import settings, portfolio_settings
from instruments import Instruments


t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
instruments = Instruments(t212=t212, portfolio_settings=portfolio_settings)

# print(instruments.get_default_ratios())
print(instruments.get_t212_ratios())

# portfolio = t212_client.portfolio()
# print(t212.pie(3857693))




