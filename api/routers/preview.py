# Standard library
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
from api.schemas import PreviewItemResponse
from core.instrument_data import INSTRUMENT_NAMES, T212_TO_YF

router = APIRouter()

_MIN_ORDER = 25.0
_DROP_THRESHOLD = 12.5


@router.get("/preview", response_model=List[PreviewItemResponse])
def preview(
    amount: float = 0,
    user_id: str = Depends(get_current_user_id),
) -> List[PreviewItemResponse]:
    """Return a per-instrument distribution preview. Supports ?amount= override."""
    user_settings = get_user_settings_for_user(user_id)
    invest_amount = amount if amount > 0 else user_settings.portfolio.invest_amount

    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    data = build_ratio_data(user_id, user_settings, t212, coinmate)
    adj_weights: Dict[str, float] = data["adj_weights"]
    target_weights: Dict[str, float] = data["target_weights"]

    result: List[PreviewItemResponse] = []
    for ticker in T212_TO_YF:
        if ticker not in adj_weights:
            continue

        raw_czk = invest_amount * adj_weights[ticker]

        if raw_czk < _DROP_THRESHOLD:
            note = "dropped"
            czk_amount = 0.0
        elif raw_czk < _MIN_ORDER:
            note = "bumped"
            czk_amount = _MIN_ORDER
        else:
            note = "normal"
            czk_amount = raw_czk

        result.append(
            PreviewItemResponse(
                ticker=ticker,
                display_name=INSTRUMENT_NAMES.get(ticker, ticker),
                target_weight=target_weights[ticker],
                drop_pct=data["drop_pcts"][ticker],
                multiplier=data["multipliers"][ticker],
                adjusted_weight=adj_weights[ticker],
                czk_amount=czk_amount,
                note=note,
            )
        )

    return result
