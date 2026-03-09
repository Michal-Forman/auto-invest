# Standard library
from typing import List, Optional

# Third-party
from fastapi import APIRouter

# Local
from api.schemas import OrderResponse
from core.db.orders import Order
from core.instrument_data import INSTRUMENT_NAMES

router = APIRouter()


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    ticker: Optional[str] = None,
    exchange: Optional[str] = None,
    status: Optional[str] = None,
) -> List[OrderResponse]:
    """Return orders with optional filters by ticker, exchange, and status."""
    orders: List[Order] = Order.get_orders(
        ticker=ticker, exchange=exchange, status=status
    )

    return [
        OrderResponse(
            id=str(o.id),
            run_id=str(o.run_id),
            ticker=o.t212_ticker,
            display_name=INSTRUMENT_NAMES.get(o.t212_ticker, o.t212_ticker),
            exchange=o.exchange,
            czk_amount=o.total_czk,
            quantity=o.filled_quantity,
            fill_price=o.fill_price,
            status=o.status,
        )
        for o in orders
    ]
