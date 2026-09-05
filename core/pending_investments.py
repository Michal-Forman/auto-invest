# Standard library
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List

# Local
from core.coinmate import Coinmate
from core.db.orders import Order
from core.db.runs import Run, RunUpdate
from core.db.users import UserRecord
from core.executor import Executor
from core.funding import OneTimeFundingCheck, one_time_funding_status
from core.instruments import Instruments
from core.log import log
from core.mailer import Mailer
from core.precision import to_decimal
from core.settings import UserSettings
from core.trading212 import Trading212

# A one-time invest waiting on funds is retried for this long before it's given up on.
PENDING_EXPIRY_DAYS = 3


def retry_pending_investments() -> None:
    """Sweep every user's pending one-time investments: place what's now funded,
    expire what's been waiting too long. Called on a timer by the API process."""
    pending_runs: List[Run] = Run.get_pending_runs()
    for run in pending_runs:
        try:
            _retry_one(run)
        except Exception as e:
            log.error(f"Pending investment retry failed for run {run.id}: {e}")


def _retry_one(run: Run) -> None:
    """Check, and if funded, place a single pending one-time investment."""
    assert run.id is not None
    assert run.user_id is not None

    if datetime.now(timezone.utc) - run.started_at > timedelta(
        days=PENDING_EXPIRY_DAYS
    ):
        _expire(run)
        return

    user: UserRecord = UserRecord.from_db(run.user_id)
    user_settings: UserSettings = UserSettings.from_user(user)
    t212 = Trading212(
        api_id_key=user_settings.t212_id_key,
        api_private_key=user_settings.t212_private_key,
        env=user_settings.env,
    )
    coinmate = Coinmate(
        user_settings.coinmate_client_id or 0,
        user_settings.coinmate_public_key,
        user_settings.coinmate_private_key,
    )
    mailer = Mailer(user_settings) if user.notifications_enabled else None

    cash_distribution: Dict[str, Decimal] = {
        ticker: to_decimal(czk) for ticker, czk in (run.distribution or {}).items()
    }
    multipliers: Dict[str, Decimal] = {
        ticker: to_decimal(mult) for ticker, mult in (run.multipliers or {}).items()
    }

    # Idempotency guard: a prior attempt may have placed orders on the exchanges and
    # then crashed before moving the run off PENDING. The order idempotency key depends
    # on the live share quantity, so re-placing would NOT be deduped — it would spend
    # real money twice. Finalize from what's already recorded instead.
    existing: List[Order] = Order.get_orders_for_runs(
        [str(run.id)], user_id=run.user_id
    )
    if existing:
        log.warning(
            f"Run {run.id} already has {len(existing)} orders; "
            "finalizing without re-placing"
        )
        run.update_in_db(Run.process_new_run_data(existing))
        if mailer:
            mailer.send_investment_confirmation(
                run, existing, cash_distribution, multipliers
            )
        return

    dca_reserve: Dict[str, Decimal] = Instruments(
        t212, coinmate, user_settings.portfolio
    ).distribute_cash()["cash_distribution"]

    statuses: List[OneTimeFundingCheck] = one_time_funding_status(
        cash_distribution, dca_reserve, t212, coinmate
    )
    if any(status.is_short for status in statuses):
        return  # still waiting — no per-hour notification, only success/expiry email

    executor = Executor(t212, coinmate, user_id=run.user_id)
    try:
        orders: List[Order] = executor.place_orders(
            cash_distribution, multipliers, run_id=run.id, investment_type="one_time"
        )
    except Exception as e:
        log.error(f"Failed to place pending investment for run {run.id}: {e}")
        placed: List[Order] = Order.get_orders_for_runs(
            [str(run.id)], user_id=run.user_id
        )
        if placed:
            # Some orders reached the exchanges before the failure. Record them as a
            # FINISHED run so reconciliation counts the money — burying them under
            # FAILED hides real fills from every report.
            run.update_in_db(Run.process_new_run_data(placed))
            banner = (
                "Your one-time investment was only partially placed. Some orders may "
                "not have been recorded — check your exchange accounts."
            )
        else:
            run.update_in_db(
                RunUpdate(
                    status="FAILED",
                    error=str(e),
                    finished_at=datetime.now(timezone.utc),
                )
            )
            banner = (
                "Your one-time investment could not be placed. It will not be "
                "retried — place it again from the app when you're ready."
            )
        if mailer:
            mailer.send_error_alert(e, run, banner_message=banner)
        return

    run.update_in_db(Run.process_new_run_data(orders))
    if mailer:
        mailer.send_investment_confirmation(run, orders, cash_distribution, multipliers)


def _expire(run: Run) -> None:
    """Give up on a pending investment that hasn't been funded in time."""
    assert run.user_id is not None

    run.update_in_db(
        RunUpdate(
            status="FAILED",
            error=f"Expired: not funded within {PENDING_EXPIRY_DAYS} days",
            finished_at=datetime.now(timezone.utc),
        )
    )

    user: UserRecord = UserRecord.from_db(run.user_id)
    if not user.notifications_enabled:
        return

    user_settings: UserSettings = UserSettings.from_user(user)
    t212 = Trading212(
        api_id_key=user_settings.t212_id_key,
        api_private_key=user_settings.t212_private_key,
        env=user_settings.env,
    )
    coinmate = Coinmate(
        user_settings.coinmate_client_id or 0,
        user_settings.coinmate_public_key,
        user_settings.coinmate_private_key,
    )
    cash_distribution: Dict[str, Decimal] = {
        ticker: to_decimal(czk) for ticker, czk in (run.distribution or {}).items()
    }
    dca_reserve: Dict[str, Decimal] = Instruments(
        t212, coinmate, user_settings.portfolio
    ).distribute_cash()["cash_distribution"]
    statuses: List[OneTimeFundingCheck] = one_time_funding_status(
        cash_distribution, dca_reserve, t212, coinmate
    )

    Mailer(user_settings).send_pending_investment_expired(run, statuses)


if __name__ == "__main__":
    retry_pending_investments()
