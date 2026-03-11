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
    """Ping each exchange to verify connectivity (cached 5 min per user)."""
    cache_key = f"health:{user_id}"
    if cache_key in health_cache:
        return health_cache[cache_key]  # type: ignore[return-value]

    t212_ok = False
    coinmate_ok = False

    print("[health] checking T212...", flush=True)
    try:
        result = get_t212_for_user(user_id).pies()
        err = result.get("err")
        status_code = (
            (result.get("res") or {}).get("status")
            if isinstance(result.get("res"), dict)
            else None
        )
        print(
            f"[health] T212 result: err={err!r}  res_type={type(result.get('res')).__name__}  status_code={status_code}",
            flush=True,
        )
        t212_ok = not err
    except Exception as e:
        print(f"[health] T212 exception: {type(e).__name__}: {e}", flush=True)

    print("[health] checking Coinmate...", flush=True)
    try:
        coinmate_result = get_coinmate_for_user(user_id).ticker()
        print(f"[health] Coinmate result: {coinmate_result}", flush=True)
        coinmate_ok = True
    except Exception as e:
        print(f"[health] Coinmate exception: {type(e).__name__}: {e}", flush=True)

    print(
        f"[health] done → api=True  t212={t212_ok}  coinmate={coinmate_ok}", flush=True
    )
    response = HealthResponse(api=True, t212=t212_ok, coinmate=coinmate_ok)
    if t212_ok and coinmate_ok:
        health_cache[cache_key] = response
    return response
