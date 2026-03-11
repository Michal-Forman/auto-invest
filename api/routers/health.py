# Third-party
from fastapi import APIRouter, Depends
import requests

# Local
from api.cache import health_cache
from api.dependencies import get_current_user_id
from api.schemas import HealthResponse
from core.settings import settings
from core.trading212 import Trading212

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(user_id: str = Depends(get_current_user_id)) -> HealthResponse:
    """Ping each exchange to verify connectivity (cached 5 min per user)."""
    cache_key = f"health:{user_id}"
    if cache_key in health_cache:
        return health_cache[cache_key]  # type: ignore[return-value]

    print("[health] checking T212...", flush=True)
    t212_ok = Trading212.ping(env=settings.env)
    print(f"[health] T212 ok={t212_ok}", flush=True)

    print("[health] checking Coinmate...", flush=True)
    coinmate_ok = False
    try:
        requests.get(
            "https://coinmate.io/api/ticker",
            params={"currencyPair": "BTC_CZK"},
            timeout=10,
        )
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
