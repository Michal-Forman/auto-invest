# Standard library
from typing import List

# Third-party
from fastapi import APIRouter

# Local
from api.schemas import ConfigResponse, InstrumentRegistryItem
from core.instrument_data import (
    INSTRUMENT_CAPS,
    INSTRUMENT_CURRENCIES,
    INSTRUMENT_NAMES,
    INSTRUMENT_TYPES,
    T212_TO_YF,
)
from core.settings import settings

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    """Return portfolio settings and the static instrument registry."""
    p = settings.portfolio

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
        t212_weight=p.t212_weight / 100,
        btc_weight=p.btc_weight,
        invest_interval=p.invest_interval,
        environment=settings.env,
        instruments=instruments,
    )
