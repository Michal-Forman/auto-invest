# Standard library
from typing import Any, Dict, List, Optional

# Third-party
from pydantic import BaseModel


class RunResponse(BaseModel):
    id: str
    created_at: str
    status: str
    total_czk: float
    order_count: int


class OrderResponse(BaseModel):
    id: str
    run_id: str
    ticker: str
    display_name: str
    exchange: str
    czk_amount: float
    quantity: Optional[float]
    fill_price: Optional[float]
    status: str


class RunDetailResponse(RunResponse):
    orders: List[OrderResponse]


class InstrumentRegistryItem(BaseModel):
    ticker: str
    display_name: str
    yahoo_symbol: str
    currency: str
    instrument_type: str
    cap_type: str


class ConfigResponse(BaseModel):
    invest_amount: float
    t212_weight: float
    btc_weight: float
    invest_interval: str
    environment: str
    instruments: List[InstrumentRegistryItem]


class InstrumentResponse(BaseModel):
    ticker: str
    display_name: str
    exchange: str
    cap_type: str
    target_weight: float
    ath_price: float
    current_price: float
    drop_pct: float
    multiplier: float
    adjusted_weight: float
    next_czk: float


class PreviewItemResponse(BaseModel):
    ticker: str
    display_name: str
    target_weight: float
    drop_pct: float
    multiplier: float
    adjusted_weight: float
    czk_amount: float
    note: str


class HealthResponse(BaseModel):
    api: str
    t212: str
    coinmate: str


class AnalyticsRunItem(BaseModel):
    date: str
    czk: float
    status: str


class AnalyticsAllocationItem(BaseModel):
    date: str
    data: Dict[str, float]


class AnalyticsStatusItem(BaseModel):
    status: str
    count: int
