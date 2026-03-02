# Third-party
from supabase import Client, create_client

# Local
from settings import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
