# Third-party
from fastapi import APIRouter, Depends

# Local
from api.cache import health_cache
from api.dependencies import (
    get_coinmate_for_user,
    get_current_user_id,
    get_t212_for_user,
)
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(user_id: str = Depends(get_current_user_id)) -> HealthResponse:
    """Check exchange connectivity using per-user credentials (cached 5 min per user)."""
    cache_key = f"health:{user_id}"
    if cache_key in health_cache:
        return health_cache[cache_key]  # type: ignore[return-value]

    t212_ok = False
    try:
        get_t212_for_user(user_id).balance()
        t212_ok = True
    except Exception as e:
        print(f"[health] T212 error: {type(e).__name__}: {e}", flush=True)

    coinmate_ok = False
    try:
        get_coinmate_for_user(user_id).balance()
        coinmate_ok = True
    except Exception as e:
        print(f"[health] Coinmate error: {type(e).__name__}: {e}", flush=True)

    response = HealthResponse(api=True, t212=t212_ok, coinmate=coinmate_ok)
    if t212_ok and coinmate_ok:
        health_cache[cache_key] = response
    return response
