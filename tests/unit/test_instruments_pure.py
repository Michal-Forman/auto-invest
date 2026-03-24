# Standard library
from decimal import Decimal

# Third-party
import pytest

# Local
from core.instruments import Instruments


class TestSoftCap:
    def test_zero_drop(self) -> None:
        assert Instruments._soft_cap(Decimal("0")) == Decimal("0")

    def test_below_cap(self) -> None:
        assert Instruments._soft_cap(Decimal("50")) == Decimal("50")

    def test_at_cap(self) -> None:
        assert Instruments._soft_cap(Decimal("75")) == Decimal("75")

    def test_above_cap(self) -> None:
        assert Instruments._soft_cap(Decimal("80")) == Decimal("75")


class TestHardCap:
    def test_below_soft_cap(self) -> None:
        assert Instruments._hard_cap(Decimal("50")) == Decimal("50")

    def test_at_soft_cap(self) -> None:
        assert Instruments._hard_cap(Decimal("75")) == Decimal("75")

    def test_above_soft_cap(self) -> None:
        assert Instruments._hard_cap(Decimal("80")) == Decimal("75")

    def test_at_reset_threshold(self) -> None:
        assert Instruments._hard_cap(Decimal("90")) == Decimal("0")

    def test_above_reset_threshold(self) -> None:
        assert Instruments._hard_cap(Decimal("95")) == Decimal("0")


class TestGetYahooSymbol:
    def test_known_ticker(self) -> None:
        assert Instruments.get_yahoo_symbol("VWCEd_EQ") == "VWCE.DE"

    def test_unknown_ticker_raises(self) -> None:
        with pytest.raises(ValueError):
            Instruments.get_yahoo_symbol("UNKNOWN_TICKER")


class TestValidateT212Ratios:
    def test_ratios_sum_to_one(self, instruments: Instruments) -> None:
        assert instruments._validate_t212_ratios({"A": Decimal("0.5"), "B": Decimal("0.5")}) is True

    def test_ratios_do_not_sum_to_one(self, instruments: Instruments) -> None:
        assert instruments._validate_t212_ratios({"A": Decimal("0.5"), "B": Decimal("0.499")}) is False

    def test_ratios_within_tolerance(self, instruments: Instruments) -> None:
        # 0.5 + 0.5000004 = 1.0000004, difference from 1.0 is 4e-7 < 1e-6
        assert instruments._validate_t212_ratios({"A": Decimal("0.5"), "B": Decimal("0.5000004")}) is True


class TestValidateCashDistribution:
    def test_all_above_minimum_unchanged(self, instruments: Instruments) -> None:
        dist = {"A": Decimal("2000"), "B": Decimal("3000")}
        result = instruments._validate_cash_distribution(dist)
        assert result == {"A": Decimal("2000"), "B": Decimal("3000")}

    def test_amount_between_half_min_and_min_bumped(
        self, instruments: Instruments
    ) -> None:
        # 24.0 is between 12.5 (half of MIN_ORDER_CZK) and 25 (MIN_ORDER_CZK)
        dist = {"A": Decimal("4976"), "B": Decimal("24")}
        result = instruments._validate_cash_distribution(dist)
        assert result["B"] == Decimal("25")

    def test_amount_at_or_below_half_minimum_dropped(
        self, instruments: Instruments
    ) -> None:
        # 7.0 <= 12.5 (MIN_ORDER_CZK / 2), so B is dropped entirely
        dist = {"A": Decimal("4993"), "B": Decimal("7")}
        result = instruments._validate_cash_distribution(dist)
        assert "B" not in result
        assert "A" in result

    def test_sum_not_equal_invest_amount_raises(self, instruments: Instruments) -> None:
        with pytest.raises(ValueError):
            instruments._validate_cash_distribution({"A": Decimal("2000"), "B": Decimal("2000")})
