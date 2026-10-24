# Third-party
import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

# Local
from core.settings import settings

transport: httpx.HTTPTransport = httpx.HTTPTransport(retries=3)
_httpx_client: httpx.Client = httpx.Client(
    transport=transport,
    # Without this httpx defaults to 5 s, which Supabase occasionally exceeds
    timeout=httpx.Timeout(30.0, connect=10.0),
)

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key,
    options=SyncClientOptions(httpx_client=_httpx_client),
)
