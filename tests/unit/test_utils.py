# Third-party
from freezegun import freeze_time

# Local
from utils import is_now_cron_time


@freeze_time("2026-03-03 09:00:00")
def test_cron_matches_exactly() -> None:
    assert is_now_cron_time("0 9 * * *") is True


@freeze_time("2026-03-03 09:01:00")
def test_cron_one_minute_late() -> None:
    assert is_now_cron_time("0 9 * * *") is False


@freeze_time("2026-03-03 08:59:00")
def test_cron_one_minute_early() -> None:
    assert is_now_cron_time("0 9 * * *") is False
