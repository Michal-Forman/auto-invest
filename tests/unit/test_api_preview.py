# Standard library
from typing import Any, Dict

# Third-party
import pytest

# Local (api)
# Local
from api.routers.preview import preview

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
    from api.routers.preview import settings as preview_settings

    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    result = preview(amount=0)
    invest_amount = preview_settings.portfolio.invest_amount
    # adj_weight for VWCEd_EQ is 0.9 → invest_amount * 0.9
    vwce = next(r for r in result if r.ticker == "VWCEd_EQ")
    assert vwce.czk_amount == pytest.approx(invest_amount * 0.9)


def test_uses_provided_amount_when_positive(mocker):
    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    result = preview(amount=1000.0)
    # VWCEd_EQ adj_weight=0.9 → 1000*0.9=900 → normal
    vwce = next(r for r in result if r.ticker == "VWCEd_EQ")
    assert vwce.czk_amount == pytest.approx(900.0)
    assert vwce.note == "normal"


def test_note_dropped_when_below_12_5(mocker):
    # adj_weights give tiny amounts so raw_czk < 12.5
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.001, "BTC": 0.999})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    result = preview(amount=100.0)
    vwce = next(r for r in result if r.ticker == "VWCEd_EQ")
    # 100 * 0.001 = 0.1 < 12.5 → dropped
    assert vwce.note == "dropped"
    assert vwce.czk_amount == 0.0


def test_note_bumped_when_between_12_5_and_25(mocker):
    # adj_weight such that amount * weight is between 12.5 and 25
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.18, "BTC": 0.82})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    result = preview(amount=100.0)
    vwce = next(r for r in result if r.ticker == "VWCEd_EQ")
    # 100 * 0.18 = 18 → bumped to 25
    assert vwce.note == "bumped"
    assert vwce.czk_amount == 25.0


def test_note_normal_when_above_25(mocker):
    data = _ratio_data(adj_weights={"VWCEd_EQ": 0.9, "BTC": 0.1})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    result = preview(amount=1000.0)
    vwce = next(r for r in result if r.ticker == "VWCEd_EQ")
    # 1000 * 0.9 = 900 > 25 → normal
    assert vwce.note == "normal"
    assert vwce.czk_amount == pytest.approx(900.0)


def test_skips_tickers_not_in_adj_weights(mocker):
    # Only BTC in adj_weights
    data = _ratio_data(adj_weights={"BTC": 1.0})
    mocker.patch("api.routers.preview.build_ratio_data", return_value=data)
    result = preview(amount=1000.0)
    tickers = [r.ticker for r in result]
    assert "BTC" in tickers
    assert "VWCEd_EQ" not in tickers


def test_all_items_have_required_fields(mocker):
    mocker.patch("api.routers.preview.build_ratio_data", return_value=_BASE_RATIO_DATA)
    result = preview(amount=5000.0)
    for item in result:
        assert hasattr(item, "ticker")
        assert hasattr(item, "display_name")
        assert hasattr(item, "target_weight")
        assert hasattr(item, "drop_pct")
        assert hasattr(item, "multiplier")
        assert hasattr(item, "adjusted_weight")
        assert hasattr(item, "czk_amount")
        assert hasattr(item, "note")
