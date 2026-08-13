# Standard library
from datetime import date, datetime, timezone
from uuid import UUID

# Third-party
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pandas as pd
import pytest

# Local (api)
# Local
from api.cache import instruments_cache
from api.main import app
from api.routers.analytics import _get_price, _to_czk_on_date
from core.db.orders import Order
from core.db.runs import Run

client = TestClient(app)


# ---------------------------------------------------------------------------
# /analytics/runs
# ---------------------------------------------------------------------------


def test_analytics_runs_empty_when_no_runs(mocker):
    mocker.patch.object(Run, "get_recent_runs", return_value=[])
    resp = client.get("/analytics/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_analytics_runs_returns_formatted_items(mocker, make_run):
    run = make_run(
        status="FILLED",
        started_at=datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc),
        planned_total_czk=5000.0,
    )
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/runs")
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert item["date"] == "2026-03-03"
    assert item["czk"] == 5000.0
    assert item["status"] == "FILLED"


def test_analytics_runs_default_limit_is_10(mocker):
    mock = mocker.patch.object(Run, "get_recent_runs", return_value=[])
    client.get("/analytics/runs")
    mock.assert_called_once_with(limit=10, user_id="test-user-id")


def test_analytics_runs_czk_defaults_zero_when_none(mocker, make_run):
    run = make_run(status="FILLED", planned_total_czk=None)
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/runs")
    assert resp.json()[0]["czk"] == 0.0


def test_analytics_runs_date_is_date_portion_of_started_at(mocker, make_run):
    run = make_run(started_at=datetime(2026, 1, 15, 14, 30, 0, tzinfo=timezone.utc))
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/runs")
    assert resp.json()[0]["date"] == "2026-01-15"


# ---------------------------------------------------------------------------
# /analytics/allocation
# ---------------------------------------------------------------------------


def test_analytics_allocation_empty_when_no_filled_runs(mocker, make_run):
    run = make_run(status="FINISHED", distribution={"VWCEd_EQ": 5000.0})
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/allocation")
    assert resp.json() == []


def test_analytics_allocation_skips_runs_without_distribution(mocker, make_run):
    run = make_run(status="FILLED", distribution=None)
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/allocation")
    assert resp.json() == []


def test_analytics_allocation_computes_percentage_correctly(mocker, make_run):
    run = make_run(status="FILLED", distribution={"A": 3000, "B": 2000})
    mocker.patch.object(Run, "get_recent_runs", return_value=[run])
    resp = client.get("/analytics/allocation")
    data = resp.json()
    assert len(data) == 1
    pct = data[0]["data"]
    assert pct["A"] == pytest.approx(60.0)
    assert pct["B"] == pytest.approx(40.0)


def test_analytics_allocation_default_limit_is_8(mocker):
    mock = mocker.patch.object(Run, "get_recent_runs", return_value=[])
    client.get("/analytics/allocation")
    mock.assert_called_once_with(limit=8, user_id="test-user-id")


# ---------------------------------------------------------------------------
# /analytics/status
# ---------------------------------------------------------------------------


def test_analytics_status_empty_when_no_runs(mocker):
    mocker.patch.object(Run, "get_status_counts", return_value=[])
    resp = client.get("/analytics/status")
    assert resp.status_code == 200
    assert resp.json() == []


def test_analytics_status_counts_statuses_correctly(mocker):
    rows = [
        {"status": "FILLED"},
        {"status": "FILLED"},
        {"status": "FAILED"},
    ]
    mocker.patch.object(Run, "get_status_counts", return_value=rows)
    resp = client.get("/analytics/status")
    counts = {item["status"]: item["count"] for item in resp.json()}
    assert counts["FILLED"] == 2
    assert counts["FAILED"] == 1


# ---------------------------------------------------------------------------
# _get_price helper
# ---------------------------------------------------------------------------


def _make_series(*values_and_dates) -> pd.Series:
    """Build a DatetimeIndex Series from (date_str, value) pairs."""
    dates, values = zip(*values_and_dates)
    return pd.Series(list(values), index=pd.DatetimeIndex(list(dates)))


def test_get_price_returns_price_for_exact_date():
    series = _make_series(("2026-03-01", 100.0), ("2026-03-05", 110.0))
    result = _get_price({"SYM": series}, "SYM", date(2026, 3, 5))
    assert result == pytest.approx(110.0)


def test_get_price_returns_last_available_price_for_missing_date():
    series = _make_series(("2026-03-01", 100.0), ("2026-03-05", 110.0))
    # 2026-03-03 is between the two dates → should return 100 (last price on or before)
    result = _get_price({"SYM": series}, "SYM", date(2026, 3, 3))
    assert result == pytest.approx(100.0)


def test_get_price_returns_zero_for_missing_symbol():
    result = _get_price({}, "MISSING", date(2026, 3, 1))
    assert result == 0.0


def test_get_price_returns_zero_for_empty_series():
    empty = pd.Series([], dtype=float)
    result = _get_price({"SYM": empty}, "SYM", date(2026, 3, 1))
    assert result == 0.0


# ---------------------------------------------------------------------------
# /analytics/portfolio-value
# ---------------------------------------------------------------------------


def test_portfolio_value_empty_when_no_filled_orders(mocker):
    mocker.patch.object(Order, "get_orders", return_value=[])
    resp = client.get("/analytics/portfolio-value")
    assert resp.status_code == 200
    assert resp.json() == []


def test_portfolio_value_served_from_cache(mocker):
    instruments_cache["portfolio_value:test-user-id"] = [
        {"date": "2026-03-03", "value": 12345.0}
    ]
    mock_get_orders = mocker.patch.object(Order, "get_orders")
    resp = client.get("/analytics/portfolio-value")
    assert resp.status_code == 200
    mock_get_orders.assert_not_called()


def test_portfolio_value_happy_path_with_mocked_yfinance(mocker, make_order, make_run):
    instruments_cache.clear()
    filled_dt = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
    order = make_order(
        t212_ticker="BTC",
        yahoo_symbol="BTC-USD",
        currency="CZK",
        exchange="COINMATE",
        instrument_type="CRYPTO",
        filled_at=filled_dt,
        filled_quantity=0.5,
        status="FILLED",
    )
    run = make_run(
        status="FILLED", started_at=datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
    )

    mocker.patch.object(Order, "get_orders", return_value=[order])
    mocker.patch.object(Run, "get_all_runs", return_value=[run])

    btc_prices = _make_series(
        ("2026-02-22", 50000.0), ("2026-03-01", 50000.0), ("2026-03-03", 55000.0)
    )
    # BTC-USD is USD-denominated so yf.download fetches BTC-USD + USDCZK=X (2 symbols).
    # Use FX rate 1.0 so expected value = qty * usd_price * fx = 0.5 * 55000 * 1.0 = 27500.
    fx_series = _make_series(("2026-03-03", 1.0))
    _patch_prices(mocker, {"BTC-USD": btc_prices, "USDCZK=X": fx_series})

    resp = client.get("/analytics/portfolio-value")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    # qty=0.5 * usd_price=55000 * fx=1.0 = 27500
    assert data[0]["value"] == pytest.approx(27500.0)


# ---------------------------------------------------------------------------
# /analytics/profit-loss
# ---------------------------------------------------------------------------


def _download_frame(series_by_symbol) -> pd.DataFrame:
    """Build a frame shaped like a real yf.download result.

    A single-symbol download returns flat OHLC columns; a multi-symbol one returns
    MultiIndex ("Close", symbol) columns. Real frames matter here — the production code
    inspects `.empty` and tests membership, which a MagicMock silently answers wrong.
    """
    if len(series_by_symbol) == 1:
        series = next(iter(series_by_symbol.values()))
        return pd.DataFrame({"Close": series})
    frame = pd.concat(series_by_symbol.values(), axis=1, keys=series_by_symbol.keys())
    frame.columns = pd.MultiIndex.from_product([["Close"], list(series_by_symbol)])
    return frame


def _patch_prices(mocker, series_by_symbol):
    """Patch yf.download so _compute_holdings_czk sees the given close series."""
    mocker.patch(
        "api.routers.analytics.yf.download",
        return_value=_download_frame(series_by_symbol),
    )


def _btc_order(make_order, **overrides):
    """A filled BTC order priced in CZK — one symbol, so no FX leg to mock."""
    defaults = dict(
        t212_ticker="BTC",
        yahoo_symbol="BTC-CZK",
        currency="CZK",
        exchange="COINMATE",
        instrument_type="CRYPTO",
        status="FILLED",
        filled_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        filled_quantity=1.0,
        filled_total_czk=1000.0,
    )
    defaults.update(overrides)
    return make_order(**defaults)


def test_profit_loss_counts_orders_from_failed_runs(mocker, make_order, make_run):
    """The regression: a FAILED run's filled orders must contribute cost, not just value.

    Two identical orders, one in a FILLED run and one in a FAILED run. Both shares are
    held, so both purchases must appear in total_invested.
    """
    instruments_cache.clear()
    orders = [
        _btc_order(make_order, run_id=UUID("11111111-1111-1111-1111-111111111111")),
        _btc_order(make_order, run_id=UUID("22222222-2222-2222-2222-222222222222")),
    ]
    mocker.patch.object(Order, "get_orders", return_value=orders)
    # Only one run reached FILLED — the other expired to FAILED and is not returned.
    mocker.patch.object(Run, "get_all_runs", return_value=[make_run(status="FILLED")])
    _patch_prices(mocker, {"BTC-CZK": _make_series(("2026-03-03", 1000.0))})

    data = client.get("/analytics/profit-loss").json()

    assert data["total_invested_czk"] == pytest.approx(2000.0)
    assert data["current_value_czk"] == pytest.approx(2000.0)
    assert data["gain_pct"] == pytest.approx(0.0)


def test_profit_loss_gain_is_zero_when_value_equals_cost(mocker, make_order, make_run):
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[_btc_order(make_order)])
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    _patch_prices(mocker, {"BTC-CZK": _make_series(("2026-03-03", 1000.0))})

    data = client.get("/analytics/profit-loss").json()

    assert data["gain_czk"] == pytest.approx(0.0)
    assert data["gain_pct"] == pytest.approx(0.0)


def test_profit_loss_reports_a_real_gain(mocker, make_order, make_run):
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[_btc_order(make_order)])
    mocker.patch.object(Run, "get_all_runs", return_value=[make_run(status="FILLED")])
    _patch_prices(mocker, {"BTC-CZK": _make_series(("2026-03-03", 1100.0))})

    data = client.get("/analytics/profit-loss").json()

    assert data["total_invested_czk"] == pytest.approx(1000.0)
    assert data["current_value_czk"] == pytest.approx(1100.0)
    assert data["gain_pct"] == pytest.approx(10.0)


def test_profit_loss_falls_back_to_total_czk_when_fill_total_missing(
    mocker, make_order, make_run
):
    instruments_cache.clear()
    order = _btc_order(make_order, filled_total_czk=None, total_czk=900.0)
    mocker.patch.object(Order, "get_orders", return_value=[order])
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    _patch_prices(mocker, {"BTC-CZK": _make_series(("2026-03-03", 900.0))})

    data = client.get("/analytics/profit-loss").json()

    assert data["total_invested_czk"] == pytest.approx(900.0)


def test_profit_loss_filled_run_count_is_independent_of_invested(
    mocker, make_order, make_run
):
    """filled_run_count stays a run-health figure and must not drive the money."""
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[_btc_order(make_order)])
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    _patch_prices(mocker, {"BTC-CZK": _make_series(("2026-03-03", 1000.0))})

    data = client.get("/analytics/profit-loss").json()

    assert data["filled_run_count"] == 0
    assert data["total_invested_czk"] == pytest.approx(1000.0)


def test_profit_loss_zero_invested_does_not_divide_by_zero(mocker):
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[])
    mocker.patch.object(Run, "get_all_runs", return_value=[])

    data = client.get("/analytics/profit-loss").json()

    assert data["total_invested_czk"] == 0
    assert data["gain_pct"] == 0.0


# ---------------------------------------------------------------------------
# /analytics/strategy-comparison
# ---------------------------------------------------------------------------


def test_strategy_comparison_includes_failed_runs(mocker, make_order, make_run):
    """Both strategies must deploy the same capital, whatever the run's status.

    The actual portfolio is built from orders, so a baseline built from FILLED runs
    only would be starved of the capital spent inside FAILED runs.
    """
    instruments_cache.clear()
    failed_run_id = UUID("22222222-2222-2222-2222-222222222222")
    orders = [
        _btc_order(make_order, run_id=failed_run_id, filled_quantity=1.0),
    ]
    failed_run = make_run(
        id=failed_run_id,
        status="FAILED",
        distribution={"BTC": 1000.0},
        multipliers={"BTC": 2.0},
        planned_total_czk=1000.0,
    )
    mocker.patch.object(Order, "get_orders", return_value=orders)
    mocker.patch.object(Run, "get_all_runs", return_value=[failed_run])
    mocker.patch(
        "api.routers.analytics._fetch_price_history",
        return_value={"BTC-CZK": _make_series(("2026-03-01", 1000.0))},
    )

    data = client.get("/analytics/strategy-comparison").json()

    assert data, "a FAILED run with filled orders must still be compared"
    # One instrument, so re-weighting cannot change anything: both sides are equal.
    assert data[-1]["actual_value"] == pytest.approx(data[-1]["baseline_value"])
    assert data[-1]["actual_value"] > 0


def test_strategy_comparison_baseline_uses_deployed_not_planned(
    mocker, make_order, make_run
):
    """A run that planned 1000 but only filled 600 must give the baseline 600."""
    instruments_cache.clear()
    run_id = UUID("33333333-3333-3333-3333-333333333333")
    orders = [
        _btc_order(
            make_order, run_id=run_id, filled_quantity=0.6, filled_total_czk=600.0
        ),
    ]
    run = make_run(
        id=run_id,
        status="FAILED",
        distribution={"BTC": 600.0, "VWCEd_EQ": 400.0},  # VWCE leg never filled
        multipliers={"BTC": 1.0, "VWCEd_EQ": 1.0},
        planned_total_czk=1000.0,
    )
    mocker.patch.object(Order, "get_orders", return_value=orders)
    mocker.patch.object(Run, "get_all_runs", return_value=[run])
    mocker.patch(
        "api.routers.analytics._fetch_price_history",
        return_value={"BTC-CZK": _make_series(("2026-03-01", 1000.0))},
    )

    data = client.get("/analytics/strategy-comparison").json()

    # Baseline is restricted to the ticker that actually filled and gets the 600 CZK
    # that was really deployed — not the 1000 that was planned.
    assert data[-1]["baseline_value"] == pytest.approx(600.0)
    assert data[-1]["actual_value"] == pytest.approx(600.0)


def test_strategy_comparison_skips_runs_with_no_filled_orders(
    mocker, make_order, make_run
):
    instruments_cache.clear()
    run_with_orders = UUID("44444444-4444-4444-4444-444444444444")
    empty_run = make_run(
        id=UUID("55555555-5555-5555-5555-555555555555"),
        status="FAILED",
        distribution={"BTC": 1000.0},
        multipliers={"BTC": 1.0},
    )
    orders = [_btc_order(make_order, run_id=run_with_orders)]
    run = make_run(
        id=run_with_orders,
        status="FILLED",
        distribution={"BTC": 1000.0},
        multipliers={"BTC": 1.0},
    )
    mocker.patch.object(Order, "get_orders", return_value=orders)
    mocker.patch.object(Run, "get_all_runs", return_value=[run, empty_run])
    mocker.patch(
        "api.routers.analytics._fetch_price_history",
        return_value={"BTC-CZK": _make_series(("2026-03-01", 1000.0))},
    )

    data = client.get("/analytics/strategy-comparison").json()

    # The empty run contributes nothing to either side rather than skewing the baseline.
    assert data[-1]["baseline_value"] == pytest.approx(data[-1]["actual_value"])


# ---------------------------------------------------------------------------
# Partial price downloads
#
# yfinance answers a rate-limited request with a short series instead of an error.
# Historical snapshots then reprice against data that is not there, which renders as a
# flat line that "spikes" on the final point — plausible enough to be believed. These
# tests pin the contract: incomplete data fails loudly and is never cached.
# ---------------------------------------------------------------------------


_TODAY = date.today().isoformat()


def _truncating_download(full_by_symbol, keep_from):
    """Stand in for yf.download, serving only rows on/after keep_from for FX symbols."""

    def _download(symbols, **kwargs):
        requested = [symbols] if isinstance(symbols, str) else list(symbols)
        served = {}
        for sym in requested:
            series = full_by_symbol[sym]
            if sym.endswith("=X"):
                series = series[series.index >= pd.Timestamp(keep_from)]
            served[sym] = series
        return _download_frame(served)

    return _download


def _usd_order(make_order, **overrides):
    defaults = dict(
        t212_ticker="BX_US_EQ",
        yahoo_symbol="BX",
        currency="USD",
        exchange="T212",
        instrument_type="STOCK",
        status="FILLED",
        filled_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        filled_quantity=1.0,
        filled_total_czk=1000.0,
    )
    defaults.update(overrides)
    return make_order(**defaults)


def test_portfolio_history_rejects_truncated_fx_history(mocker, make_order, make_run):
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[_usd_order(make_order)])
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    mocker.patch("api.routers.analytics.time.sleep")
    full = {
        "BX": _make_series(("2026-03-01", 100.0), (_TODAY, 120.0)),
        "USDCZK=X": _make_series(("2026-03-01", 22.0), (_TODAY, 23.0)),
    }
    mocker.patch(
        "api.routers.analytics.yf.download",
        side_effect=_truncating_download(full, _TODAY),
    )

    resp = client.get("/analytics/portfolio-history")

    assert resp.status_code == 503
    assert "USDCZK=X" in resp.json()["detail"]
    # A bad response must not be served for the next 15 minutes.
    assert "portfolio_history:test-user" not in instruments_cache


def test_portfolio_history_retries_and_succeeds_on_complete_data(
    mocker, make_order, make_run
):
    """The retry path exists for flaky bulk downloads, not to paper over real gaps."""
    instruments_cache.clear()
    mocker.patch.object(Order, "get_orders", return_value=[_usd_order(make_order)])
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    mocker.patch("api.routers.analytics.time.sleep")
    full = {
        "BX": _make_series(("2026-03-01", 100.0), (_TODAY, 120.0)),
        "USDCZK=X": _make_series(("2026-03-01", 22.0), (_TODAY, 23.0)),
    }
    calls = {"n": 0}

    def _flaky(symbols, **kwargs):
        calls["n"] += 1
        keep = _TODAY if calls["n"] == 1 else "2026-01-01"
        return _truncating_download(full, keep)(symbols, **kwargs)

    mocker.patch("api.routers.analytics.yf.download", side_effect=_flaky)

    resp = client.get("/analytics/portfolio-history")

    assert resp.status_code == 200
    assert calls["n"] > 1, "the incomplete bulk download must be retried"
    assert resp.json()[0]["value"] == pytest.approx(2200.0)  # 1 share * 100 USD * 22


def test_price_on_date_before_series_start_uses_earliest_known_price():
    """Zero would erase the holding from that snapshot; the first known price will not."""
    series = _make_series(("2026-03-05", 110.0), ("2026-03-10", 120.0))
    assert _get_price({"SYM": series}, "SYM", date(2026, 3, 1)) == pytest.approx(110.0)


def test_to_czk_on_date_refuses_to_return_an_unconverted_price():
    """The old fallback returned the raw USD price, understating the value ~21x."""
    with pytest.raises(HTTPException) as excinfo:
        empty = pd.Series([], dtype=float)
        _to_czk_on_date(100.0, "USD", {"USDCZK=X": empty}, date(2026, 3, 1))
    assert excinfo.value.status_code == 503
