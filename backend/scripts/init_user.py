import asyncio
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials verified from user logs
SUPABASE_URL = "http://127.0.0.1:54321"
SUPABASE_KEY = "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"

USER_ID = "11111111-1111-1111-1111-111111111111"
EMAIL = "test_unique_999@example.com"
PASSWORD = "password123"

def create_user():
    print(f"Connecting to {SUPABASE_URL}...")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    print(f"Creating user {USER_ID} ({EMAIL})...")
    
    try:
        # Check if user exists (by trying to sign in or just creating)
        # We will just try to create.
        
        # Using the admin api to create user with specific ID
        # Note: The Python client wrapper might differ slightly in different versions,
        # but auth.admin.create_user is standard.
        
        attributes = {
            "email": EMAIL,
            "password": PASSWORD,
            "email_confirm": True,
            "user_metadata": {"name": "Test User"}
        }
        
        # We cannot force the ID via the standard create_user of GoTrue easily in all versions without specific params.
        # However, we can try.
        
        # BUT, since we have the service role key, we can try to just run a raw SQL command via the 'rpc' interface if strictly needed
        # but creating a user via API is safer for auth schema.
        
        # Let's try the admin create first.
        user = supabase.auth.admin.create_user({
            "email": EMAIL,
            "password": PASSWORD,
            "email_confirm": True,
            "user_metadata": {"name": "Test User"}
            # "id": USER_ID # Some versions allow this
        })
        
        print(f"User created with ID: {user.user.id}")
        
        if user.user.id != USER_ID:
            print(f"WARNING: User created but ID is {user.user.id}, NOT {USER_ID}.")
            print("To fix this, we might need to update the ID in the database directly or use SQL.")
            
            # Try to update the ID via SQL if possible? No, can't easily.
            # But let's see.
        else:
             print("SUCCESS: User created with correct ID.")

    except Exception as e:
        print(f"Error creating user: {e}")
        # If it fails, it might be because of duplicate, which is fine.

if __name__ == "__main__":
    create_user()
