# Standard library
from typing import Any, Dict

# Third-party
from fastapi.testclient import TestClient
import pytest

# Local (api)
# Local
from api.main import app

client = TestClient(app)

_BASE_RATIO_DATA: Dict[str, Any] = {
    "default_ratios": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "target_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "ath_prices": {"VWCEd_EQ": 100.0, "BTC": 50000.0},
    "current_prices": {"VWCEd_EQ": 80.0, "BTC": 40000.0},
    "drop_pcts": {"VWCEd_EQ": 20.0, "BTC": 20.0},
    "multipliers": {"VWCEd_EQ": 1.25, "BTC": 1.25},
    "adj_weights": {"VWCEd_EQ": 0.9, "BTC": 0.1},
    "next_czk": {"VWCEd_EQ": 4500.0, "BTC": 500.0},
}


def _ratio_data(**overrides) -> Dict[str, Any]:
    data = {**_BASE_RATIO_DATA}
    data.update(overrides)
    return data


def test_uses_settings_invest_amount_when_amount_is_zero(mocker):
    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    resp = client.get("/preview")
    assert resp.status_code == 200
    # test UserSettings has invest_amount=5000.0; adj_weight for VWCEd_EQ=0.9
    vwce = next(r for r in resp.json() if r["ticker"] == "VWCEd_EQ")
    assert vwce["czk_amount"] == pytest.approx(5000.0 * 0.9)


def test_uses_provided_amount_when_positive(mocker):
    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    resp = client.get("/preview?amount=1000")
    assert resp.status_code == 200
    vwce = next(r for r in resp.json() if r["ticker"] == "VWCEd_EQ")
    assert vwce["czk_amount"] == pytest.approx(900.0)
    assert vwce["note"] == "normal"


def test_note_dropped_when_below_12_5(mocker):
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.001, "BTC": 0.999})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    resp = client.get("/preview?amount=100")
    vwce = next(r for r in resp.json() if r["ticker"] == "VWCEd_EQ")
    assert vwce["note"] == "dropped"
    assert vwce["czk_amount"] == 0.0


def test_note_bumped_when_between_12_5_and_25(mocker):
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.18, "BTC": 0.82})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    resp = client.get("/preview?amount=100")
    vwce = next(r for r in resp.json() if r["ticker"] == "VWCEd_EQ")
    assert vwce["note"] == "bumped"
    assert vwce["czk_amount"] == 25.0


def test_note_normal_when_above_25(mocker):
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.9, "BTC": 0.1})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    resp = client.get("/preview?amount=1000")
    vwce = next(r for r in resp.json() if r["ticker"] == "VWCEd_EQ")
    assert vwce["note"] == "normal"
    assert vwce["czk_amount"] == pytest.approx(900.0)


def test_skips_tickers_not_in_adj_weights(mocker):
    data = _ratio_data(adj_weights={"BTC": 1.0})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    resp = client.get("/preview?amount=1000")
    tickers = [r["ticker"] for r in resp.json()]
    assert "BTC" in tickers
    assert "VWCEd_EQ" not in tickers


def test_all_items_have_required_fields(mocker):
    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    resp = client.get("/preview?amount=5000")
    for item in resp.json():
        assert "ticker" in item
        assert "display_name" in item
        assert "target_weight" in item
        assert "drop_pct" in item
        assert "multiplier" in item
        assert "adjusted_weight" in item
        assert "czk_amount" in item
        assert "note" in item
