from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Literal, List
from uuid import UUID
from pydantic import BaseModel

from db.client import supabase


from uuid import uuid4
from db.orders import Order
from log import log
from settings import settings

TABLE = "runs"

Status = Literal[
        "CREATED",
        "FINISHED",
        "FILLED",
        "FAILED",
        "UNKNOWN"
        ]

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

class Run(BaseModel):
    # --- Identity ---
    id: Optional[UUID] = None

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

    def _to_insert_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def _post_to_db(self) -> Optional[Dict[str, Any]]:
        run_data = self._to_insert_dict()

        response = (
            supabase
            .table(TABLE)
            .insert(run_data)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    def update_in_db(self, update_data: RunUpdate) -> Optional[Dict[str, Any]]:
        if not self.id:
            raise ValueError("Cannot update run without id")

        update_fields = update_data.model_dump(mode="json", exclude_none=True)

        response = (
            supabase
            .table(TABLE)
            .update(update_fields)
            .eq("id", str(self.id))
            .execute()
        )

        if response.data:
            log.info("Successfully updated the run in db")
            return response.data[0]

        return None

    @staticmethod
    def create_run(run_start: datetime) -> Run:
        run = Run(
                started_at=run_start,
                status="CREATED",
                invest_amount=settings.portfolio.invest_amount,
                invest_interval=settings.portfolio.invest_interval,
                t212_default_weight=settings.portfolio.t212_weight,
                btc_default_weight=settings.portfolio.btc_weight,
                total_orders=0,
                successful_orders=0,
                failed_orders=0,
                test=True
        )       

        try:
            inserted = run._post_to_db()
        except Exception as e:
            log.error(f"Failed to insert run into database: {e}")
            raise RuntimeError("Run creation failed during DB insert") from e

        if not inserted:
            raise RuntimeError("Run creation failed: no row returned from DB")

        log.info("Run successfully placed and recorded in database")

        return Run.model_validate(inserted)

    def _are_all_orders_filled(self) -> bool:
        if not self.id:
            raise ValueError("Cannot update run without id")
        res = (
            supabase
            .table("orders")
            .select("id", count="exact")
            .eq("run_id", self.id)
            .neq("status", "FILLED")
            .execute()
        )
        print(f"res_count: {res.count}")
        return (res.count or 0) == 0

    def _mark_run_filled(self) -> None:
        if not self.id:
            raise ValueError("Cannot update run without id")
        (
            supabase
            .table("runs")
            .update({"status": "FILLED"})
            .eq("id", self.id)
            .execute()
        )

    def _try_mark_run_filled(self) -> bool:
        if self._are_all_orders_filled():
            self._mark_run_filled()
            return True
        return False

    def _try_mark_run_failed_if_expired(self) -> None:
        if self.status != "FINISHED":
            return

        if not self.finished_at:
            return

        now = datetime.now(timezone.utc)
        expiry_threshold = now - timedelta(days=14)

        if self.finished_at < expiry_threshold:
            update = RunUpdate(status="FAILED")
            self.update_in_db(update)

    @staticmethod
    def _get_finished_runs() -> List[Run]:
        response = (
            supabase
            .table("runs")
            .select("*")
            .eq("status", "FINISHED")
            .order("started_at", desc=True)
            .execute()
        )

        if not response.data:
            return []

        return [Run.model_validate(row) for row in response.data]

    @classmethod
    def update_runs(cls):
        finished_runs: List[Run] = cls._get_finished_runs()
        for run in finished_runs:
            print("updating_run")
            try:
                run._try_mark_run_failed_if_expired()
                run._try_mark_run_filled()
            except Exception as e:
                print(f"the errro in my except statement!!!, in update runs, look: {e}")


    @staticmethod
    def process_new_run_data(orders: List[Order]) -> RunUpdate:
        total_orders = len(orders)
        successful_orders = sum(1 for o in orders if o.status not in ("FAILED", "UNKNOWN"))
        failed_orders = sum(1 for o in orders if o.status in ("FAILED", "UNKNOWN"))

        planned_total_czk = float(sum(o.total_czk for o in orders))

        distribution = {o.t212_ticker: o.total_czk for o in orders}
        multipliers = {o.t212_ticker: o.multiplier for o in orders}

        errors = [o.error for o in orders if o.error]
        error = "; ".join(errors) if errors else None

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
        

if __name__ == "__main__":
    Run.update_runs()


