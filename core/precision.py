# Standard library
from decimal import ROUND_HALF_UP, Decimal
from typing import Union

PRECISION_BTC = Decimal("0.00000001")  # 8 dp
PRECISION_SHARES = Decimal("0.001")  # 3 dp
PRECISION_CZK = Decimal("0.01")  # 2 dp
PRECISION_FX = Decimal("0.0001")  # 4 dp
RATIO_TOLERANCE = Decimal("1E-6")


def to_decimal(value: Union[float, int, str, Decimal]) -> Decimal:
    """Convert a float/int/str/Decimal to Decimal via str() to avoid float imprecision."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_btc(value: Decimal) -> Decimal:
    """Quantize to 8 decimal places (BTC/crypto standard)."""
    return value.quantize(PRECISION_BTC, rounding=ROUND_HALF_UP)


def quantize_shares(value: Decimal) -> Decimal:
    """Quantize to 3 decimal places (T212 wire requirement)."""
    return value.quantize(PRECISION_SHARES, rounding=ROUND_HALF_UP)


def quantize_czk(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places (CZK monetary standard)."""
    return value.quantize(PRECISION_CZK, rounding=ROUND_HALF_UP)


def quantize_fx(value: Decimal) -> Decimal:
    """Quantize to 4 decimal places (forex rate standard)."""
    return value.quantize(PRECISION_FX, rounding=ROUND_HALF_UP)
