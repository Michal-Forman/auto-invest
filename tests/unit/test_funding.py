# Standard library
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List
from unittest.mock import MagicMock

# Local
from core.funding import (
    EXECUTION_MARGIN,
    ExchangeFunding,
    InsufficientFundsError,
    funding_status,
    should_send_alert,
    should_send_recovery,
    split_by_exchange,
)

_NOW = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)

# T212 side sums to 750, BTC to 250
_DISTRIBUTION: Dict[str, Decimal] = {
    "VWCEd_EQ": Decimal("500"),
    "KKR_US_EQ": Decimal("250"),
    "BTC": Decimal("250"),
}


def _clients(t212_balance: str, coinmate_balance: str) -> tuple:
    """Build Trading212/Coinmate mocks that report the given free cash."""
    t212 = MagicMock()
    t212.balance.return_value = Decimal(t212_balance)
    coinmate = MagicMock()
    coinmate.balance.return_value = Decimal(coinmate_balance)
    return t212, coinmate


def _by_exchange(statuses: List[ExchangeFunding]) -> Dict[str, ExchangeFunding]:
    return {s.exchange: s for s in statuses}


# ---------------------------------------------------------------------------
# Tests: split_by_exchange
# ---------------------------------------------------------------------------


def test_btc_routes_to_coinmate_and_everything_else_to_t212() -> None:
    totals = split_by_exchange(_DISTRIBUTION)
    assert totals["T212"] == Decimal("750")
    assert totals["COINMATE"] == Decimal("250")


def test_portfolio_without_btc_leaves_coinmate_at_zero() -> None:
    totals = split_by_exchange({"VWCEd_EQ": Decimal("1000")})
    assert totals["COINMATE"] == Decimal("0")


# ---------------------------------------------------------------------------
# Tests: funding_status
# ---------------------------------------------------------------------------


def test_ample_cash_is_not_short() -> None:
    t212, coinmate = _clients("5000", "5000")
    statuses = funding_status(_DISTRIBUTION, t212, coinmate)

    assert len(statuses) == 2
    assert all(not s.is_short for s in statuses)
    assert all(s.shortfall_czk == Decimal("0") for s in statuses)


def test_exactly_enough_including_margin_is_not_short() -> None:
    """750 * 1.015 = 761.25 — covered to the haler, so the run may proceed."""
    t212, coinmate = _clients("761.25", "253.75")
    statuses = _by_exchange(funding_status(_DISTRIBUTION, t212, coinmate))

    assert statuses["T212"].needed_czk == Decimal("761.25")
    assert not statuses["T212"].is_short
    assert not statuses["COINMATE"].is_short


def test_covers_plan_but_not_margin_is_short() -> None:
    """This is the real-world failure: enough for the plan, not for the fill."""
    t212, coinmate = _clients("750", "250")
    statuses = _by_exchange(funding_status(_DISTRIBUTION, t212, coinmate))

    assert statuses["T212"].is_short
    assert statuses["T212"].shortfall_czk == Decimal("11.25")


def test_one_exchange_short_leaves_the_other_healthy() -> None:
    t212, coinmate = _clients("5000", "200")
    statuses = _by_exchange(funding_status(_DISTRIBUTION, t212, coinmate))

    assert not statuses["T212"].is_short
    assert statuses["COINMATE"].is_short
    assert statuses["COINMATE"].shortfall_czk == Decimal("53.75")


def test_both_exchanges_short() -> None:
    t212, coinmate = _clients("700", "200")
    short = [s for s in funding_status(_DISTRIBUTION, t212, coinmate) if s.is_short]

    assert {s.exchange for s in short} == {"T212", "COINMATE"}


def test_exchange_with_nothing_to_buy_is_skipped() -> None:
    t212, coinmate = _clients("5000", "0")
    statuses = funding_status({"VWCEd_EQ": Decimal("1000")}, t212, coinmate)

    assert [s.exchange for s in statuses] == ["T212"]
    coinmate.balance.assert_not_called()


def test_runs_and_margin_scale_the_requirement() -> None:
    """The alert path asks for several runs at the user's wider buffer."""
    t212, coinmate = _clients("2000", "2000")
    statuses = _by_exchange(
        funding_status(_DISTRIBUTION, t212, coinmate, runs=2, margin=Decimal("1.2"))
    )

    # 750 * 1.2 = 900 per run, 1800 for two runs
    assert statuses["T212"].per_run_czk == Decimal("900.00")
    assert statuses["T212"].needed_czk == Decimal("1800.00")
    assert not statuses["T212"].is_short


def test_runs_below_one_is_clamped() -> None:
    """A zero-run alert window must still check a single run, never nothing."""
    t212, coinmate = _clients("5000", "5000")
    statuses = _by_exchange(funding_status(_DISTRIBUTION, t212, coinmate, runs=0))

    assert statuses["T212"].runs == 1


def test_amounts_stay_decimal_and_quantized() -> None:
    t212, coinmate = _clients("100", "100")
    status = _by_exchange(funding_status(_DISTRIBUTION, t212, coinmate))["T212"]

    for value in (status.required_czk, status.needed_czk, status.shortfall_czk):
        assert isinstance(value, Decimal)
        assert value == value.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Tests: InsufficientFundsError
# ---------------------------------------------------------------------------


def test_error_message_names_every_short_exchange() -> None:
    t212, coinmate = _clients("700", "200")
    short = [s for s in funding_status(_DISTRIBUTION, t212, coinmate) if s.is_short]
    message = str(InsufficientFundsError(short))

    assert "T212" in message
    assert "COINMATE" in message
    assert "53.75" in message


def test_error_keeps_shortfalls_for_the_email() -> None:
    t212, coinmate = _clients("5000", "200")
    short = [s for s in funding_status(_DISTRIBUTION, t212, coinmate) if s.is_short]
    error = InsufficientFundsError(short)

    assert [s.exchange for s in error.shortfalls] == ["COINMATE"]


# ---------------------------------------------------------------------------
# Tests: alert cadence
# ---------------------------------------------------------------------------


def test_no_alert_when_nothing_is_short() -> None:
    assert should_send_alert(set(), None, set(), _NOW) is False


def test_alerts_when_never_alerted_before() -> None:
    assert should_send_alert({"T212"}, None, set(), _NOW) is True


def test_suppresses_repeat_within_cooldown() -> None:
    yesterday = _NOW - timedelta(days=1)
    assert should_send_alert({"T212"}, yesterday, {"T212"}, _NOW) is False


def test_repeats_after_cooldown() -> None:
    four_days_ago = _NOW - timedelta(days=4)
    assert should_send_alert({"T212"}, four_days_ago, {"T212"}, _NOW) is True


def test_newly_short_exchange_bypasses_cooldown() -> None:
    """Coinmate going short must not wait for T212's cooldown to expire."""
    yesterday = _NOW - timedelta(days=1)
    assert should_send_alert({"T212", "COINMATE"}, yesterday, {"T212"}, _NOW) is True


def test_recovery_only_after_a_previous_alert() -> None:
    assert should_send_recovery(set(), {"COINMATE"}) is True
    assert should_send_recovery(set(), set()) is False
    assert should_send_recovery({"T212"}, {"T212"}) is False


def test_default_margin_is_the_execution_margin() -> None:
    funding = ExchangeFunding(
        exchange="T212",
        required_czk=Decimal("1000"),
        available_czk=Decimal("0"),
    )
    assert funding.margin == EXECUTION_MARGIN
    assert funding.needed_czk == Decimal("1015.00")
