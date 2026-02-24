from trading212 import Trading212
from coinmate import Coinmate
from settings import PortfolioSettings
from instruments import Instruments
from instrument_data import INSTRUMENT_CURRENCIES, INSTRUMENT_TYPES, T212_TO_YF
from log import log
from db.orders import Order, Currency
from datetime import datetime

from typing import Dict



class Executor: 
    def __init__(self, t212: Trading212, coinmate: Coinmate, portfolio_settings: PortfolioSettings) -> None:
        self.t212 = t212
        self.coinmate = coinmate
        self.portfolio_settings = portfolio_settings

    def _place_btc_order(self, amount: float) -> None:
        """Place a market order to buy BTC on Coinmate for the specified amount in CZK."""
        amount = round(amount, 2)  # Coinmate requires amounts to have at most 2 decimal places
        # Place the order on Coinmate
        response_data = self.coinmate.buy_instant(amount, "BTC_CZK")
        req = response_data.get("req")
        res = response_data.get("res")
        err = response_data.get("err")

        print(f"Response data: req: {req} res {res} err {err} End of response data")

        if res and res["error"] == False:
            status = "SUBMITTED"
        else:
            status = "FAILED"

        # Write the order in database
        order = Order(
            run_id=settings.run_id,
            exchange="COINMATE",
            instrument_type="CRYPTO",
            t212_ticker="BTC",
            yahoo_symbol=T212_TO_YF["BTC"],
            currency="CZK",
            side="BUY",
            order_type="INSTANT",
            price=Instruments.get_btc_price(),
            quantity= round(amount / Instruments.get_btc_price(), 8),
            total=round(amount, 2),
            total_czk=round(amount, 2),
            extended_hours=False,
            submitted_at=datetime.utcnow(),
            status=status,
            external_order_id=str(res["data"]) if res else None,
            request=req,
            response=res,
            error=err
        )

        try:
            inserted = order.post_to_db()
        except Exception as e:
            log.error(f"Failed to insert order into database: {e}")
            inserted = False


        if inserted:
            log.info(f"Order successfully placed and recorded in database: BTC")
        else:
            log.error("Order already exists (idempotency triggered) or failed to insert")


    def _place_t212_order(self, ticker: str, amount: float)  -> None:
        """Place a market order to buy the specified ticker on Trading212 for the specified amount in CZK."""
        instrument_currency: Currency = INSTRUMENT_CURRENCIES[ticker]
        if not instrument_currency:
            raise ValueError(f"Unknown currency for ticker {ticker}")
        amount_in_correct_currency: float = amount / Instruments.get_fx_rate_to_czk(instrument_currency)

        current_price = Instruments.get_current_price(ticker)
        amount_in_shares = amount_in_correct_currency / current_price

        # Place the order
        response_data = self.t212.equity_order_place_market(ticker, round(amount_in_shares, 3))
        req = response_data.get("req")
        res = response_data.get("res")
        error = response_data.get("err")

        print(res)

        if res is not None:
            if res["filledQuantity"] == res["quantity"]:
                status = "FILLED"
            elif res["filledQuantity"] > 0:
                status = "PARTIALLY_FILLED"
            elif res["filledQuantity"] == 0:
                status = "SUBMITTED"
            else:
                status = "UNKNOWN"
                log.warning(f"Can't get order status for some reason. Not a big runtime risk, but it's not good")
        else:
            status = "FAILED"


        # Write the order in database
        order = Order(
            run_id=settings.run_id,
            exchange="T212",
            instrument_type=INSTRUMENT_TYPES[ticker],
            t212_ticker=ticker,
            yahoo_symbol=T212_TO_YF[ticker],
            currency=instrument_currency,
            side="BUY",
            order_type="MARKET",
            price=current_price,
            quantity=round(amount_in_shares, 8),
            total=round(amount_in_correct_currency, 2),
            total_czk=round(amount, 2),
            extended_hours=res.get("extendedHours") if res else False,
            status=status,
            submitted_at=datetime.utcnow(),
            request=req,
            response=res,
            error=str(error),
            external_order_id=str(res.get("id")) if res else None,
            filled_quantity=res.get("filledQuantity") if res else None,
        )

        try:
            inserted = order.post_to_db()
        except Exception as e:
            log.error(f"Failed to insert order into database: {e}")
            inserted = False


        if inserted:
            log.info(f"Order successfully placed and recorded in database: {ticker}")
        else:
            log.error("Order already exists (idempotency triggered) or failed to insert")

    def place_orders(self, cash_distribution: Dict[str, float]) -> None:
        """Place orders for each instrument according to the provided cash distribution"""
        for ticker, amount in cash_distribution.items():
            if ticker == "BTC":
                self._place_btc_order(amount)
            else:
                self._place_t212_order(ticker, amount)
        log.info("All orders placed successfully")



if __name__ == "__main__":
    from settings import settings
    from instruments import Instruments

    t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
    coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
    instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
    executor = Executor(t212, coinmate, settings.portfolio)

    # executor._place_t212_order("VWCEd_EQ", 25.0)
    # executor._place_btc_order(21) # Fails if its less than 50

    # cash_distribution = instruments.distribute_cash()
    # executor.place_orders(cash_distribution)



