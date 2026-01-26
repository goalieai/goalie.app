from supabase import create_client, Client
from app.core.config import settings

def get_supabase() -> Client:
    """Initialize and return the Supabase client."""
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be provided in .env")
    
    return create_client(settings.supabase_url, settings.supabase_key)

# Global client instance
supabase = None
try:
    if settings.supabase_url and settings.supabase_key:
        supabase = get_supabase()
except Exception as e:
    print(f"Warning: Failed to initialize Supabase client: {e}")
