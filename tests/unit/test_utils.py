# Standard library
from datetime import datetime, timezone

# Third-party
from freezegun import freeze_time

# Local
from core.utils import find_balance_exhaustion_date, is_now_cron_time


@freeze_time("2026-03-03 09:00:00")
def test_cron_matches_exactly() -> None:
    assert is_now_cron_time("0 9 * * *") is True


@freeze_time("2026-03-03 09:01:00")
def test_cron_one_minute_late() -> None:
    assert is_now_cron_time("0 9 * * *") is False


@freeze_time("2026-03-03 08:59:00")
def test_cron_one_minute_early() -> None:
    assert is_now_cron_time("0 9 * * *") is False


# ---------------------------------------------------------------------------
# Tests: find_balance_exhaustion_date
# ---------------------------------------------------------------------------

# Daily cron at 09:00 UTC; freeze at midnight so next run is 09:00 same day
_CRON_DAILY = "0 9 * * *"


@freeze_time("2026-03-03 00:00:00")
def test_exhaustion_on_first_run() -> None:
    """Balance just below one buffered spend: exhausted on the very first run."""
    spend = 1000.0
    balance = spend * 1.1 - 0.01  # just under one buffered spend
    result = find_balance_exhaustion_date(_CRON_DAILY, spend, balance)
    assert result is not None
    assert result == datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-03-03 00:00:00")
def test_exhaustion_on_third_run() -> None:
    """Balance covers exactly 2 buffered spends; exhausted on run 3."""
    spend = 1000.0
    buffer = 1.1
    balance = spend * buffer * 2 + 0.01  # survives 2 runs, fails on 3rd
    result = find_balance_exhaustion_date(_CRON_DAILY, spend, balance, buffer)
    assert result is not None
    # 3rd daily run from 2026-03-03 00:00 is 2026-03-05 09:00
    assert result == datetime(2026, 3, 5, 9, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-03-03 00:00:00")
def test_returns_none_when_balance_lasts_over_one_year() -> None:
    """Large balance that won't be exhausted within 365 days returns None."""
    spend = 1.0
    balance = 9_999_999.0  # effectively never runs out within a year
    result = find_balance_exhaustion_date(_CRON_DAILY, spend, balance)
    assert result is None


@freeze_time("2026-03-03 00:00:00")
def test_custom_buffer_affects_exhaustion_date() -> None:
    """Higher buffer means earlier exhaustion date."""
    spend = 1000.0
    balance = 1500.0
    # With buffer=1.0: first run depletes 1000, balance=500; second run depletes 1000 → exhausted on run 2
    result_no_buffer = find_balance_exhaustion_date(
        _CRON_DAILY, spend, balance, buffer=1.0
    )
    # With buffer=1.6: first run depletes 1600 → balance goes negative immediately
    result_high_buffer = find_balance_exhaustion_date(
        _CRON_DAILY, spend, balance, buffer=1.6
    )
    assert result_high_buffer is not None
    assert result_no_buffer is not None
    assert result_high_buffer < result_no_buffer


@freeze_time("2026-03-03 00:00:00")
def test_exhaustion_date_is_tz_aware() -> None:
    """Returned datetime should be timezone-aware (UTC)."""
    result = find_balance_exhaustion_date(_CRON_DAILY, 1000.0, 500.0)
    assert result is not None
    assert result.tzinfo is not None


@freeze_time("2026-03-03 00:00:00")
def test_zero_balance_exhausted_on_first_run() -> None:
    """Zero balance is exhausted immediately on the first run."""
    result = find_balance_exhaustion_date(_CRON_DAILY, 100.0, 0.0)
    assert result is not None
    assert result == datetime(2026, 3, 3, 9, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests: find_balance_exhaustion_date – once-per-day deduplication
# ---------------------------------------------------------------------------


@freeze_time("2026-03-06 00:00:00")  # Friday; next Monday is March 9
def test_minute_cron_deduplicates_to_once_per_day() -> None:
    """Minute-granularity cron (e.g. '* * * * 1') should only count once per day."""
    spend = 500.0
    balance = 5000.0
    # "* * * * 1" fires every minute on Mondays, but should count as 1 run per Monday
    result_minute = find_balance_exhaustion_date("* * * * 1", spend, balance)
    result_daily = find_balance_exhaustion_date("0 9 * * 1", spend, balance)
    assert result_minute is not None
    assert result_daily is not None
    # Both should exhaust on the same DATE (time may differ)
    assert result_minute.date() == result_daily.date()


@freeze_time("2026-03-03 00:00:00")
def test_weekly_cron_exhaustion_spans_multiple_weeks() -> None:
    """Weekly cron should advance week by week, not minute by minute."""
    spend = 1000.0
    balance = 3500.0  # covers 3 weeks at buffer=1.0, exhausted on week 4
    result = find_balance_exhaustion_date("0 9 * * 1", spend, balance, buffer=1.0)
    assert result is not None
    # 2026-03-03 is Tuesday; next Mondays: Mar 9, 16, 23, 30
    # Run 1 (Mar 9): 3500-1000=2500, Run 2 (Mar 16): 1500, Run 3 (Mar 23): 500, Run 4 (Mar 30): -500
    assert result == datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)


@freeze_time("2026-03-03 00:00:00")
def test_twice_daily_cron_counts_once_per_day() -> None:
    """Cron firing at 09:00 and 21:00 should still count once per day."""
    spend = 1000.0
    balance = 2500.0  # covers 2 days at buffer=1.0
    result_once = find_balance_exhaustion_date("0 9 * * *", spend, balance, buffer=1.0)
    result_twice = find_balance_exhaustion_date(
        "0 9,21 * * *", spend, balance, buffer=1.0
    )
    assert result_once is not None
    assert result_twice is not None
    assert result_once.date() == result_twice.date()
