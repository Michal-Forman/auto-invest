# Standard library
from typing import List, Optional

# Third-party
from fastapi import APIRouter, Depends, HTTPException

# Local
from api.dependencies import get_current_user_id
from api.schemas import OrderResponse, RunDetailResponse, RunResponse
from core.db.orders import Order
from core.db.runs import Run
from core.instrument_data import INSTRUMENT_NAMES

router = APIRouter()


def _order_to_response(order: Order) -> OrderResponse:
    """Map an Order model to an OrderResponse."""
    return OrderResponse(
        id=str(order.id),
        run_id=str(order.run_id),
        ticker=order.t212_ticker,
        display_name=INSTRUMENT_NAMES.get(order.t212_ticker, order.t212_ticker),
        exchange=order.exchange,
        czk_amount=order.total_czk,
        quantity=order.filled_quantity,
        fill_price=order.fill_price,
        status=order.status,
    )


def _run_to_response(run: Run) -> RunResponse:
    """Map a Run model to a RunResponse."""
    return RunResponse(
        id=str(run.id),
        created_at=run.started_at.isoformat(),
        status=run.status,
        total_czk=run.planned_total_czk or 0.0,
        order_count=run.total_orders or 0,
    )


@router.get("/runs", response_model=List[RunResponse])
def list_runs(
    limit: int = 50,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
) -> List[RunResponse]:
    """Return runs with optional status filter, most recent first."""
    runs: List[Run] = Run.get_all_runs(limit=limit, status=status, user_id=user_id)
    return [_run_to_response(r) for r in runs]


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: str, user_id: str = Depends(get_current_user_id)
) -> RunDetailResponse:
    """Return a single run with its embedded orders."""
    runs: List[Run] = Run.get_all_runs(limit=1000, user_id=user_id)
    run: Optional[Run] = next((r for r in runs if str(r.id) == run_id), None)

    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    orders: List[Order] = Order.get_orders_for_runs([run_id], user_id=user_id)

    return RunDetailResponse(
        **_run_to_response(run).model_dump(),
        orders=[_order_to_response(o) for o in orders],
    )
