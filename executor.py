from trading212 import Trading212
from coinmate import Coinmate
from settings import PortfolioSettings
from instruments import Instruments
from instrument_data import INSTRUMENT_CURRENCIES

from typing import Dict



class Executor: 
    def __init__(self, t212: Trading212, coinmate: Coinmate, portfolio_settings: PortfolioSettings) -> None:
        self.t212 = t212
        self.coinmate = coinmate
        self.portfolio_settings = portfolio_settings

    def _place_btc_order(self, amount: float):
        """Place a market order to buy BTC on Coinmate for the specified amount in CZK."""
        amount = round(amount, 2)  # Coinmate requires amounts to have at most 2 decimal places
        # Place the order on Coinmate
        self.coinmate.buy_instant(amount, "BTC_CZK")

    def _place_t212_order(self, ticker: str, amount: float):
        """Place a market order to buy the specified ticker on Trading212 for the specified amount in CZK."""
        instrument_currency: str = INSTRUMENT_CURRENCIES[ticker]
        if not instrument_currency:
            raise ValueError(f"Unknown currency for ticker {ticker}")
        amount_in_correct_currency: float = amount / Instruments.get_fx_rate_to_czk(instrument_currency)

        current_price = Instruments.get_current_price(ticker)
        amount_in_shares = amount_in_correct_currency / current_price

        # Place the order
        self.t212.equity_order_place_market(ticker, round(amount_in_shares, 3))



    def place_orders(self, cash_distribution: Dict[str, float]) -> None:
        """Place orders for each instrument according to the provided cash distribution"""
        for ticker, amount in cash_distribution.items():
            if ticker == "BTC":
                self._place_btc_order(amount)
            else:
                self._place_t212_order(ticker, amount)



if __name__ == "__main__":
    from settings import settings
    from instruments import Instruments

    t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
    coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
    instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
    executor = Executor(t212, coinmate, settings.portfolio)

    # executor._place_t212_order("VWCEd_EQ", 100.0)

    # cash_distribution = instruments.distribute_cash()
    # executor.place_orders(cash_distribution)

    executor._place_btc_order(100.0)


