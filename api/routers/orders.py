# Standard library
from typing import List, Optional

# Third-party
from fastapi import APIRouter, Depends

# Local
from api.dependencies import get_current_user_id
from api.schemas import OrderResponse
from core.db.orders import Order
from core.instrument_data import INSTRUMENT_NAMES

router = APIRouter()


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    ticker: Optional[str] = None,
    exchange: Optional[str] = None,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
) -> List[OrderResponse]:
    """Return orders with optional filters by ticker, exchange, and status."""
    orders: List[Order] = Order.get_orders(
        ticker=ticker, exchange=exchange, status=status, user_id=user_id
    )

    return [
        OrderResponse(
            id=str(o.id),
            run_id=str(o.run_id),
            ticker=o.t212_ticker,
            display_name=INSTRUMENT_NAMES.get(o.t212_ticker, o.t212_ticker),
            exchange=o.exchange,
            czk_amount=float(o.total_czk),
            quantity=(
                float(o.filled_quantity) if o.filled_quantity is not None else None
            ),
            fill_price=float(o.fill_price) if o.fill_price is not None else None,
            status=o.status,
        )
        for o in orders
    ]
