# Standard library
from datetime import datetime, timedelta, timezone

# Third-party
from croniter import croniter  # type: ignore[import-untyped]


def runs_in_next_days(cron_expr: str, days: int) -> int:
    """Count how many times a cron schedule fires in the next `days` days (max once per day)."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    itr: croniter = croniter(cron_expr, now)
    seen_dates: set = set()
    while True:
        nxt: datetime = itr.get_next(datetime)
        if nxt > end:
            return len(seen_dates)
        seen_dates.add(nxt.date())


def is_now_cron_time(cron_expr: str) -> bool:
    """
    Returns True if current UTC minute matches the cron expression.
    Cron format example: "0 9 * * *"
    """

    now: datetime = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    # Create iterator using one minute before now
    base: datetime = now - timedelta(minutes=1)

    itr: croniter = croniter(cron_expr, base)
    next_run: datetime = itr.get_next(datetime)

    return next_run == now


if __name__ == "__main__":
    print(runs_in_next_days("* * * * 1", 30))
