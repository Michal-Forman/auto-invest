# Future
from __future__ import annotations

# Standard library
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional, cast
from uuid import UUID, uuid4

# Third-party
from pydantic import BaseModel

# Local
from core.db.base import BaseDBModel
from core.db.client import supabase
from core.db.orders import Order
from core.log import log
from core.settings import PortfolioSettings, settings

RUN_EXPIRY_DAYS = 14

Status = Literal["CREATED", "FINISHED", "FILLED", "FAILED", "UNKNOWN"]


class RunUpdate(BaseModel):
    planned_total_czk: Optional[float] = None
    filled_total_czk: Optional[float] = None
    finished_at: Optional[datetime] = None
    status: Optional[Status] = None
    total_orders: Optional[int] = None
    successful_orders: Optional[int] = None
    failed_orders: Optional[int] = None
    distribution: Optional[Dict[str, Any]] = None
    multipliers: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Run(BaseDBModel):
    # --- Identity ---
    TABLE: ClassVar[str] = "runs"
    id: Optional[UUID] = None
    user_id: Optional[str] = None

    # --- Timing ---
    started_at: datetime
    finished_at: Optional[datetime] = None

    # --- Status ---
    status: Status

    # --- Investment snapshot ---
    invest_amount: float
    invest_interval: str
    t212_default_weight: float
    btc_default_weight: float

    # --- Execution summary ---
    planned_total_czk: Optional[float] = None
    filled_total_czk: Optional[float] = None

    total_orders: Optional[int] = None
    successful_orders: Optional[int] = None
    failed_orders: Optional[int] = None

    # --- Debug / analytics ---
    distribution: Optional[Dict[str, Any]] = None
    multipliers: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    test: bool

    # -------------------------
    # Helper methods for DB
    # -------------------------

    def update_in_db(self, update_data: RunUpdate) -> Optional[Dict[str, Any]]:
        """Apply a RunUpdate to this run's row in Supabase. Returns the updated row dict or None."""
        if not self.id:
            raise ValueError("Cannot update run without id")

        update_fields: Dict[str, Any] = update_data.model_dump(
            mode="json", exclude_none=True
        )

        response: Any = (
            supabase.table(self.TABLE)
            .update(update_fields)
            .eq("id", str(self.id))
            .execute()
        )

        if response.data:
            log.info("Successfully updated the run in db")
            row = cast(Dict[str, Any], response.data[0])
            for field, value in update_data.model_dump(exclude_none=True).items():
                setattr(self, field, value)
            return row

        return None

    @staticmethod
    def create_run(
        run_start: datetime,
        portfolio: "PortfolioSettings",
        user_id: Optional[str] = None,
    ) -> Run:
        """Create a new CREATED run with the given portfolio settings, insert it into DB, and return the persisted Run."""
        run = Run(
            started_at=run_start,
            status="CREATED",
            invest_amount=portfolio.invest_amount,
            invest_interval=portfolio.invest_interval,
            t212_default_weight=portfolio.t212_weight,
            btc_default_weight=portfolio.btc_weight,
            total_orders=0,
            successful_orders=0,
            failed_orders=0,
            test=False,
            user_id=user_id,
        )

        try:
            inserted: Optional[Dict[str, Any]] = run.post_to_db()
        except Exception as e:
            log.error(f"Failed to insert run into database: {e}")
            raise RuntimeError("Run creation failed during DB insert") from e

        if not inserted:
            raise RuntimeError("Run creation failed: no row returned from DB")

        log.info("Run successfully placed and recorded in database")

        return run

    def _are_all_orders_filled(self) -> bool:
        """Check whether every order in this run has status FILLED."""
        if not self.id:
            raise ValueError("Cannot update run without id")
        res: Any = (
            supabase.table("orders")
            .select("id", count="exact")  # type: ignore[arg-type]
            .eq("run_id", self.id)
            .neq("status", "FILLED")
            .execute()
        )
        return (res.count or 0) == 0

    def _sum_orders_filled_czk(self) -> float:
        """Sum filled_total_czk across all orders belonging to this run."""
        if not self.id:
            raise ValueError("Cannot sum orders without run id")
        res: Any = (
            supabase.table("orders")
            .select("filled_total_czk")
            .eq("run_id", self.id)
            .execute()
        )
        return sum(row["filled_total_czk"] or 0.0 for row in (res.data or []))

    def _mark_run_filled(self, filled_total_czk: float) -> None:
        """Set this run's status to FILLED and persist filled_total_czk."""
        if not self.id:
            raise ValueError("Cannot update run without id")
        (
            supabase.table("runs")
            .update({"status": "FILLED", "filled_total_czk": filled_total_czk})
            .eq("id", self.id)
            .execute()
        )
        self.status = "FILLED"
        self.filled_total_czk = filled_total_czk

    def _try_mark_run_filled(self) -> bool:
        """Mark the run as FILLED if all its orders are filled. Returns True if status was updated."""
        if self._are_all_orders_filled():
            self._mark_run_filled(self._sum_orders_filled_czk())
            return True
        return False

    def _try_mark_run_failed_if_expired(self) -> None:
        """Mark a FINISHED run as FAILED if it has been waiting for order fills for more than 14 days."""
        if self.status != "FINISHED":
            return

        if not self.finished_at:
            return

        now: datetime = datetime.now(timezone.utc)
        expiry_threshold: datetime = now - timedelta(days=RUN_EXPIRY_DAYS)

        if self.finished_at < expiry_threshold:
            update = RunUpdate(status="FAILED")
            self.update_in_db(update)

    @staticmethod
    def _get_finished_runs(user_id: Optional[str] = None) -> List[Run]:
        """Fetch all runs with status FINISHED from the database, ordered by most recent first."""
        query: Any = (
            supabase.table("runs")
            .select("*")
            .eq("status", "FINISHED")
            .order("started_at", desc=True)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response: Any = query.execute()

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @classmethod
    def update_runs(cls, user_id: Optional[str] = None) -> None:
        """Process all FINISHED runs: mark expired ones as FAILED, mark fully-filled ones as FILLED."""
        finished_runs: List[Run] = cls._get_finished_runs(user_id=user_id)
        for run in finished_runs:
            try:
                run._try_mark_run_failed_if_expired()
                run._try_mark_run_filled()
            except Exception as e:
                log.error(f"Failed to update run {run.id}: {e}")

    @staticmethod
    def process_new_run_data(orders: List[Order]) -> RunUpdate:
        """Build a RunUpdate from the placed orders with totals, distribution, multipliers, and error summary."""
        total_orders = len(orders)
        successful_orders = sum(
            1 for o in orders if o.status not in ("FAILED", "UNKNOWN")
        )
        failed_orders = sum(1 for o in orders if o.status in ("FAILED", "UNKNOWN"))

        planned_total_czk: float = float(sum(o.total_czk for o in orders))

        distribution: Dict[str, float] = {o.t212_ticker: o.total_czk for o in orders}
        multipliers: Dict[str, float] = {o.t212_ticker: o.multiplier for o in orders}

        errors: List[str] = [o.error for o in orders if o.error]
        error: Optional[str] = "; ".join(errors) if errors else None

        return RunUpdate(
            planned_total_czk=planned_total_czk,
            finished_at=datetime.now(timezone.utc),
            status="FINISHED",
            total_orders=total_orders,
            successful_orders=successful_orders,
            failed_orders=failed_orders,
            distribution=distribution,
            multipliers=multipliers,
            error=error,
        )

    @staticmethod
    def get_all_runs(
        limit: int = 50,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Run]:
        """Fetch runs with optional status/user filter, ordered by most recent first."""
        query: Any = (
            supabase.table(Run.TABLE)
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)

        response: Any = query.execute()

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @staticmethod
    def get_recent_runs(limit: int = 50, user_id: Optional[str] = None) -> List[Run]:
        """Fetch the N most recent FINISHED or FILLED runs, ordered by most recent first."""
        query: Any = (
            supabase.table(Run.TABLE)
            .select("*")
            .in_("status", ["FINISHED", "FILLED"])
            .order("started_at", desc=True)
            .limit(limit)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response: Any = query.execute()

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @staticmethod
    def get_runs_for_period(
        year: int, month: int, user_id: Optional[str] = None
    ) -> List[Run]:
        """Fetch all FINISHED or FILLED runs for the given year/month (UTC)."""
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        query: Any = (
            supabase.table(Run.TABLE)
            .select("*")
            .in_("status", ["FINISHED", "FILLED"])
            .gte("started_at", start.isoformat())
            .lt("started_at", end.isoformat())
            .order("started_at", desc=True)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response: Any = query.execute()

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @staticmethod
    def get_failed_runs_for_period(
        year: int, month: int, user_id: Optional[str] = None
    ) -> List[Run]:
        """Fetch all FAILED runs that started in the given year/month (UTC)."""
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        query: Any = (
            supabase.table(Run.TABLE)
            .select("*")
            .eq("status", "FAILED")
            .gte("started_at", start.isoformat())
            .lt("started_at", end.isoformat())
            .order("started_at", desc=True)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response: Any = query.execute()

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @staticmethod
    def run_exists_today(user_id: Optional[str] = None) -> bool:
        """Check if a run was already created today (UTC). Always returns False in non-prod."""
        now: datetime = datetime.now(timezone.utc)

        start_of_day: datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day: datetime = start_of_day + timedelta(days=1)

        query: Any = (
            supabase.table(Run.TABLE)
            .select("id")
            .gte("started_at", start_of_day.isoformat())
            .lt("started_at", end_of_day.isoformat())
            .limit(1)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        response: Any = query.execute()

        if settings.env != "prod":
            return False

        return bool(response.data)
