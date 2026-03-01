from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Literal, Dict, Any, List
from uuid import UUID
from httpx import RequestError
from pydantic import BaseModel, Field, model_validator
from db.client import supabase
from log import log
import hashlib
from trading212 import Trading212
from coinmate import Coinmate

TABLE = "orders"

Currency = Literal["USD", "CZK", "EUR", "GBP", "GBX"]
Side = Literal["BUY", "SELL"]
Exchange = Literal["T212", "COINMATE"]
OrderType = Literal["MARKET", "LIMIT", "INSTANT", "QUICK"]
InstrumentType = Literal["STOCK", "ETF", "CRYPTO"]
Status = Literal[
    "SUBMITTED",
    "FILLED",
    "PARTIALLY_FILLED",
    "CANCELLED",
    "FAILED",
    "UNKNOWN",
]

class OrderUpdate(BaseModel):
    # --- Update ---
    status: Optional[Status] = None

    # --- Create ---
    filled_quantity: Optional[float] = None
    filled_at: Optional[datetime] = None
    filled_total: Optional[float] = None
    filled_total_czk: Optional[float] = None
    fill_fx_rate: Optional[float] = None
    fill_price: Optional[float] = None

    fee_currency: Optional[Currency] = None
    fee: Optional[float] = None
    fee_czk: Optional[float] = None

class Order(BaseModel):
    # --- Identity ---
    id: Optional[UUID] = None
    run_id: UUID
    idempotency_key: Optional[str] = None

    # --- Context ---
    exchange: Exchange
    instrument_type: InstrumentType
    t212_ticker: str
    yahoo_symbol: str
    name: str

    currency: Currency
    side: Side
    order_type: OrderType
    fx_rate: float

    # --- Order values ---
    price: float
    quantity: float
    total: float
    total_czk: float
    limit_price: Optional[float] = None
    extended_hours: bool
    multiplier: float

    # --- State ---
    status: Status = "UNKNOWN"
    external_order_id: Optional[str] = None

    submitted_at: datetime
    filled_at: Optional[datetime] = None

    filled_quantity: Optional[float] = None
    fill_price: Optional[float] = None
    filled_total: Optional[float] = None
    filled_total_czk: Optional[float] = None
    fill_fx_rate: Optional[float] = None

    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    fee_czk: Optional[float] = None

    request: Optional[dict] = None
    response: Optional[dict] = None
    error: Optional[str] = None

    created_at: Optional[datetime] = None

    # -------------------------
    # Logic validation
    # -------------------------

    @model_validator(mode="after")
    def validate_business_rules(self) -> "Order":
        # LIMIT must have limit_price
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("LIMIT order must have limit_price")

        # Generate idempotency_key if not provided (It should not have been)
        if not self.idempotency_key:
            self.idempotency_key = self.generate_idempotency_key()

        # Normalize precision
        self.quantity = round(self.quantity, 8)
        self.total = round(self.total, 2)
        self.total_czk = round(self.total_czk, 2)

        return self

        return self


    # -------------------------
    # Helper methods for DB
    # -------------------------

    def _to_insert_dict(self) -> Dict[str, Any]:
        """
        Připraví dict pro Supabase insert.
        Vyhodí None hodnoty.
        """
        data = self.model_dump(mode="json", exclude_none=True)
        return data

    def post_to_db(self) -> Optional[Dict[str, Any]]:
        """
        Inserts a new order into Supabase.
        Returns inserted row (including generated id).
        Returns None if idempotency_key already exists.
        """

        order_data = self._to_insert_dict()

        response = (
            supabase
            .table(TABLE)
            .insert(order_data)
            .execute()
        )

        # If conflict happens, Supabase returns error
        if response.data:
            return response.data[0]

        return None

    def generate_idempotency_key(self) -> str:
        """
        Generates a unique idempotency key based on order parameters.
        This can be used to ensure that the same order is not created multiple times.
        """

        raw = (
            f"{self.run_id}|"
            f"{self.exchange}|"
            f"{self.instrument_type}|"
            f"{self.t212_ticker}|"
            f"{self.side}|"
            f"{self.order_type}|"
            f"{self.quantity:.5f}|"
            f"{self.total:.2f}|"
            f"{self.limit_price if self.limit_price is not None else ''}|"
        )

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def update_in_db(self, update_data: OrderUpdate) -> Optional[Dict[str, Any]]:
        if not self.id:
            raise ValueError("Cannot update order without id")

        update_fields = update_data.model_dump(mode="json", exclude_none=True)

        response = (
            supabase
            .table(TABLE)
            .update(update_fields)
            .eq("id", str(self.id))
            .execute()
        )

        if response.data:
            log.info("Successfully updated the order in db")
            return response.data[0]

        return None

    @staticmethod
    def get_submitted_orders() -> List[Order]:
        response = (
            supabase
            .table(TABLE)
            .select("*")
            .eq("status", "SUBMITTED")
            .execute()
        )

        if not response.data:
            return []

        return [Order.model_validate(row) for row in response.data]

    @staticmethod
    def _process_new_coinmate_data(order) -> OrderUpdate:
        status = "FILLED" if order["amount"] != 0 else "FAILED"

        ts = order["createdTimestamp"]
        filled_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

        filled_total = order["amount"] * order["price"] - order["fee"]

        return OrderUpdate(
            status=status,
            filled_quantity=order["amount"],
            filled_at=filled_at,
            filled_total=filled_total,
            filled_total_czk=filled_total,
            fill_fx_rate=1.0,
            fill_price=order["price"],
            fee_currency="CZK",
            fee=order["fee"],
            fee_czk=order["fee"],
            
        )

    @classmethod
    def update_orders(cls, t212: Trading212, coinmate: Coinmate):
        orders_to_update: List[Order] = Order.get_submitted_orders()
        coinmate_history_data: Dict[str, Any] = coinmate.user_trades()
        t212_history_data: Dict[str, Any] = t212.orders_page()

        if coinmate_history_data["res"]["error"] is not False:
            raise RequestError("Failed to get coinmate history data")

        if t212_history_data.get("items") == None:
            raise RequestError("Failed to get t212 history data")

        for order in orders_to_update:
            if order.t212_ticker == "BTC":
                orders = coinmate_history_data["res"]["data"]
                matched_order = next(
                    (o for o in orders if str(o["orderId"]) == str(order.external_order_id)),
                    None
                )
                if matched_order:
                    orderUpdate = cls._process_new_coinmate_data(matched_order)
                    try:
                        order.update_in_db(orderUpdate)                       
                    except Exception as e:
                        log.error(e)
                else:
                    log.warning("No matching order found")
                
            else:
                items = t212_history_data["items"]
                matched_item = next(
                    (item for item in items if str(item["order"]["id"]) == str(order.external_order_id)),
                    None
                )
                if matched_item:
                    orderUpdate = cls._process_new_t212_data(matched_item)
                    try:
                        order.update_in_db(orderUpdate)                       
                    except Exception as e:
                        log.error(e)
                else:
                    log.warning("No matching order found")


    @staticmethod
    def _process_new_t212_data(item) -> OrderUpdate:
        order = item.get("order")
        fill = item.get("fill")

        if order["status"] == "CANCELLED":
            status = "CANCELLED"
        elif fill is not None:
            status = "FILLED"
        else:
            status = "SUBMITTED"

        filled_total = order.get("filledValue")
        if filled_total is None:
            filled_total = order.get("walletImpact", {}).get("netValue")

        if fill is not None:
            filled_at=fill.get("filledAt")
            fill_fx_rate= 1 / fill.get("walletImpact").get("fxRate")
            fee = abs(fill.get("walletImpact").get("taxes")[0].get("quantity")) 
            fee_currency= fill.get("walletImpact").get("taxes")[0].get("currency")
            fee_czk = fee if fee_currency == "CZK" else None
            filled_total_czk = fill.get("walletImpact").get("netValue")
            filled_total = filled_total_czk * fill_fx_rate
            fill_price=fill.get("price")
        else:
            filled_at = None
            fill_fx_rate = None
            fee = None
            fee_currency = None
            fee_czk = None
            filled_total_czk = None
            filled_total = None
            fill_price = None


        return OrderUpdate(
            status=status,
            filled_quantity=order["filledQuantity"],
            filled_at=filled_at,
            filled_total=filled_total,
            filled_total_czk=filled_total_czk,
            fill_fx_rate=fill_fx_rate,
            fill_price=fill_price,
            fee_currency=fee_currency,
            fee=fee,
            fee_czk=fee_czk,
        )

if __name__ == "__main__":
    from datetime import datetime
    from uuid import uuid4

    try:
        order = Order(
            run_id="test",
            exchange="T212",
            instrument_type="ETF",
            t212_ticker="CSPX_EQ",
            yahoo_symbol="CSPX.L",
            currency="USD",
            side="BUY",
            order_type="MARKET",
            price=400.0,
            quantity=1.0,
            total=400.0,
            total_czk=9500.0,
            extended_hours=False,
            submitted_at=datetime.utcnow(),
            multiplier=1.0
        )

        print("Creating order in DB...")

        inserted = order.post_to_db()
 
        if inserted:
            print("Inserted successfully:")
            print(inserted)
        else:
            print("Order already exists (idempotency triggered)")


    except Exception as e:
        print("Error while creating Order:")
        print(e)

