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
    currency: str
    instrument_type: str
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
    api: bool
    t212: bool
    coinmate: bool


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


class PortfolioValueItem(BaseModel):
    date: str
    value: float


class HoldingItem(BaseModel):
    ticker: str
    value_czk: float


class WarningItem(BaseModel):
    ticker: str
    type: str
    detail: str


class ProfileResponse(BaseModel):
    t212_id_key: str
    t212_private_key: str
    coinmate_client_id: Optional[int]
    coinmate_public_key: str
    coinmate_private_key: str
    pie_id: Optional[int]
    t212_weight: Optional[int]
    btc_weight: Optional[float]
    invest_amount: Optional[float]
    invest_interval: Optional[str]
    balance_buffer: Optional[float]
    balance_alert_days: Optional[int]
    btc_withdrawal_treshold: Optional[int]
    btc_external_adress: str
    t212_deposit_account: Optional[str]
    t212_deposit_vs: Optional[str]
    coinmate_deposit_account: Optional[str]
    coinmate_deposit_vs: Optional[str]
    cron_enabled: bool
    notifications_enabled: bool
    btc_withdrawals_enabled: bool
    trading212_enabled: bool
    coinmate_enabled: bool


class InvestResponse(BaseModel):
    run_id: str
    total_czk: float


class ProfitLossResponse(BaseModel):
    filled_run_count: int
    total_invested_czk: float
    current_value_czk: float
    gain_czk: float
    gain_pct: float


class PortfolioHistoryItem(BaseModel):
    date: str
    value: float


class StrategyComparisonItem(BaseModel):
    date: str
    actual_value: float
    baseline_value: float


class HoldingRatioItem(BaseModel):
    ticker: str
    ratio_pct: float


class ProfileUpdate(BaseModel):
    t212_id_key: Optional[str] = None
    t212_private_key: Optional[str] = None
    coinmate_client_id: Optional[int] = None
    coinmate_public_key: Optional[str] = None
    coinmate_private_key: Optional[str] = None
    pie_id: Optional[int] = None
    t212_weight: Optional[int] = None
    btc_weight: Optional[float] = None
    invest_amount: Optional[float] = None
    invest_interval: Optional[str] = None
    balance_buffer: Optional[float] = None
    balance_alert_days: Optional[int] = None
    btc_withdrawal_treshold: Optional[int] = None
    btc_external_adress: Optional[str] = None
    t212_deposit_account: Optional[str] = None
    t212_deposit_vs: Optional[str] = None
    coinmate_deposit_account: Optional[str] = None
    coinmate_deposit_vs: Optional[str] = None
    cron_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    btc_withdrawals_enabled: Optional[bool] = None
    trading212_enabled: Optional[bool] = None
    coinmate_enabled: Optional[bool] = None
