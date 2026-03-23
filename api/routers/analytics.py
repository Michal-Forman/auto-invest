# Standard library
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

# Third-party
from fastapi import APIRouter, Depends
import yfinance as yf  # type: ignore[import-untyped]

# Local
from api.cache import instruments_cache
from api.dependencies import get_current_user_id
from api.schemas import (
    AnalyticsAllocationItem,
    AnalyticsRunItem,
    AnalyticsStatusItem,
    PortfolioValueItem,
    WarningItem,
)
from core.db.orders import Order
from core.db.runs import Run
from core.warnings import compute_warnings

router = APIRouter(prefix="/analytics")


@router.get("/runs", response_model=List[AnalyticsRunItem])
def analytics_runs(
    limit: int = 10, user_id: str = Depends(get_current_user_id)
) -> List[AnalyticsRunItem]:
    """Return the last N runs with their CZK total and status for bar chart display."""
    runs: List[Run] = Run.get_recent_runs(limit=limit, user_id=user_id)
    return [
        AnalyticsRunItem(
            date=run.started_at.date().isoformat(),
            czk=run.planned_total_czk or 0.0,
            status=run.status,
        )
        for run in runs
    ]


@router.get("/allocation", response_model=List[AnalyticsAllocationItem])
def analytics_allocation(
    limit: int = 8, user_id: str = Depends(get_current_user_id)
) -> List[AnalyticsAllocationItem]:
    """Return per-ticker allocation percentages for the last N FILLED runs."""
    runs: List[Run] = Run.get_recent_runs(limit=limit, user_id=user_id)
    result: List[AnalyticsAllocationItem] = []

    for run in runs:
        if run.status != "FILLED" or not run.distribution:
            continue

        dist: Dict[str, Any] = run.distribution
        total = sum(dist.values())
        if total == 0:
            continue

        pct: Dict[str, float] = {
            ticker: round(czk / total * 100, 2) for ticker, czk in dist.items()
        }
        result.append(
            AnalyticsAllocationItem(
                date=run.started_at.date().isoformat(),
                data=pct,
            )
        )

    return result


@router.get("/status", response_model=List[AnalyticsStatusItem])
def analytics_status(
    user_id: str = Depends(get_current_user_id),
) -> List[AnalyticsStatusItem]:
    """Return run counts grouped by status."""
    rows: List[Dict[str, Any]] = Run.get_status_counts(user_id=user_id)
    counts: Counter = Counter(row["status"] for row in rows)
    return [
        AnalyticsStatusItem(status=status, count=count)
        for status, count in counts.most_common()
    ]


_FX_SYMBOLS: Dict[str, str] = {
    "USD": "USDCZK=X",
    "EUR": "EURCZK=X",
    "GBP": "GBPCZK=X",
    "GBX": "GBPCZK=X",
}


@router.get("/portfolio-value", response_model=List[PortfolioValueItem])
def analytics_portfolio_value(
    user_id: str = Depends(get_current_user_id),
) -> List[PortfolioValueItem]:
    """Return current portfolio value (CZK) based on filled quantities and latest prices."""
    cache_key = f"portfolio_value:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    valid_orders = [o for o in all_orders if o.filled_at and o.filled_quantity]
    if not valid_orders:
        return []

    holdings: Dict[str, float] = defaultdict(float)
    for o in valid_orders:
        holdings[o.t212_ticker] += o.filled_quantity or 0.0

    ticker_meta: Dict[str, tuple] = {
        o.t212_ticker: (o.yahoo_symbol, o.currency) for o in valid_orders
    }

    yahoo_symbols: List[str] = list({meta[0] for meta in ticker_meta.values()})
    fx_needed: List[str] = list(
        {
            _FX_SYMBOLS[currency]
            for _, currency in ticker_meta.values()
            if currency in _FX_SYMBOLS
        }
    )
    all_dl = yahoo_symbols + fx_needed

    if len(all_dl) == 1:
        hist_raw = yf.download(
            all_dl[0], period="5d", auto_adjust=True, progress=False
        )
        close_series: Dict[str, Any] = {all_dl[0]: hist_raw["Close"]}
    else:
        hist_raw = yf.download(
            all_dl, period="5d", auto_adjust=True, progress=False
        )
        close_series = {sym: hist_raw["Close"][sym] for sym in all_dl}

    def _latest_price(symbol: str) -> float:
        series = close_series.get(symbol)
        if series is None or series.empty:
            return 0.0
        clean = series.dropna()
        return float(clean.iloc[-1]) if not clean.empty else 0.0

    total_czk = 0.0
    for ticker, qty in holdings.items():
        if qty <= 0:
            continue
        meta = ticker_meta.get(ticker)
        if not meta:
            continue
        yahoo_symbol, currency = meta
        price = _latest_price(yahoo_symbol)
        if currency == "CZK":
            price_czk = price
        elif currency in _FX_SYMBOLS:
            fx = _latest_price(_FX_SYMBOLS[currency])
            price_czk = price * fx * (0.01 if currency == "GBX" else 1.0)
        else:
            price_czk = price
        total_czk += qty * price_czk

    result: List[PortfolioValueItem] = [
        PortfolioValueItem(date=date.today().isoformat(), value=round(total_czk, 0))
    ]
    instruments_cache[cache_key] = result
    return result


@router.get("/warnings", response_model=List[WarningItem])
def analytics_warnings(
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
) -> List[WarningItem]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    recent = [o for o in all_orders if o.filled_at and o.filled_at >= since]
    return [WarningItem(**w) for w in compute_warnings(recent)]
