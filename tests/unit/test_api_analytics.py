# Standard library
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

# Third-party
from fastapi.testclient import TestClient
import pandas as pd
import pytest

# Local (api)
# Local
from api.cache import instruments_cache
from api.main import app
from api.routers.analytics import _get_price
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
    mocker.patch.object(Run, "get_all_runs", return_value=[])
    resp = client.get("/analytics/status")
    assert resp.status_code == 200
    assert resp.json() == []


def test_analytics_status_counts_statuses_correctly(mocker, make_run):
    runs = [
        make_run(status="FILLED"),
        make_run(status="FILLED"),
        make_run(status="FAILED"),
    ]
    mocker.patch.object(Run, "get_all_runs", return_value=runs)
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
    mock_df = MagicMock()
    mock_df.__getitem__ = MagicMock(return_value=btc_prices)
    mocker.patch("api.routers.analytics.yf.download", return_value=mock_df)

    resp = client.get("/analytics/portfolio-value")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    # qty=0.5 * price_at_snap_date(2026-03-03)=55000 = 27500
    assert data[0]["value"] == pytest.approx(27500.0)
