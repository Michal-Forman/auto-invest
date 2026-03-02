# Standard library
from datetime import datetime
from typing import Dict, List
from uuid import UUID

# Local
from coinmate import Coinmate
from db.orders import Currency, Order
from instrument_data import (INSTRUMENT_CURRENCIES, INSTRUMENT_NAMES,
                             INSTRUMENT_TYPES, T212_TO_YF)
# Local
from instruments import Instruments
from log import log
from settings import PortfolioSettings, settings
from trading212 import Trading212


class Executor: 
    def __init__(self, t212: Trading212, coinmate: Coinmate, portfolio_settings: PortfolioSettings) -> None:
        self.t212 = t212
        self.coinmate = coinmate
        self.portfolio_settings = portfolio_settings

    def _place_btc_order(self, amount: float, multiplier: float, run_id: UUID) -> Order:
        """Place a market order to buy BTC on Coinmate for the specified amount in CZK."""
        amount = round(amount, 2)  # Coinmate requires amounts to have at most 2 decimal places
        # Place the order on Coinmate
        response_data = self.coinmate.buy_instant(amount, "BTC_CZK")
        req = response_data.get("req")
        res = response_data.get("res")
        err = response_data.get("err")

        if res and res["error"] == False:
            status = "SUBMITTED"
        else:
            status = "FAILED"

        # Write the order in database
        order = Order(
            run_id=run_id,
            exchange="COINMATE",
            instrument_type="CRYPTO",
            t212_ticker="BTC",
            yahoo_symbol=T212_TO_YF["BTC"],
            name=INSTRUMENT_NAMES["BTC"],
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
            error=err,
            multiplier=multiplier,
            fx_rate=1
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

        return order


    def _place_t212_order(self, ticker: str, amount: float, multiplier: float, run_id: UUID)  -> Order:
        """Place a market order to buy the specified ticker on Trading212 for the specified amount in CZK."""
        instrument_currency: Currency = INSTRUMENT_CURRENCIES[ticker]
        if not instrument_currency:
            raise ValueError(f"Unknown currency for ticker {ticker}")
        fx_rate = 1 / Instruments.get_fx_rate_to_czk(instrument_currency)
        amount_in_correct_currency: float = amount * fx_rate 

        current_price = Instruments.get_current_price(ticker)
        amount_in_shares = amount_in_correct_currency / current_price

        # Place the order
        response_data = self.t212.equity_order_place_market(ticker, round(amount_in_shares, 3))
        req = response_data.get("req")
        res = response_data.get("res")
        error = response_data.get("err")

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
            run_id=run_id,
            exchange="T212",
            instrument_type=INSTRUMENT_TYPES[ticker],
            t212_ticker=ticker,
            yahoo_symbol=T212_TO_YF[ticker],
            name=INSTRUMENT_NAMES[ticker],
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
            multiplier=multiplier,
            fx_rate=fx_rate
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

        return order

    def place_orders(self, cash_distribution: Dict[str, float], multipliers: Dict[str, float], run_id: UUID) -> List[Order]:
        """Place orders for each instrument according to the provided cash distribution"""
        orders: List[Order] = []

        for ticker, amount in cash_distribution.items():
            multiplier = multipliers[ticker]
            if ticker == "BTC":
                order = self._place_btc_order(amount, multiplier, run_id)
                orders.append(order)
            else:
                order = self._place_t212_order(ticker, amount, multiplier, run_id)
                orders.append(order)

        log.info("All orders placed successfully")

        return orders



if __name__ == "__main__":
# Standard library
    from uuid import uuid4

# Local
    from instruments import Instruments
    from settings import settings

    run_id = uuid4()

    t212 = Trading212(api_id_key=settings.t212_id_key, api_private_key=settings.t212_private_key, demo=False)
    coinmate = Coinmate(settings.coinmate_client_id, settings.coinmate_public_key, settings.coinmate_private_key)
    instruments = Instruments(t212=t212, portfolio_settings=settings.portfolio)
    executor = Executor(t212, coinmate, settings.portfolio)

    executor._place_t212_order("VWCEd_EQ", 25.0, 2.5, run_id=run_id)
    # executor._place_btc_order(11, 1.5, run_id) # Fails if its less than 50

    # cash_distribution = instruments.distribute_cash()
    # executor.place_orders(cash_distribution)
    



