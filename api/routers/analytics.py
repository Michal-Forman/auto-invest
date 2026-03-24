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
    HoldingItem,
    HoldingRatioItem,
    PortfolioHistoryItem,
    PortfolioValueItem,
    ProfitLossResponse,
    StrategyComparisonItem,
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

# Yahoo symbols where the price currency differs from the order's transaction currency
# (BTC is purchased in CZK on Coinmate, but Yahoo Finance provides BTC-USD price in USD)
_YAHOO_PRICE_CURRENCY: Dict[str, str] = {
    "BTC-USD": "USD",
}


def _compute_holdings_czk(user_id: str) -> Dict[str, float]:
    """Return per-ticker portfolio value in CZK based on filled quantities and latest prices."""
    cache_key = f"holdings_czk:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    valid_orders = [o for o in all_orders if o.filled_at and o.filled_quantity]
    if not valid_orders:
        return {}

    holdings: Dict[str, float] = defaultdict(float)
    for o in valid_orders:
        holdings[o.t212_ticker] += o.filled_quantity or 0.0

    ticker_meta: Dict[str, tuple] = {
        o.t212_ticker: (o.yahoo_symbol, o.currency) for o in valid_orders
    }

    yahoo_symbols: List[str] = list({meta[0] for meta in ticker_meta.values()})
    fx_needed: List[str] = list(
        {
            _FX_SYMBOLS[_YAHOO_PRICE_CURRENCY.get(meta[0], meta[1])]
            for meta in ticker_meta.values()
            if _YAHOO_PRICE_CURRENCY.get(meta[0], meta[1]) in _FX_SYMBOLS
        }
    )
    all_dl = yahoo_symbols + fx_needed

    if len(all_dl) == 1:
        hist_raw = yf.download(all_dl[0], period="5d", auto_adjust=True, progress=False)
        close_series: Dict[str, Any] = {all_dl[0]: hist_raw["Close"]}
    else:
        hist_raw = yf.download(all_dl, period="5d", auto_adjust=True, progress=False)
        close_series = {sym: hist_raw["Close"][sym] for sym in all_dl}

    def _latest_price(symbol: str) -> float:
        series = close_series.get(symbol)
        if series is None or series.empty:
            return 0.0
        clean = series.dropna()
        return float(clean.iloc[-1]) if not clean.empty else 0.0

    per_ticker: Dict[str, float] = {}
    for ticker, qty in holdings.items():
        if qty <= 0:
            continue
        meta = ticker_meta.get(ticker)
        if not meta:
            continue
        yahoo_symbol, currency = meta
        price_currency = _YAHOO_PRICE_CURRENCY.get(yahoo_symbol, currency)
        price = _latest_price(yahoo_symbol)
        if price_currency == "CZK":
            price_czk = price
        elif price_currency in _FX_SYMBOLS:
            fx = _latest_price(_FX_SYMBOLS[price_currency])
            price_czk = price * fx * (0.01 if price_currency == "GBX" else 1.0)
        else:
            price_czk = price
        per_ticker[ticker] = qty * price_czk

    instruments_cache[cache_key] = per_ticker
    return per_ticker


@router.get("/portfolio-value", response_model=List[PortfolioValueItem])
def analytics_portfolio_value(
    user_id: str = Depends(get_current_user_id),
) -> List[PortfolioValueItem]:
    """Return current portfolio value (CZK) based on filled quantities and latest prices."""
    cache_key = f"portfolio_value:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]
    per_ticker = _compute_holdings_czk(user_id)
    if not per_ticker:
        return []
    total_czk = sum(per_ticker.values())
    result = [
        PortfolioValueItem(date=date.today().isoformat(), value=round(total_czk, 0))
    ]
    instruments_cache[cache_key] = result
    return result


@router.get("/holdings", response_model=List[HoldingItem])
def analytics_holdings(
    user_id: str = Depends(get_current_user_id),
) -> List[HoldingItem]:
    """Return per-ticker holdings value in CZK."""
    per_ticker = _compute_holdings_czk(user_id)
    return [HoldingItem(ticker=t, value_czk=round(v, 0)) for t, v in per_ticker.items()]


def _fetch_price_history(
    ticker_meta: Dict[str, tuple],
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    """Download full yfinance Close history for all instruments + FX pairs."""
    yahoo_symbols: List[str] = list({meta[0] for meta in ticker_meta.values()})
    fx_needed: List[str] = list(
        {_FX_SYMBOLS[c] for _, c in ticker_meta.values() if c in _FX_SYMBOLS}
    )
    all_dl = yahoo_symbols + fx_needed
    end_dl = end_date + timedelta(days=1)

    if len(all_dl) == 1:
        hist = yf.download(
            all_dl[0], start=start_date, end=end_dl, auto_adjust=True, progress=False
        )
        return {all_dl[0]: hist["Close"]}
    else:
        hist = yf.download(
            all_dl, start=start_date, end=end_dl, auto_adjust=True, progress=False
        )
        return {sym: hist["Close"][sym] for sym in all_dl}


def _get_price(close_series: Dict[str, Any], symbol: str, target: date) -> float:
    """Return closing price for symbol on or before target date."""
    return _price_on_date(close_series.get(symbol), target)


def _price_on_date(series: Any, target: date) -> float:
    """Return closing price on or before target date (handles weekends/holidays)."""
    if series is None or series.empty:
        return 0.0
    clean = series.dropna()
    if clean.empty:
        return 0.0
    mask = clean.index.date <= target
    eligible = clean[mask]
    return float(eligible.iloc[-1]) if not eligible.empty else 0.0


def _to_czk_on_date(
    price: float, currency: str, close_series: Dict[str, Any], target: date
) -> float:
    """Convert instrument price to CZK using historical FX rate on target date."""
    if currency == "CZK":
        return price
    fx_symbol = _FX_SYMBOLS.get(currency)
    if not fx_symbol:
        return price
    fx = _price_on_date(close_series.get(fx_symbol), target)
    if fx == 0.0:
        return price
    return price * fx * (0.01 if currency == "GBX" else 1.0)


@router.get("/profit-loss", response_model=ProfitLossResponse)
def analytics_profit_loss(
    user_id: str = Depends(get_current_user_id),
) -> ProfitLossResponse:
    filled_runs: List[Run] = Run.get_all_runs(
        limit=1000, status="FILLED", user_id=user_id
    )
    filled_run_count = len(filled_runs)
    total_invested = sum(
        r.filled_total_czk or r.planned_total_czk or 0.0 for r in filled_runs
    )
    per_ticker = _compute_holdings_czk(user_id)
    current_value = sum(per_ticker.values())
    gain_czk = current_value - total_invested
    gain_pct = (gain_czk / total_invested * 100) if total_invested > 0 else 0.0
    return ProfitLossResponse(
        filled_run_count=filled_run_count,
        total_invested_czk=round(total_invested, 0),
        current_value_czk=round(current_value, 0),
        gain_czk=round(gain_czk, 0),
        gain_pct=round(gain_pct, 2),
    )


@router.get("/holdings-ratio", response_model=List[HoldingRatioItem])
def analytics_holdings_ratio(
    user_id: str = Depends(get_current_user_id),
) -> List[HoldingRatioItem]:
    per_ticker = _compute_holdings_czk(user_id)
    total = sum(per_ticker.values())
    if total == 0:
        return []
    return sorted(
        [
            HoldingRatioItem(ticker=t, ratio_pct=round(v / total * 100, 2))
            for t, v in per_ticker.items()
        ],
        key=lambda x: x.ratio_pct,
        reverse=True,
    )


@router.get("/portfolio-history", response_model=List[PortfolioHistoryItem])
def analytics_portfolio_history(
    user_id: str = Depends(get_current_user_id),
) -> List[PortfolioHistoryItem]:
    cache_key = f"portfolio_history:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    valid_orders = sorted(
        [o for o in all_orders if o.filled_at and o.filled_quantity],
        key=lambda o: o.filled_at,  # type: ignore[arg-type, return-value]
    )
    if not valid_orders:
        return []

    ticker_meta: Dict[str, tuple] = {
        o.t212_ticker: (o.yahoo_symbol, o.currency) for o in valid_orders
    }
    earliest = valid_orders[0].filled_at.date()  # type: ignore[union-attr]
    close_series = _fetch_price_history(ticker_meta, earliest, date.today())

    snap_dates = sorted({o.filled_at.date() for o in valid_orders} | {date.today()})  # type: ignore[union-attr]

    cumulative: Dict[str, float] = defaultdict(float)
    order_idx = 0
    result: List[PortfolioHistoryItem] = []

    for snap_date in snap_dates:
        while order_idx < len(valid_orders) and valid_orders[order_idx].filled_at.date() <= snap_date:  # type: ignore[union-attr]
            o = valid_orders[order_idx]
            cumulative[o.t212_ticker] += o.filled_quantity or 0.0
            order_idx += 1

        total_czk = 0.0
        for ticker, qty in cumulative.items():
            if qty <= 0:
                continue
            meta = ticker_meta.get(ticker)
            if not meta:
                continue
            yahoo_sym, currency = meta
            price = _price_on_date(close_series.get(yahoo_sym), snap_date)
            total_czk += _to_czk_on_date(price, currency, close_series, snap_date) * qty

        result.append(
            PortfolioHistoryItem(date=snap_date.isoformat(), value=round(total_czk, 0))
        )

    instruments_cache[cache_key] = result
    return result


@router.get("/strategy-comparison", response_model=List[StrategyComparisonItem])
def analytics_strategy_comparison(
    user_id: str = Depends(get_current_user_id),
) -> List[StrategyComparisonItem]:
    cache_key = f"strategy_comparison:{user_id}"
    if cache_key in instruments_cache:
        return instruments_cache[cache_key]  # type: ignore[return-value]

    filled_runs: List[Run] = Run.get_all_runs(
        limit=1000, status="FILLED", user_id=user_id
    )
    filled_runs = sorted(
        [r for r in filled_runs if r.distribution], key=lambda r: r.started_at
    )
    if not filled_runs:
        return []

    all_orders: List[Order] = Order.get_orders(status="FILLED", user_id=user_id)
    valid_orders = sorted(
        [o for o in all_orders if o.filled_at and o.filled_quantity],
        key=lambda o: o.filled_at,  # type: ignore[arg-type, return-value]
    )
    if not valid_orders:
        return []

    ticker_meta = {o.t212_ticker: (o.yahoo_symbol, o.currency) for o in valid_orders}
    earliest = min(r.started_at.date() for r in filled_runs)
    close_series = _fetch_price_history(ticker_meta, earliest, date.today())

    actual_qty: Dict[str, float] = defaultdict(float)
    baseline_qty: Dict[str, float] = defaultdict(float)
    order_idx = 0
    snap_dates = sorted({r.started_at.date() for r in filled_runs} | {date.today()})
    run_idx = 0

    result: List[StrategyComparisonItem] = []

    for snap_date in snap_dates:
        while (
            run_idx < len(filled_runs)
            and filled_runs[run_idx].started_at.date() <= snap_date
        ):
            run = filled_runs[run_idx]
            dist: Dict[str, Any] = run.distribution or {}
            mults: Dict[str, Any] = run.multipliers or {}
            planned_total = run.planned_total_czk or sum(dist.values())

            unboost = {t: czk / mults.get(t, 1.0) for t, czk in dist.items()}
            total_unboost = sum(unboost.values())
            if total_unboost > 0:
                baseline_dist = {
                    t: (v / total_unboost) * planned_total for t, v in unboost.items()
                }
            else:
                baseline_dist = {}

            run_date = run.started_at.date()
            for ticker, baseline_czk in baseline_dist.items():
                meta = ticker_meta.get(ticker)
                if not meta:
                    continue
                yahoo_sym, currency = meta
                price = _price_on_date(close_series.get(yahoo_sym), run_date)
                price_czk = _to_czk_on_date(price, currency, close_series, run_date)
                if price_czk > 0:
                    baseline_qty[ticker] += baseline_czk / price_czk
            run_idx += 1

        while order_idx < len(valid_orders) and valid_orders[order_idx].filled_at.date() <= snap_date:  # type: ignore[union-attr]
            o = valid_orders[order_idx]
            actual_qty[o.t212_ticker] += o.filled_quantity or 0.0
            order_idx += 1

        def portfolio_value(qty_map: Dict[str, float]) -> float:
            total = 0.0
            for ticker, qty in qty_map.items():
                if qty <= 0:
                    continue
                meta = ticker_meta.get(ticker)
                if not meta:
                    continue
                yahoo_sym, currency = meta
                price = _price_on_date(close_series.get(yahoo_sym), snap_date)
                total += _to_czk_on_date(price, currency, close_series, snap_date) * qty
            return round(total, 0)

        result.append(
            StrategyComparisonItem(
                date=snap_date.isoformat(),
                actual_value=portfolio_value(actual_qty),
                baseline_value=portfolio_value(baseline_qty),
            )
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
