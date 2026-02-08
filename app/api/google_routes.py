from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.supabase import supabase

google_router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _build_flow() -> Flow:
    """Build a Google OAuth flow from config settings."""
    client_config = {
        "web": {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    return flow


def _get_google_email(creds) -> str:
    """Fetch the Google email address associated with the OAuth credentials."""
    try:
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info.get("email", "")
    except Exception as e:
        print(f"[GOOGLE] Failed to fetch user email: {e}")
        return ""


@google_router.get("/auth-url")
async def get_auth_url(user_id: str = Query(...)):
    """Generate Google OAuth consent URL. Frontend redirects the user here."""
    flow = _build_flow()
    # Also request email scope so we can identify the Google account
    flow.oauth2session.scope = SCOPES + ["openid", "https://www.googleapis.com/auth/userinfo.email"]
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=user_id,
    )
    return {"auth_url": auth_url}


@google_router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Google OAuth callback. Exchanges code for tokens, stores in Supabase,
    then redirects to the frontend.
    """
    user_id = state
    # print(f"[GOOGLE DEBUG] === OAuth callback started ===")
    # print(f"[GOOGLE DEBUG] user_id from state: {user_id}")

    try:
        flow = _build_flow()
        # Must match the scopes used in auth-url
        flow.oauth2session.scope = SCOPES + ["openid", "https://www.googleapis.com/auth/userinfo.email"]
        flow.fetch_token(code=code)
        creds = flow.credentials
        # print(f"[GOOGLE DEBUG] Token exchange succeeded")
        # print(f"[GOOGLE DEBUG] access_token present: {bool(creds.token)}")
        # print(f"[GOOGLE DEBUG] refresh_token present: {bool(creds.refresh_token)}")
        # print(f"[GOOGLE DEBUG] scopes: {creds.scopes}")
    except Exception as e:
        print(f"[GOOGLE] Token exchange failed: {e}")
        redirect_url = f"{settings.frontend_origin}/google-connected?success=false&error=token_exchange"
        return RedirectResponse(url=redirect_url)

    # Fetch the Google email for this account
    google_email = _get_google_email(creds)
    # print(f"[GOOGLE DEBUG] Fetched google_email: {google_email}")

    if not google_email:
        redirect_url = f"{settings.frontend_origin}/google-connected?success=false&error=no_email"
        return RedirectResponse(url=redirect_url)

    token_data = {
        "user_id": user_id,
        "google_email": google_email,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    # print(f"[GOOGLE DEBUG] token_data keys: {list(token_data.keys())}")
    # print(f"[GOOGLE DEBUG] token_data user_id: {token_data['user_id']}")
    # print(f"[GOOGLE DEBUG] token_data google_email: {token_data['google_email']}")

    try:
        if supabase:
            # print(f"[GOOGLE DEBUG] Supabase client is available")
            # Upsert: match on (user_id, google_email)
            existing = (
                supabase.table("google_tokens")
                .select("id")
                .eq("user_id", user_id)
                .eq("google_email", google_email)
                .execute()
            )
            # print(f"[GOOGLE DEBUG] Existing rows query result: {existing.data}")
            if existing.data:
                # print(f"[GOOGLE DEBUG] Updating existing row id={existing.data[0]['id']}")
                supabase.table("google_tokens").update(token_data).eq("id", existing.data[0]["id"]).execute()
                # print(f"[GOOGLE DEBUG] Update result: {update_result.data}")
            else:
                # print(f"[GOOGLE DEBUG] Inserting new row...")
                supabase.table("google_tokens").insert(token_data).execute()
                # print(f"[GOOGLE DEBUG] Insert result: {insert_result.data}")
        else:
            # print(f"[GOOGLE DEBUG] Supabase client is None — cannot store tokens!")
            pass
    except Exception as e:
        print(f"[GOOGLE] Failed to store tokens in Supabase: {e}")
        # print(f"[GOOGLE DEBUG] Exception type: {type(e).__name__}")
        # print(f"[GOOGLE DEBUG] Full exception: {repr(e)}")
        redirect_url = f"{settings.frontend_origin}/google-connected?success=false&error=db_error"
        return RedirectResponse(url=redirect_url)

    redirect_url = f"{settings.frontend_origin}/google-connected?success=true"
    return RedirectResponse(url=redirect_url)


@google_router.get("/status")
async def google_status(user_id: str = Query(...)):
    """Check if a user has Google Calendar connected. Returns connected accounts."""
    # print(f"[GOOGLE DEBUG] === Status check for user_id: {user_id} ===")
    if not supabase:
        # print(f"[GOOGLE DEBUG] Supabase client is None")
        return {"connected": False, "accounts": []}

    try:
        result = (
            supabase.table("google_tokens")
            .select("id, google_email")
            .eq("user_id", user_id)
            .execute()
        )
        # print(f"[GOOGLE DEBUG] Status query returned {len(result.data)} rows: {result.data}")
        return {
            "connected": len(result.data) > 0,
            "accounts": [{"id": r["id"], "email": r["google_email"]} for r in result.data],
        }
    except Exception as e:
        print(f"[GOOGLE] Status check failed: {e}")
        # print(f"[GOOGLE DEBUG] Status exception type: {type(e).__name__}, repr: {repr(e)}")
        return {"connected": False, "accounts": []}


@google_router.post("/disconnect")
async def google_disconnect(user_id: str = Query(...), google_email: str = Query(None)):
    """Remove stored Google tokens for a user. Optionally specify which account."""
    try:
        if supabase:
            query = supabase.table("google_tokens").delete().eq("user_id", user_id)
            if google_email:
                query = query.eq("google_email", google_email)
            query.execute()
    except Exception as e:
        print(f"[GOOGLE] Disconnect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"disconnected": True}
