# Standard library
from typing import Dict
from unittest.mock import MagicMock

# Third-party
import pandas as pd  # type: ignore[import-untyped]
import pytest
from pytest_mock import MockerFixture

# Local
from instruments import Instruments
from settings import PortfolioSettings


class TestAdjustRatio:
    def test_no_cap_25pct_drop(self, mocker: MockerFixture) -> None:
        # VWCEd_EQ has cap "none": drop 25% → multiplier = 100/75 ≈ 1.333
        mocker.patch.object(Instruments, "get_ath", return_value=200.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=150.0)
        result = Instruments._adjust_ratio("VWCEd_EQ", 1.0)
        assert result["multiplier"] == pytest.approx(100 / 75)

    def test_soft_cap_clamps_at_75pct(self, mocker: MockerFixture) -> None:
        # SC0Ud_EQ has cap "soft": drop 90% → capped to 75% → multiplier = 100/25 = 4.0
        mocker.patch.object(Instruments, "get_ath", return_value=200.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=20.0)
        result = Instruments._adjust_ratio("SC0Ud_EQ", 1.0)
        assert result["multiplier"] == pytest.approx(4.0)

    def test_hard_cap_resets_above_90pct(self, mocker: MockerFixture) -> None:
        # BTC has cap "hard": drop 95% → reset to 0% → multiplier = 1.0
        mocker.patch.object(Instruments, "get_ath", return_value=200.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=10.0)
        result = Instruments._adjust_ratio("BTC", 1.0)
        assert result["multiplier"] == pytest.approx(1.0)

    def test_adjusted_value_scales_with_multiplier(self, mocker: MockerFixture) -> None:
        # VWCEd_EQ, drop 50% → multiplier = 2.0 → adjusted_value = 10.0 * 2.0 = 20.0
        mocker.patch.object(Instruments, "get_ath", return_value=200.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=100.0)
        result = Instruments._adjust_ratio("VWCEd_EQ", 10.0)
        assert result["adjusted_value"] == pytest.approx(20.0)


class TestDistributeCash:
    def test_proportional_split(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            instruments,
            "get_adjusted_ratios",
            return_value={
                "VWCEd_EQ": {"multiplier": 1.0, "adjusted_value": 1.0},
                "BTC": {"multiplier": 2.0, "adjusted_value": 3.0},
            },
        )
        result = instruments.distribute_cash()
        dist = result["cash_distribution"]
        # total adjusted = 4.0; VWCEd_EQ → 1/4 of 5000 = 1250, BTC → 3/4 = 3750
        assert dist["VWCEd_EQ"] == pytest.approx(1250.0)
        assert dist["BTC"] == pytest.approx(3750.0)
        assert sum(dist.values()) == pytest.approx(5000.0)

    def test_instrument_below_min_dropped(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            instruments,
            "get_adjusted_ratios",
            return_value={
                "VWCEd_EQ": {"multiplier": 1.0, "adjusted_value": 1000.0},
                "SC0Ud_EQ": {"multiplier": 1.0, "adjusted_value": 0.001},
            },
        )
        result = instruments.distribute_cash()
        # SC0Ud_EQ gets ~0.005 CZK → below 12.5 → dropped
        assert "SC0Ud_EQ" not in result["cash_distribution"]
        assert "VWCEd_EQ" in result["cash_distribution"]

    def test_returns_matching_multiplier_keys(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            instruments,
            "get_adjusted_ratios",
            return_value={
                "VWCEd_EQ": {"multiplier": 1.5, "adjusted_value": 2500.0},
                "BTC": {"multiplier": 2.0, "adjusted_value": 2500.0},
            },
        )
        result = instruments.distribute_cash()
        assert set(result["cash_distribution"].keys()) == set(result["multipliers"].keys())


class TestGetFxRateToCzk:
    def test_czk_is_one(self, mocker: MockerFixture) -> None:
        mock_yf_ticker = mocker.patch("instruments.yf.Ticker")
        result = Instruments.get_fx_rate_to_czk("CZK")
        assert result == 1.0
        mock_yf_ticker.assert_not_called()

    def test_usd_rate(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [25.0]})
        mocker.patch("instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("USD")
        assert result == pytest.approx(25.0)

    def test_gbx_divides_by_100(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [3000.0]})
        mocker.patch("instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("GBX")
        assert result == pytest.approx(30.0)

    def test_eur_rate(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [24.5]})
        mocker.patch("instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("EUR")
        assert result == pytest.approx(24.5)
