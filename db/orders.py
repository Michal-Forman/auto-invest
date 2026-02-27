from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from db.client import supabase

import hashlib

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

