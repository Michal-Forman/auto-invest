# Standard library
from typing import Dict, List

# Third-party
from fastapi import APIRouter

# Local
from api.routers.instruments import build_ratio_data
from api.schemas import PreviewItemResponse
from core.instrument_data import INSTRUMENT_NAMES, T212_TO_YF
from core.settings import settings

router = APIRouter()

_MIN_ORDER = 25.0
_DROP_THRESHOLD = 12.5


@router.get("/preview", response_model=List[PreviewItemResponse])
def preview(amount: float = 0) -> List[PreviewItemResponse]:
    """Return a per-instrument distribution preview. Supports ?amount= override."""
    invest_amount = amount if amount > 0 else settings.portfolio.invest_amount

    data = build_ratio_data()
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
