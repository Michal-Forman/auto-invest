# Third-party
import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

# Local
from core.settings import settings

transport: httpx.HTTPTransport = httpx.HTTPTransport(retries=3)
_httpx_client: httpx.Client = httpx.Client(transport=transport)

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key,
    options=SyncClientOptions(httpx_client=_httpx_client),
)
