from datetime import datetime, timedelta, timezone
from typing import List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.supabase import supabase
from app.agent.schema import ProjectPlan


def get_user_google_credentials(user_id: str, google_email: Optional[str] = None) -> Optional[Credentials]:
    """
    Load Google OAuth credentials from Supabase for a user.
    Returns Credentials or None if not connected.
    Auto-refreshes expired tokens and saves them back.

    If google_email is specified, loads that specific account.
    Otherwise, loads the first connected account (most recently created).
    """
    # print(f"[GOOGLE DEBUG] === get_user_google_credentials for user_id: {user_id}, google_email: {google_email} ===")
    if not supabase or not user_id:
        # print(f"[GOOGLE DEBUG] Early return: supabase={bool(supabase)}, user_id={bool(user_id)}")
        return None

    query = supabase.table("google_tokens").select("*").eq("user_id", user_id)
    if google_email:
        query = query.eq("google_email", google_email)

    result = query.order("created_at", desc=True).limit(1).execute()
    # print(f"[GOOGLE DEBUG] Credentials query returned {len(result.data)} rows")
    if not result.data:
        # print(f"[GOOGLE DEBUG] No credentials found for user")
        return None

    token_data = result.data[0]
    # print(f"[GOOGLE DEBUG] Loaded credentials for google_email: {token_data.get('google_email')}")
    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/calendar"]),
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed tokens back (match by id for precision)
        supabase.table("google_tokens").update({
            "access_token": creds.token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }).eq("id", token_data["id"]).execute()

    return creds


def _build_calendar_service(creds: Credentials):
    """Build a Google Calendar API service from credentials."""
    return build("calendar", "v3", credentials=creds)


async def create_calendar_events_for_plan(user_id: str, plan: ProjectPlan) -> List[dict]:
    """
    Create Google Calendar events for all tasks in a confirmed plan.

    For each MicroTask with scheduled_at:
    - Summary: [Goalie] task_name
    - Description: goal context + rationale + energy level
    - Duration: estimated_minutes
    - Reminder: 10min popup

    Returns list of created event details. Returns [] if user has no Google tokens.
    """
    creds = get_user_google_credentials(user_id)
    if not creds:
        return []

    service = _build_calendar_service(creds)
    created_events = []

    for task in plan.tasks:
        # Use scheduled_at if available, otherwise skip
        if task.scheduled_at:
            try:
                start_dt = datetime.fromisoformat(task.scheduled_at)
            except (ValueError, TypeError):
                continue
        else:
            # No scheduled time — skip calendar event for this task
            continue

        end_dt = start_dt + timedelta(minutes=task.estimated_minutes)

        # Build event description
        description_parts = [
            f"Goal: {plan.smart_goal_summary}",
            f"Rationale: {task.rationale}",
            f"Energy: {task.energy_required}",
            f"Estimated: {task.estimated_minutes} min",
        ]

        event_body = {
            "summary": f"[Goalie] {task.task_name}",
            "description": "\n".join(description_parts),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }

        try:
            result = (
                service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )
            created_events.append({
                "event_id": result.get("id"),
                "link": result.get("htmlLink"),
                "task_name": task.task_name,
            })
            print(f"[CALENDAR] Created event for '{task.task_name}': {result.get('htmlLink')}")
        except Exception as e:
            print(f"[CALENDAR] Failed to create event for '{task.task_name}': {e}")

    return created_events


async def fetch_raw_calendar_events(user_id: str, days_ahead: int = 7) -> list[dict]:
    """
    Fetch raw calendar events as parsed dicts with datetime start/end.

    Returns a list of {"start": datetime, "end": datetime, "summary": str}.
    Returns [] if user has no Google tokens or on error.
    """
    creds = get_user_google_credentials(user_id)
    if not creds:
        return []

    service = _build_calendar_service(creds)

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
    except Exception as e:
        print(f"[CALENDAR] Failed to fetch raw events: {e}")
        return []

    parsed = []
    for event in events_result.get("items", []):
        start_raw = event["start"].get("dateTime", event["start"].get("date"))
        end_raw = event["end"].get("dateTime", event["end"].get("date"))
        try:
            start_dt = datetime.fromisoformat(start_raw)
            end_dt = datetime.fromisoformat(end_raw)
            parsed.append({
                "start": start_dt,
                "end": end_dt,
                "summary": event.get("summary", "Untitled"),
            })
        except (ValueError, TypeError):
            continue

    return parsed


async def get_calendar_context(user_id: str, days_ahead: int = 3) -> str:
    """
    Fetch upcoming calendar events and format as context for the agent.

    Returns a formatted string with upcoming events, or empty string
    if user has no Google tokens connected.
    """
    creds = get_user_google_credentials(user_id)
    if not creds:
        return ""

    service = _build_calendar_service(creds)

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
            )
            .execute()
        )
    except Exception as e:
        print(f"[CALENDAR] Failed to fetch events for context: {e}")
        return ""

    events = events_result.get("items", [])
    if not events:
        return "## Google Calendar\nNo upcoming events in the next 3 days."

    lines = [f"## Google Calendar (next {days_ahead} days)"]
    for event in events:
        start_raw = event["start"].get("dateTime", event["start"].get("date"))
        summary = event.get("summary", "Untitled")
        try:
            dt = datetime.fromisoformat(start_raw)
            lines.append(f"- {dt.strftime('%a %b %d, %I:%M %p')}: {summary}")
        except (ValueError, TypeError):
            lines.append(f"- {start_raw}: {summary}")

    return "\n".join(lines)
