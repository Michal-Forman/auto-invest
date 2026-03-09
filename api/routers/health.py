# Third-party
from fastapi import APIRouter

# Local
from api.dependencies import get_coinmate, get_t212
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Ping each exchange to verify connectivity."""
    t212_ok = False
    coinmate_ok = False

    print("[health] checking T212...", flush=True)
    try:
        result = get_t212().pies()
        err = result.get("err")
        status_code = (result.get("res") or {}).get("status") if isinstance(result.get("res"), dict) else None
        print(f"[health] T212 result: err={err!r}  res_type={type(result.get('res')).__name__}  status_code={status_code}", flush=True)
        t212_ok = not err
    except Exception as e:
        print(f"[health] T212 exception: {type(e).__name__}: {e}", flush=True)

    print("[health] checking Coinmate...", flush=True)
    try:
        coinmate_result = get_coinmate().ticker()
        print(f"[health] Coinmate result: {coinmate_result}", flush=True)
        coinmate_ok = True
    except Exception as e:
        print(f"[health] Coinmate exception: {type(e).__name__}: {e}", flush=True)

    print(f"[health] done → api=True  t212={t212_ok}  coinmate={coinmate_ok}", flush=True)
    return HealthResponse(api=True, t212=t212_ok, coinmate=coinmate_ok)
