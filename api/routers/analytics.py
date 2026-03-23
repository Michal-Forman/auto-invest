# Standard library
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

# Third-party
from fastapi import APIRouter, Depends
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
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


def _get_price(close_series: Dict[str, Any], symbol: str, target: date) -> float:
    """Return the last available close price for symbol on or before target date."""
    series = close_series.get(symbol)
    if series is None or series.empty:
        return 0.0
    target_ts = pd.Timestamp(target)
    filtered = series[series.index.normalize() <= target_ts].dropna()
    if filtered.empty:
        fallback = series.dropna()
        return float(fallback.iloc[0]) if not fallback.empty else 0.0
    return float(filtered.iloc[-1])


@router.get("/portfolio-value", response_model=List[PortfolioValueItem])
def analytics_portfolio_value(
    user_id: str = Depends(get_current_user_id),
) -> List[PortfolioValueItem]:
    """Return actual portfolio value (CZK) at each completed run date using historical prices."""
    cache_key = f"portfolio_value:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    valid_orders = [o for o in all_orders if o.filled_at and o.filled_quantity]
    if not valid_orders:
        return []

    all_runs: List[Run] = Run.get_all_runs(limit=1000, user_id=user_id)
    snapshot_dates = sorted(
        {r.started_at.date() for r in all_runs if r.status in ("FILLED", "FINISHED")}
    )
    if not snapshot_dates:
        return []

    valid_orders.sort(key=lambda o: o.filled_at or datetime.min)  # type: ignore[arg-type]

    ticker_meta: Dict[str, tuple] = {
        o.t212_ticker: (o.yahoo_symbol, o.currency) for o in valid_orders
    }

    start_date = valid_orders[0].filled_at.date() - timedelta(days=7)  # type: ignore[union-attr]
    end_date = date.today() + timedelta(days=1)

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
            all_dl[0], start=start_date, end=end_date, auto_adjust=True, progress=False
        )
        close_series: Dict[str, Any] = {all_dl[0]: hist_raw["Close"]}
    else:
        hist_raw = yf.download(
            all_dl, start=start_date, end=end_date, auto_adjust=True, progress=False
        )
        close_series = {sym: hist_raw["Close"][sym] for sym in all_dl}

    result: List[PortfolioValueItem] = []
    running_holdings: Dict[str, float] = defaultdict(float)
    order_idx = 0

    for snap_date in snapshot_dates:
        while order_idx < len(valid_orders):
            o = valid_orders[order_idx]
            if o.filled_at.date() <= snap_date:  # type: ignore[union-attr]
                running_holdings[o.t212_ticker] += o.filled_quantity or 0.0
                order_idx += 1
            else:
                break

        total_czk = 0.0
        for ticker, qty in running_holdings.items():
            if qty <= 0:
                continue
            meta = ticker_meta.get(ticker)
            if not meta:
                continue
            yahoo_symbol, currency = meta
            price = _get_price(close_series, yahoo_symbol, snap_date)
            if currency == "CZK":
                price_czk = price
            elif currency in _FX_SYMBOLS:
                fx = _get_price(close_series, _FX_SYMBOLS[currency], snap_date)
                price_czk = price * fx * (0.01 if currency == "GBX" else 1.0)
            else:
                price_czk = price
            total_czk += qty * price_czk

        result.append(
            PortfolioValueItem(date=snap_date.isoformat(), value=round(total_czk, 0))
        )

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
