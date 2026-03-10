# Standard library
from typing import List

# Third-party
from fastapi import APIRouter, Depends

# Local
from api.dependencies import get_current_user_id, get_user_settings_for_user
from api.schemas import ConfigResponse, InstrumentRegistryItem
from core.instrument_data import (
    INSTRUMENT_CAPS,
    INSTRUMENT_CURRENCIES,
    INSTRUMENT_NAMES,
    INSTRUMENT_TYPES,
    T212_TO_YF,
)
from core.settings import UserSettings, settings

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def config(user_id: str = Depends(get_current_user_id)) -> ConfigResponse:
    """Return portfolio settings and the static instrument registry."""
    user_settings: UserSettings = get_user_settings_for_user(user_id)
    p = user_settings.portfolio

    instruments: List[InstrumentRegistryItem] = [
        InstrumentRegistryItem(
            ticker=ticker,
            display_name=INSTRUMENT_NAMES.get(ticker, ticker),
            yahoo_symbol=T212_TO_YF[ticker],
            currency=INSTRUMENT_CURRENCIES.get(ticker, ""),
            instrument_type=INSTRUMENT_TYPES.get(ticker, ""),
            cap_type=INSTRUMENT_CAPS.get(ticker, "none"),
        )
        for ticker in T212_TO_YF
    ]

    return ConfigResponse(
        invest_amount=p.invest_amount,
        t212_weight=float(p.t212_weight),
        btc_weight=p.btc_weight,
        invest_interval=p.invest_interval,
        environment=settings.env,
        instruments=instruments,
    )
