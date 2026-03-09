# Standard library
from typing import Any, Dict, List

# Third-party
from fastapi import APIRouter

# Local
from api.cache import instruments_cache
from api.dependencies import get_coinmate, get_t212
from api.schemas import InstrumentResponse
from core.instrument_data import (
    INSTRUMENT_CAPS,
    INSTRUMENT_NAMES,
    INSTRUMENT_TYPES,
    T212_TO_YF,
)
from core.instruments import Instruments
from core.settings import settings

router = APIRouter()

_SOFT_CAP = 75
_HARD_CAP_RESET = 90
_CACHE_KEY = "instruments"


def _apply_cap(drop: float, cap_type: str) -> float:
    """Apply the configured cap type to a raw drop percentage."""
    if cap_type == "soft":
        return min(drop, _SOFT_CAP)
    if cap_type == "hard":
        return 0.0 if drop >= _HARD_CAP_RESET else min(drop, _SOFT_CAP)
    return drop  # "none"


def build_ratio_data() -> Dict[str, Any]:
    """Fetch live prices and compute ATH-adjusted ratios. Results are cached for 15 minutes."""
    if _CACHE_KEY in instruments_cache:
        return instruments_cache[_CACHE_KEY]  # type: ignore[return-value]

    t212 = get_t212()
    coinmate = get_coinmate()
    instruments_obj = Instruments(t212, coinmate, settings.portfolio)
    default_ratios: Dict[str, float] = instruments_obj.get_default_ratios()

    total_default = sum(default_ratios.values())

    ath_prices: Dict[str, float] = {}
    current_prices: Dict[str, float] = {}
    drop_pcts: Dict[str, float] = {}
    multipliers: Dict[str, float] = {}
    adjusted_values: Dict[str, float] = {}

    for ticker, base_ratio in default_ratios.items():
        ath = Instruments.get_ath(ticker)
        current = Instruments.get_current_price(ticker)
        raw_drop = (ath - current) / ath * 100
        cap_type = INSTRUMENT_CAPS.get(ticker, "none")
        capped_drop = _apply_cap(raw_drop, cap_type)
        mult = 100 / (100 - capped_drop)

        ath_prices[ticker] = ath
        current_prices[ticker] = current
        drop_pcts[ticker] = raw_drop
        multipliers[ticker] = mult
        adjusted_values[ticker] = base_ratio * mult

    total_adj = sum(adjusted_values.values())
    adj_weights: Dict[str, float] = {
        t: v / total_adj for t, v in adjusted_values.items()
    }
    target_weights: Dict[str, float] = {
        t: v / total_default for t, v in default_ratios.items()
    }

    # Compute default-amount CZK distribution
    raw_czk: Dict[str, float] = {
        t: settings.portfolio.invest_amount * w for t, w in adj_weights.items()
    }
    next_czk: Dict[str, float] = {}
    for ticker, czk in raw_czk.items():
        if czk < 12.5:
            next_czk[ticker] = 0.0
        elif czk < 25.0:
            next_czk[ticker] = 25.0
        else:
            next_czk[ticker] = czk

    data: Dict[str, Any] = {
        "default_ratios": default_ratios,
        "target_weights": target_weights,
        "ath_prices": ath_prices,
        "current_prices": current_prices,
        "drop_pcts": drop_pcts,
        "multipliers": multipliers,
        "adjusted_values": adjusted_values,
        "adj_weights": adj_weights,
        "next_czk": next_czk,
    }
    instruments_cache[_CACHE_KEY] = data
    return data


@router.get("/instruments", response_model=List[InstrumentResponse])
def list_instruments() -> List[InstrumentResponse]:
    """Return live instrument data including ATH drop, multiplier, and next CZK allocation. Cached for 15 minutes."""
    data = build_ratio_data()

    result: List[InstrumentResponse] = []
    for ticker in T212_TO_YF:
        if ticker not in data["default_ratios"]:
            continue
        exchange = "Coinmate" if ticker == "BTC" else "T212"
        result.append(
            InstrumentResponse(
                ticker=ticker,
                display_name=INSTRUMENT_NAMES.get(ticker, ticker),
                exchange=exchange,
                cap_type=INSTRUMENT_CAPS.get(ticker, "none"),
                target_weight=data["target_weights"][ticker],
                ath_price=data["ath_prices"][ticker],
                current_price=data["current_prices"][ticker],
                drop_pct=data["drop_pcts"][ticker],
                multiplier=data["multipliers"][ticker],
                adjusted_weight=data["adj_weights"][ticker],
                next_czk=data["next_czk"].get(ticker, 0.0),
            )
        )

    return result
