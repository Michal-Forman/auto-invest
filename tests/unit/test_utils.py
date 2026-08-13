# Third-party
from freezegun import freeze_time

# Local
from core.utils import is_now_cron_time, runs_in_next_days


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
# Tests: runs_in_next_days
# ---------------------------------------------------------------------------


@freeze_time("2026-03-03 00:00:00")
def test_daily_cron_counts_one_run_per_day() -> None:
    assert runs_in_next_days("0 9 * * *", 7) == 7


@freeze_time("2026-03-03 00:00:00")  # Tuesday
def test_weekly_cron_counts_one_run_per_week() -> None:
    # Next Mondays within 30 days: Mar 9, 16, 23, 30
    assert runs_in_next_days("0 9 * * 1", 30) == 4


@freeze_time("2026-03-06 00:00:00")  # Friday; next Monday is March 9
def test_minute_cron_deduplicates_to_once_per_day() -> None:
    """'* * * * 1' fires every minute on Mondays but counts once per Monday."""
    assert runs_in_next_days("* * * * 1", 7) == runs_in_next_days("0 9 * * 1", 7) == 1


@freeze_time("2026-03-03 00:00:00")
def test_twice_daily_cron_counts_once_per_day() -> None:
    assert runs_in_next_days("0 9,21 * * *", 5) == runs_in_next_days("0 9 * * *", 5)


@freeze_time("2026-03-03 00:00:00")  # Tuesday
def test_returns_zero_when_no_run_in_window() -> None:
    """Weekly Monday cron with a 3-day window has nothing to count."""
    assert runs_in_next_days("0 9 * * 1", 3) == 0


@freeze_time("2026-03-03 00:00:00")
def test_biweekly_cron_fires_twice_per_week() -> None:
    assert 8 <= runs_in_next_days("0 9 * * 1,4", 30) <= 10  # Mon + Thu


@freeze_time("2026-03-03 00:00:00")
def test_monthly_cron_fires_once_in_30_days() -> None:
    # 1st of each month: only 2026-04-01 falls within 30 days
    assert runs_in_next_days("0 9 1 * *", 30) == 1
