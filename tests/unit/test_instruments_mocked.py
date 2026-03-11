# Standard library
from dataclasses import replace
from typing import Any, Dict, cast
from unittest.mock import MagicMock

# Third-party
import pandas as pd  # type: ignore[import-untyped]
import pytest
from pytest_mock import MockerFixture

# Local
from core.instruments import Instruments
from core.settings import PortfolioSettings


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
        assert set(result["cash_distribution"].keys()) == set(
            result["multipliers"].keys()
        )


class TestGetFxRateToCzk:
    def test_czk_is_one(self, mocker: MockerFixture) -> None:
        mock_yf_ticker = mocker.patch("core.instruments.yf.Ticker")
        result = Instruments.get_fx_rate_to_czk("CZK")
        assert result == 1.0
        mock_yf_ticker.assert_not_called()

    def test_usd_rate(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [25.0]})
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("USD")
        assert result == pytest.approx(25.0)

    def test_gbx_divides_by_100(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [3000.0]})
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("GBX")
        assert result == pytest.approx(30.0)

    def test_eur_rate(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({"Close": [24.5]})
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_fx_rate_to_czk("EUR")
        assert result == pytest.approx(24.5)

    def test_raises_when_no_history(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        with pytest.raises(ValueError, match="No price data"):
            Instruments.get_fx_rate_to_czk("USD")


class TestGetT212Ratios:
    def test_returns_ticker_weight_dict_on_success(
        self, instruments: Instruments
    ) -> None:
        cast(MagicMock, instruments.t212.pie).return_value = {
            "req": None,
            "res": {
                "instruments": [
                    {"ticker": "VWCEd_EQ", "expectedShare": 0.6},
                    {"ticker": "CSPX_EQ", "expectedShare": 0.4},
                ]
            },
            "err": None,
        }
        result = instruments.get_t212_ratios()
        assert result == {"VWCEd_EQ": pytest.approx(0.6), "CSPX_EQ": pytest.approx(0.4)}

    def test_raises_on_api_error(self, instruments: Instruments) -> None:
        cast(MagicMock, instruments.t212.pie).return_value = {
            "req": None,
            "res": None,
            "err": "HTTP 429 Too Many Requests",
        }
        with pytest.raises(ValueError, match="T212 pie request failed"):
            instruments.get_t212_ratios()

    def test_raises_on_empty_instruments(self, instruments: Instruments) -> None:
        cast(MagicMock, instruments.t212.pie).return_value = {
            "req": None,
            "res": {"instruments": []},
            "err": None,
        }
        with pytest.raises(ValueError, match="do not sum to 1.0"):
            instruments.get_t212_ratios()


class TestGetDefaultRatios:
    def test_returns_combined_t212_and_btc_ratios(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            instruments,
            "get_t212_ratios",
            return_value={"VWCEd_EQ": 0.8, "CSPX_EQ": 0.2},
        )
        result = instruments.get_default_ratios()
        # T212 ratios scaled by t212_weight (95), BTC appended at btc_weight (0.05)
        assert "VWCEd_EQ" in result
        assert "CSPX_EQ" in result
        assert "BTC" in result
        assert result["BTC"] == pytest.approx(0.05)
        assert result["VWCEd_EQ"] == pytest.approx(0.8 * 95)


class TestGetAth:
    def test_returns_max_close_for_regular_ticker(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100.0, 200.0, 150.0]}
        )
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_ath("VWCEd_EQ")
        assert result == pytest.approx(200.0)

    def test_raises_on_empty_history(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        with pytest.raises(ValueError, match="No historical data"):
            Instruments.get_ath("VWCEd_EQ")

    def test_calls_get_btc_ath_for_btc(self, mocker: MockerFixture) -> None:
        mock_btc_ath = mocker.patch.object(
            Instruments, "_get_btc_ath", return_value=5_000_000.0
        )
        result = Instruments.get_ath("BTC")
        mock_btc_ath.assert_called_once()
        assert result == pytest.approx(5_000_000.0)


class TestGetCurrentPrice:
    def test_returns_latest_close(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100.0, 105.0, 110.0]}
        )
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        result = Instruments.get_current_price("VWCEd_EQ")
        assert result == pytest.approx(110.0)

    def test_raises_on_empty_history(self, mocker: MockerFixture) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mocker.patch("core.instruments.yf.Ticker", return_value=mock_ticker)
        with pytest.raises(ValueError, match="No price data"):
            Instruments.get_current_price("VWCEd_EQ")


class TestGetBtcPrice:
    def _make_ticker(self, fast_info: Any, history_data: Any = None) -> MagicMock:
        mock = MagicMock()
        mock.fast_info = fast_info
        if history_data is not None:
            mock.history.return_value = history_data
        return mock

    def test_uses_fast_info_last_price_when_available(
        self, mocker: MockerFixture
    ) -> None:
        btc_ticker = self._make_ticker({"lastPrice": 85_000.0})
        fx_ticker = self._make_ticker({"lastPrice": 23.5})
        mocker.patch("core.instruments.yf.Ticker", side_effect=[btc_ticker, fx_ticker])
        result = Instruments.get_btc_price()
        assert result == pytest.approx(85_000.0 * 23.5)

    def test_falls_back_to_history_close_when_fast_info_missing(
        self, mocker: MockerFixture
    ) -> None:
        btc_hist = pd.DataFrame({"Close": [85_000.0]})
        btc_ticker = self._make_ticker({}, history_data=btc_hist)
        fx_ticker = self._make_ticker({"lastPrice": 23.5})
        mocker.patch("core.instruments.yf.Ticker", side_effect=[btc_ticker, fx_ticker])
        result = Instruments.get_btc_price()
        assert result == pytest.approx(85_000.0 * 23.5)

    def test_converts_using_fx_rate(self, mocker: MockerFixture) -> None:
        btc_ticker = self._make_ticker({"lastPrice": 100_000.0})
        fx_ticker = self._make_ticker({"lastPrice": 22.0})
        mocker.patch("core.instruments.yf.Ticker", side_effect=[btc_ticker, fx_ticker])
        result = Instruments.get_btc_price()
        assert result == pytest.approx(2_200_000.0)


class TestGetBtcAth:
    def test_returns_max_across_all_tickers(self, mocker: MockerFixture) -> None:
        dates = pd.date_range("2020-01-01", periods=2)
        btc_df = pd.DataFrame({"Close": [10_000.0, 50_000.0]}, index=dates)
        fx_df = pd.DataFrame({"Close": [22.0, 25.0]}, index=dates)

        def mock_ticker(symbol: str) -> MagicMock:
            mock = MagicMock()
            if symbol == "BTC-USD":
                mock.history.return_value = btc_df
            else:
                mock.history.return_value = fx_df
            return mock

        mocker.patch("core.instruments.yf.Ticker", side_effect=mock_ticker)
        result = Instruments._get_btc_ath()
        # max(10000*22, 50000*25) = max(220000, 1250000) = 1250000
        assert result == pytest.approx(1_250_000.0)


class TestGetAdjustedRatios:
    def test_returns_adjusted_ratios_dict(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            instruments,
            "get_default_ratios",
            return_value={"VWCEd_EQ": 0.9, "BTC": 0.1},
        )
        mocker.patch.object(
            Instruments,
            "_adjust_ratio",
            side_effect=[
                {"multiplier": 1.5, "adjusted_value": 1.35},
                {"multiplier": 2.0, "adjusted_value": 0.2},
            ],
        )
        result = instruments.get_adjusted_ratios()
        assert "VWCEd_EQ" in result
        assert "BTC" in result
        assert result["VWCEd_EQ"]["multiplier"] == pytest.approx(1.5)
        assert result["BTC"]["multiplier"] == pytest.approx(2.0)


class TestIsBtcWithdrawalTresholdExceeded:
    @pytest.fixture(autouse=True)
    def setup(self, instruments: Instruments, mocker: MockerFixture) -> None:
        mocker.patch.object(Instruments, "get_btc_price", return_value=1_500_000.0)
        mocker.patch.object(instruments.coinmate, "btc_balance", return_value=0.01)

    def test_returns_true_when_above_threshold(self, instruments: Instruments) -> None:
        instruments.portfolio_settings = replace(
            instruments.portfolio_settings, btc_withdrawal_treshold=10_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is True

    def test_returns_false_when_below_threshold(self, instruments: Instruments) -> None:
        instruments.portfolio_settings = replace(
            instruments.portfolio_settings, btc_withdrawal_treshold=20_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is False

    def test_returns_true_when_exactly_at_threshold(
        self, instruments: Instruments
    ) -> None:
        # 0.01 BTC * 1_500_000 CZK/BTC = 15_000 CZK
        instruments.portfolio_settings = replace(
            instruments.portfolio_settings, btc_withdrawal_treshold=15_000
        )
        assert instruments.is_btc_withdrawal_treshold_exceeded() is True

    def test_uses_coinmate_balance(self, instruments: Instruments) -> None:
        instruments.is_btc_withdrawal_treshold_exceeded()
        cast(MagicMock, instruments.coinmate.btc_balance).assert_called_once()

    def test_uses_btc_price(
        self, instruments: Instruments, mocker: MockerFixture
    ) -> None:
        mock_price = mocker.patch.object(
            Instruments, "get_btc_price", return_value=1_500_000.0
        )
        instruments.is_btc_withdrawal_treshold_exceeded()
        mock_price.assert_called_once()
