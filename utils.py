# Standard library
from datetime import datetime, timedelta, timezone
from typing import Optional

# Third-party
from croniter import croniter  # type: ignore[import-untyped]

# Local
from settings import settings


def find_balance_exhaustion_date(
    cron_expr: str, spend_per_run: float, current_balance: float, buffer: float = 1.1
) -> Optional[datetime]:
    """Return the datetime of the first future cron run where balance (with buffer) runs out.

    Returns None if balance won't be exhausted within 1 year.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=365)
    itr: croniter = croniter(cron_expr, now)
    balance = current_balance
    while True:
        nxt: datetime = itr.get_next(datetime)
        if nxt > end:
            return None
        balance -= spend_per_run * buffer
        if balance < 0:
            return nxt


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
    print(settings.portfolio.invest_interval)
    print(is_now_cron_time(settings.portfolio.invest_interval))
