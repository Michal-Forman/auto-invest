# Standard library
from typing import Any, Dict

# Third-party
from fastapi import APIRouter

# Local
from api.dependencies import get_coinmate, get_t212
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Ping each exchange to verify connectivity."""
    t212_status = "ok"
    coinmate_status = "ok"

    try:
        result: Dict[str, Any] = get_t212().pies()
        if result.get("err"):
            t212_status = "error"
    except Exception:
        t212_status = "error"

    try:
        get_coinmate().ticker()
    except Exception:
        coinmate_status = "error"

    return HealthResponse(api="ok", t212=t212_status, coinmate=coinmate_status)
