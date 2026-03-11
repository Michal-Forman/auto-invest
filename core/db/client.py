# Third-party
from supabase import Client, create_client

# Local
from core.settings import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
