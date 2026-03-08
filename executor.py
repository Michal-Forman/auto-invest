# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

# Local
from coinmate import Coinmate
from db.orders import Currency, Order, Status
from db.btc_withdrawals import BtcWithdrawal
from instrument_data import (
    INSTRUMENT_CURRENCIES,
    INSTRUMENT_NAMES,
    INSTRUMENT_TYPES,
    T212_TO_YF,
)
from instruments import Instruments
from log import log
from settings import settings
from trading212 import Trading212


class Executor:
    def __init__(
        self,
        t212: Trading212,
        coinmate: Coinmate,
    ) -> None:
        """Initialize with Trading212 and Coinmate clients plus portfolio configuration."""
        self.t212 = t212
        self.coinmate = coinmate

    def _place_btc_order(self, amount: float, multiplier: float, run_id: UUID) -> Order:
        """Place an instant BTC buy on Coinmate for the given CZK amount, persist the Order to DB, and return it."""
        amount = round(
            amount, 2
        )  # Coinmate requires amounts to have at most 2 decimal places
        # Place the order on Coinmate
        response_data: Dict[str, Any] = self.coinmate.buy_instant(amount, "BTC_CZK")
        req: Any = response_data.get("req")
        res: Any = response_data.get("res")
        err: Any = response_data.get("err")

        status: Status
        if res and res.get("error") is False:
            status = "SUBMITTED"
        else:
            status = "FAILED"

        btc_price = Instruments.get_btc_price()

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
            price=btc_price,
            quantity=round(amount / btc_price, 8),
            total=round(amount, 2),
            total_czk=round(amount, 2),
            extended_hours=False,
            submitted_at=datetime.now(timezone.utc),
            status=status,
            external_order_id=str(res.get("data")) if res else None,
            request=req,
            response=res,
            error=str(err) if err else None,
            multiplier=multiplier,
            fx_rate=1,
        )

        try:
            inserted: Optional[Dict[str, Any]] = order.post_to_db()
            if inserted:
                log.info("BTC order recorded in database")
            else:
                log.warning("BTC order already exists in DB (idempotency key matched)")
        except Exception as e:
            log.error(f"Failed to insert BTC order into database: {e}")

        return order

    def _place_t212_order(
        self, ticker: str, amount: float, multiplier: float, run_id: UUID
    ) -> Order:
        """Place a T212 market buy for the given CZK amount (converted to the instrument's currency), persist the Order to DB, and return it."""
        instrument_currency: Currency = INSTRUMENT_CURRENCIES[ticker]
        if not instrument_currency:
            raise ValueError(f"Unknown currency for ticker {ticker}")
        fx_rate = Instruments.get_fx_rate_to_czk(instrument_currency)
        amount_in_correct_currency: float = amount / fx_rate

        current_price: float = Instruments.get_current_price(ticker)
        amount_in_shares = amount_in_correct_currency / current_price

        # Place the order
        response_data: Dict[str, Any] = self.t212.equity_order_place_market(
            ticker, round(amount_in_shares, 3)
        )
        req: Any = response_data.get("req")
        res: Any = response_data.get("res")
        error: Any = response_data.get("err")

        status: Status
        if res is not None:
            filled_qty = res.get("filledQuantity", 0)
            quantity = res.get("quantity", 0)
            if filled_qty == quantity:
                status = "FILLED"
            elif filled_qty > 0:
                status = "PARTIALLY_FILLED"
            elif filled_qty == 0:
                status = "SUBMITTED"
            else:
                status = "UNKNOWN"
                log.warning(
                    f"Unexpected filledQuantity value for {ticker}: {filled_qty}"
                )
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
            submitted_at=datetime.now(timezone.utc),
            request=req,
            response=res,
            error=str(error),
            external_order_id=str(res.get("id")) if res else None,
            filled_quantity=res.get("filledQuantity") if res else None,
            multiplier=multiplier,
            fx_rate=fx_rate,
        )

        try:
            inserted: Optional[Dict[str, Any]] = order.post_to_db()
            if inserted:
                log.info(f"{ticker} order recorded in database")
            else:
                log.warning(
                    f"{ticker} order already exists in DB (idempotency key matched)"
                )
        except Exception as e:
            log.error(f"Failed to insert {ticker} order into database: {e}")

        return order

    def place_orders(
        self,
        cash_distribution: Dict[str, float],
        multipliers: Dict[str, float],
        run_id: UUID,
    ) -> List[Order]:
        """Place a buy order for every instrument in the cash distribution. Routes BTC to Coinmate and everything else to T212."""
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

    def withdraw_btc(self) -> Optional[BtcWithdrawal]:
        """Withdraw the full BTC balance to the external wallet and persist the withdrawal record. Returns the persisted BtcWithdrawal or None on failure."""
        try:
            btc_balance: float = self.coinmate.btc_balance()
            transaction_data: Dict[str, Any] = self.coinmate.btc_withdraw(
                btc_adress=settings.btc_external_adress, amount=btc_balance
            )
            btc_price = Instruments.get_btc_price()
            actual_amount = float(transaction_data["amount"])
            amount_czk = Decimal(str(round(actual_amount * btc_price, 2)))
            return BtcWithdrawal.create_withdrawal(withdrawal_data=transaction_data, amount_czk=amount_czk)
        except Exception as e:
            log.error(f"Failed to withdraw BTC: {e}")
            return None
