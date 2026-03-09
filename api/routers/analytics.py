# Standard library
from collections import Counter
from typing import Any, Dict, List

# Third-party
from fastapi import APIRouter

# Local
from api.schemas import AnalyticsAllocationItem, AnalyticsRunItem, AnalyticsStatusItem
from core.db.runs import Run

router = APIRouter(prefix="/analytics")


@router.get("/runs", response_model=List[AnalyticsRunItem])
def analytics_runs(limit: int = 10) -> List[AnalyticsRunItem]:
    """Return the last N runs with their CZK total and status for bar chart display."""
    runs: List[Run] = Run.get_recent_runs(limit=limit)
    return [
        AnalyticsRunItem(
            date=run.started_at.date().isoformat(),
            czk=run.planned_total_czk or 0.0,
            status=run.status,
        )
        for run in runs
    ]


@router.get("/allocation", response_model=List[AnalyticsAllocationItem])
def analytics_allocation(limit: int = 8) -> List[AnalyticsAllocationItem]:
    """Return per-ticker allocation percentages for the last N FILLED runs."""
    runs: List[Run] = Run.get_recent_runs(limit=limit)
    result: List[AnalyticsAllocationItem] = []

    for run in runs:
        if run.status != "FILLED" or not run.distribution:
            continue

        dist: Dict[str, Any] = run.distribution
        total = sum(dist.values())
        if total == 0:
            continue

        pct: Dict[str, float] = {
            ticker: round(czk / total * 100, 2) for ticker, czk in dist.items()
        }
        result.append(
            AnalyticsAllocationItem(
                date=run.started_at.date().isoformat(),
                data=pct,
            )
        )

    return result


@router.get("/status", response_model=List[AnalyticsStatusItem])
def analytics_status() -> List[AnalyticsStatusItem]:
    """Return run counts grouped by status."""
    runs: List[Run] = Run.get_all_runs(limit=1000)
    counts: Counter = Counter(run.status for run in runs)
    return [
        AnalyticsStatusItem(status=status, count=count)
        for status, count in counts.most_common()
    ]
