# Future
from __future__ import annotations

# Standard library
from datetime import datetime, timezone
import hashlib
from typing import Any, ClassVar, Dict, List, Literal, Optional, cast
from uuid import UUID

# Third-party
from httpx import RequestError
from pydantic import BaseModel, Field, model_validator

# Local
from core.coinmate import Coinmate
from core.db.base import BaseDBModel
from core.db.client import supabase
from core.log import log
from core.settings import settings
from core.trading212 import Trading212

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


class Order(BaseDBModel):
    # --- Identity ---
    TABLE: ClassVar[str] = "orders"
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
        """Enforce business rules: LIMIT orders need limit_price, auto-generate idempotency key, normalize precision."""
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

    # -------------------------
    # Helper methods for DB
    # -------------------------

    def generate_idempotency_key(self) -> str:
        """Generate a SHA-256 idempotency key from the order's identifying fields to prevent duplicate inserts."""

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
        """Apply an OrderUpdate to this order's row in Supabase. Returns the updated row dict or None."""
        if not self.id:
            raise ValueError("Cannot update order without id")

        update_fields: Dict[str, Any] = update_data.model_dump(
            mode="json", exclude_none=True
        )

        response: Any = (
            supabase.table(self.TABLE)
            .update(update_fields)
            .eq("id", str(self.id))
            .execute()
        )

        if response.data:
            log.info("Successfully updated the order in db")
            row = cast(Dict[str, Any], response.data[0])
            for field, value in update_data.model_dump(exclude_none=True).items():
                setattr(self, field, value)
            return row

        return None

    @staticmethod
    def get_orders_for_runs(run_ids: List[str]) -> List[Order]:
        """Fetch all orders belonging to the given run IDs."""
        if not run_ids:
            return []

        response: Any = (
            supabase.table(Order.TABLE).select("*").in_("run_id", run_ids).execute()
        )

        if not response.data:
            return []

        return [Order.model_validate(row) for row in response.data]

    @staticmethod
    def get_orders(
        ticker: Optional[str] = None,
        exchange: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Order]:
        """Fetch orders with optional filters, ordered by most recent first."""
        query: Any = (
            supabase.table(Order.TABLE)
            .select("*")
            .order("submitted_at", desc=True)
        )

        if ticker:
            query = query.eq("t212_ticker", ticker)
        if exchange:
            query = query.eq("exchange", exchange)
        if status:
            query = query.eq("status", status)

        response: Any = query.execute()

        if not response.data:
            return []

        return [Order.model_validate(row) for row in response.data]

    @staticmethod
    def get_submitted_orders() -> List[Order]:
        """Fetch all orders with status SUBMITTED from the database."""
        response: Any = (
            supabase.table(Order.TABLE).select("*").eq("status", "SUBMITTED").execute()
        )

        if not response.data:
            return []

        return [Order.model_validate(row) for row in response.data]

    @staticmethod
    def _process_new_coinmate_data(order: Dict[str, Any]) -> OrderUpdate:
        """Parse a Coinmate trade history entry into an OrderUpdate with fill details and fees."""
        status: Status = "FILLED" if order["amount"] != 0 else "FAILED"

        ts: int = order["createdTimestamp"]
        filled_at: datetime = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

        filled_total: float = order["amount"] * order["price"] - order["fee"]

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
    def update_orders(cls, t212: Trading212, coinmate: Coinmate) -> None:
        """Match all SUBMITTED orders against T212/Coinmate trade history and update their fill status in the DB."""
        orders_to_update: List[Order] = Order.get_submitted_orders()

        if not orders_to_update:
            log.info("No submitted orders to update")
            return

        coinmate_history_data: Dict[str, Any] = coinmate.user_trades()
        t212_history_data: List[Dict[str, Any]] = (
            t212.orders() if settings.env == "prod" else t212.orders_page()
        )
        updated_orders: List[Order] = []
        pending_orders: List[Order] = []
        unresolved_orders: List[Order] = []

        coinmate_res = coinmate_history_data.get("res") or {}
        if coinmate_res.get("error") is not False:
            raise RequestError("Failed to get Coinmate history data")

        if t212_history_data is None:
            raise RequestError("Failed to get T212 history data")

        for order in orders_to_update:
            order_update: Optional[OrderUpdate] = None

            if order.t212_ticker == "BTC":
                orders: List[Dict[str, Any]] = coinmate_res.get("data") or []
                matched_order: Optional[Dict[str, Any]] = next(
                    (
                        o
                        for o in orders
                        if str(o["orderId"]) == str(order.external_order_id)
                    ),
                    None,
                )
                if matched_order:
                    order_update = cls._process_new_coinmate_data(matched_order)
                else:
                    log.warning(
                        f"No matching Coinmate order found for {order.external_order_id} ({order.t212_ticker})"
                    )
                    unresolved_orders.append(order)

            else:
                items: List[Dict[str, Any]] = t212_history_data
                matched_item: Optional[Dict[str, Any]] = next(
                    (
                        item
                        for item in items
                        if str(item["order"]["id"]) == str(order.external_order_id)
                    ),
                    None,
                )
                if matched_item:
                    order_update = cls._process_new_t212_data(matched_item)
                elif order.external_order_id:
                    equity_resp: Dict[str, Any] = t212.equity_order(
                        int(order.external_order_id)
                    )
                    if equity_resp.get("err") is None:
                        log.info(
                            f"Order {order.external_order_id} ({order.t212_ticker}) is still pending on T212"
                        )
                        pending_orders.append(order)
                    else:
                        log.warning(
                            f"No matching order found for {order.external_order_id} ({order.t212_ticker})"
                        )
                        unresolved_orders.append(order)
                else:
                    log.warning(
                        f"No matching order found and no external_order_id for {order.t212_ticker}"
                    )
                    unresolved_orders.append(order)

            if order_update:
                try:
                    order.update_in_db(order_update)
                    log.info(
                        f"Successfully updated order {order.external_order_id} ({order.t212_ticker})"
                    )
                    updated_orders.append(order)
                except Exception as e:
                    log.error(
                        f"Failed to update order {order.id} ({order.t212_ticker}): {e}"
                    )

        log.info(
            f"Orders updated: {len(updated_orders)}, pending: {len(pending_orders)}, unresolved: {len(unresolved_orders)}"
        )

    @staticmethod
    def _process_new_t212_data(item: Dict[str, Any]) -> OrderUpdate:
        """Parse a T212 order history item into an OrderUpdate with fill details, fees, and FX rate."""
        order: Dict[str, Any] = item["order"]
        fill: Optional[Dict[str, Any]] = item.get("fill")

        status: Status
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
            wallet_impact: Dict[str, Any] = fill["walletImpact"]
            filled_at = fill.get("filledAt")
            fill_fx_rate = 1 / wallet_impact["fxRate"]
            fee = abs(wallet_impact["taxes"][0]["quantity"])
            fee_currency = wallet_impact["taxes"][0]["currency"]
            fee_czk = fee if fee_currency == "CZK" else None
            filled_total_czk = wallet_impact["netValue"]
            filled_total = filled_total_czk / fill_fx_rate
            fill_price = fill.get("price")
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
