# Standard library
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

# Third-party
from fastapi import APIRouter, Depends

# Local
from api.cache import instruments_cache
from api.dependencies import (
    get_coinmate_for_user,
    get_current_user_id,
    get_t212_for_user,
    get_user_settings_for_user,
)
from api.schemas import InstrumentResponse
from core.coinmate import Coinmate
from core.instrument_data import (
    INSTRUMENT_CAPS,
    INSTRUMENT_CURRENCIES,
    INSTRUMENT_NAMES,
    INSTRUMENT_TYPES,
    T212_TO_YF,
)
from core.instruments import Instruments
from core.settings import UserSettings
from core.trading212 import Trading212

router = APIRouter()

_SOFT_CAP = 75
_HARD_CAP_RESET = 90


def _apply_cap(drop: float, cap_type: str) -> float:
    """Apply the configured cap type to a raw drop percentage."""
    if cap_type == "soft":
        return min(drop, _SOFT_CAP)
    if cap_type == "hard":
        return 0.0 if drop >= _HARD_CAP_RESET else min(drop, _SOFT_CAP)
    return drop  # "none"


def build_ratio_data(
    user_id: str,
    user_settings: UserSettings,
    t212: Trading212,
    coinmate: Coinmate,
) -> Dict[str, Any]:
    """Fetch live prices and compute ATH-adjusted ratios. Results are cached 15 min per user."""
    cache_key = f"instruments:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    instruments_obj = Instruments(t212, coinmate, user_settings.portfolio)
    default_ratios: Dict[str, float] = instruments_obj.get_default_ratios()

    total_default = sum(default_ratios.values())

    ath_prices: Dict[str, float] = {}
    current_prices: Dict[str, float] = {}
    drop_pcts: Dict[str, float] = {}
    multipliers: Dict[str, float] = {}
    adjusted_values: Dict[str, float] = {}

    def _fetch_ticker_data(ticker: str) -> Tuple[str, float, float]:
        ath: float = Instruments.get_ath(ticker)
        current: float = Instruments.get_current_price(ticker)
        return ticker, ath, current

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_fetch_ticker_data, ticker): ticker for ticker in default_ratios
        }
        for future in as_completed(futures):
            ticker, ath, current = future.result()
            base_ratio: float = default_ratios[ticker]
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
        t: user_settings.portfolio.invest_amount * w for t, w in adj_weights.items()
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
    instruments_cache[cache_key] = data
    return data


@router.get("/instruments", response_model=List[InstrumentResponse])
def list_instruments(
    user_id: str = Depends(get_current_user_id),
) -> List[InstrumentResponse]:
    """Return live instrument data including ATH drop, multiplier, and next CZK allocation. Cached 15 min per user."""
    user_settings = get_user_settings_for_user(user_id)
    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    data = build_ratio_data(user_id, user_settings, t212, coinmate)

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
                currency=INSTRUMENT_CURRENCIES.get(ticker, ""),
                instrument_type=INSTRUMENT_TYPES.get(ticker, ""),
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
