# Standard library
from typing import Any, Dict

# Third-party
from fastapi.testclient import TestClient
import pytest

# Local (api)
# Local
from api.cache import instruments_cache
from api.main import app
from api.routers.instruments import _apply_cap
from core.instruments import Instruments

client = TestClient(app)

_CACHE_KEY = "instruments:test-user-id"

_FAKE_RATIO_DATA: Dict[str, Any] = {
    "default_ratios": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "target_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "ath_prices": {"VWCEd_EQ": 100.0, "BTC": 50000.0},
    "current_prices": {"VWCEd_EQ": 80.0, "BTC": 40000.0},
    "drop_pcts": {"VWCEd_EQ": 20.0, "BTC": 20.0},
    "multipliers": {"VWCEd_EQ": 1.25, "BTC": 1.25},
    "adjusted_values": {"VWCEd_EQ": 1.125, "BTC": 0.125},
    "adj_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "next_czk": {"VWCEd_EQ": 4500.0, "BTC": 500.0},
}


# --- _apply_cap pure function tests ---


def test_none_cap_returns_raw():
    assert _apply_cap(80.0, "none") == 80.0


def test_soft_cap_clamps_at_75():
    assert _apply_cap(80.0, "soft") == 75.0


def test_soft_cap_no_clamp_below_75():
    assert _apply_cap(50.0, "soft") == 50.0


def test_hard_cap_resets_at_90():
    assert _apply_cap(90.0, "hard") == 0.0


def test_hard_cap_clamps_below_90():
    assert _apply_cap(89.0, "hard") == 75.0


def test_hard_cap_unchanged_below_75():
    assert _apply_cap(50.0, "hard") == 50.0


# --- Endpoint tests ---


def test_returns_200_with_list(mocker):
    mocker.patch(
        "api.routers.instruments.build_ratio_data", return_value=_FAKE_RATIO_DATA
    )
    resp = client.get("/instruments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_one_item_per_ticker_in_default_ratios(mocker):
    mocker.patch(
        "api.routers.instruments.build_ratio_data", return_value=_FAKE_RATIO_DATA
    )
    resp = client.get("/instruments")
    tickers = [i["ticker"] for i in resp.json()]
    assert "VWCEd_EQ" in tickers
    assert "BTC" in tickers


def test_btc_exchange_is_coinmate(mocker):
    mocker.patch(
        "api.routers.instruments.build_ratio_data", return_value=_FAKE_RATIO_DATA
    )
    resp = client.get("/instruments")
    btc = next(i for i in resp.json() if i["ticker"] == "BTC")
    assert btc["exchange"] == "Coinmate"


def test_non_btc_exchange_is_t212(mocker):
    mocker.patch(
        "api.routers.instruments.build_ratio_data", return_value=_FAKE_RATIO_DATA
    )
    resp = client.get("/instruments")
    vwce = next(i for i in resp.json() if i["ticker"] == "VWCEd_EQ")
    assert vwce["exchange"] == "T212"


def test_response_schema_all_fields_present(mocker):
    mocker.patch(
        "api.routers.instruments.build_ratio_data", return_value=_FAKE_RATIO_DATA
    )
    resp = client.get("/instruments")
    required = {
        "ticker",
        "display_name",
        "exchange",
        "cap_type",
        "target_weight",
        "ath_price",
        "current_price",
        "drop_pct",
        "multiplier",
        "adjusted_weight",
        "next_czk",
    }
    for item in resp.json():
        assert required.issubset(item.keys())


def test_result_served_from_cache(mocker):
    # Pre-populate cache; expensive computation should not run if cache is hit.
    instruments_cache[_CACHE_KEY] = _FAKE_RATIO_DATA
    mock_get_ratios = mocker.patch.object(Instruments, "get_default_ratios")
    client.get("/instruments")
    mock_get_ratios.assert_not_called()
