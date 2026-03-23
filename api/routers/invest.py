# Standard library
from datetime import datetime, timezone
from typing import Dict, List

# Third-party
from fastapi import APIRouter, Depends

# Local
from api.dependencies import (
    get_coinmate_for_user,
    get_current_user_id,
    get_t212_for_user,
    get_user_settings_for_user,
)
from api.routers.instruments import build_ratio_data
from api.schemas import InvestResponse
from core.db.orders import Order
from core.db.runs import Run, RunUpdate
from core.executor import Executor

router = APIRouter()

_MIN_ORDER = 25.0
_DROP_THRESHOLD = 12.5


@router.post("/invest", response_model=InvestResponse)
def place_investment(
    amount: float = 0,
    user_id: str = Depends(get_current_user_id),
) -> InvestResponse:
    """Place a one-time manual investment using ATH-adjusted distribution."""
    user_settings = get_user_settings_for_user(user_id)
    invest_amount = amount if amount > 0 else user_settings.portfolio.invest_amount

    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    data = build_ratio_data(user_id, user_settings, t212, coinmate)

    adj_weights: Dict[str, float] = data["adj_weights"]
    multipliers_map: Dict[str, float] = data["multipliers"]

    cash_distribution: Dict[str, float] = {}
    multipliers: Dict[str, float] = {}
    for ticker, weight in adj_weights.items():
        raw_czk = invest_amount * weight
        if raw_czk < _DROP_THRESHOLD:
            continue
        cash_distribution[ticker] = max(raw_czk, _MIN_ORDER)
        multipliers[ticker] = multipliers_map[ticker]

    run_start = datetime.now(timezone.utc)
    run = Run.create_run(
        run_start, user_settings.portfolio, user_id=user_id, investment_type="one_time"
    )
    assert run.id is not None

    executor = Executor(t212, coinmate, user_id=user_id)
    orders: List[Order] = executor.place_orders(
        cash_distribution, multipliers, run_id=run.id, investment_type="one_time"
    )

    run_update: RunUpdate = Run.process_new_run_data(orders)
    run.update_in_db(run_update)

    return InvestResponse(
        run_id=str(run.id), total_czk=float(sum(o.total_czk for o in orders))
    )
