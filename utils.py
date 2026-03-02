# Standard library
from datetime import datetime, timezone

# Third-party
from croniter import croniter

# Local
from settings import settings


def is_now_cron_time(cron_expr: str) -> bool:
    """
    Returns True if current UTC minute matches the cron expression.
    Cron format example: "0 9 * * *"
    """

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    # Create iterator using one minute before now
    base = now.replace(minute=now.minute - 1)

    itr = croniter(cron_expr, base)
    next_run = itr.get_next(datetime)

    return next_run == now


if __name__ == "__main__":
    print(settings.portfolio.invest_interval)
    print(is_now_cron_time(settings.portfolio.invest_interval))
