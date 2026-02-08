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
        # # Debug: decode JWT payload to identify key role (anon vs service_role)
        # import json, base64
        # try:
        #     payload_b64 = settings.supabase_key.split(".")[1]
        #     payload_b64 += "=" * (4 - len(payload_b64) % 4)
        #     payload = json.loads(base64.b64decode(payload_b64))
        #     print(f"[SUPABASE DEBUG] JWT role: {payload.get('role', 'UNKNOWN')}")
        #     print(f"[SUPABASE DEBUG] JWT issuer: {payload.get('iss', 'UNKNOWN')}")
        # except Exception as e:
        #     print(f"[SUPABASE DEBUG] Could not decode key: {e}")
except Exception as e:
    print(f"Warning: Failed to initialize Supabase client: {e}")
