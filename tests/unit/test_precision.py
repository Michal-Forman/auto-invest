# Standard library
from decimal import Decimal

# Local
from core.precision import (
    quantize_btc,
    quantize_czk,
    quantize_fx,
    quantize_shares,
    to_decimal,
)


class TestToDecimal:
    def test_float_avoids_imprecision(self) -> None:
        assert to_decimal(0.1) + to_decimal(0.2) == Decimal("0.3")

    def test_int_input(self) -> None:
        assert to_decimal(5) == Decimal("5")

    def test_string_input(self) -> None:
        assert to_decimal("1.23456789") == Decimal("1.23456789")

    def test_decimal_input_passthrough(self) -> None:
        d = Decimal("3.14")
        assert to_decimal(d) is d


class TestQuantizeBtc:
    def test_rounds_to_8dp(self) -> None:
        assert quantize_btc(Decimal("0.123456789")) == Decimal("0.12345679")

    def test_exact_8dp_unchanged(self) -> None:
        assert quantize_btc(Decimal("0.00000001")) == Decimal("0.00000001")


class TestQuantizeCzk:
    def test_rounds_to_2dp(self) -> None:
        assert quantize_czk(Decimal("100.555")) == Decimal("100.56")

    def test_exact_2dp_unchanged(self) -> None:
        assert quantize_czk(Decimal("100.50")) == Decimal("100.50")


class TestQuantizeShares:
    def test_rounds_to_3dp(self) -> None:
        assert quantize_shares(Decimal("1.23456")) == Decimal("1.235")


class TestQuantizeFx:
    def test_rounds_to_4dp(self) -> None:
        assert quantize_fx(Decimal("25.12345")) == Decimal("25.1235")
