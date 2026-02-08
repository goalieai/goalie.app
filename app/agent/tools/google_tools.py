"""Google Calendar tools for the conversational agent.

Uses a closure-based factory pattern so each tool instance captures
the user_id and can fetch per-user Google OAuth credentials.
"""

import asyncio
from typing import Optional, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# ── Input schemas ──────────────────────────────────────────────

class ReadCalendarInput(BaseModel):
    """Input schema for read_calendar tool."""
    days_ahead: int = Field(
        default=3,
        description="Number of days ahead to fetch events (1-14)",
        ge=1,
        le=14,
    )


class CreateCalendarEventInput(BaseModel):
    """Input schema for create_calendar_event tool."""
    title: str = Field(description="Event title/summary")
    date: str = Field(description="Date in YYYY-MM-DD format")
    start_time: str = Field(description="Start time in HH:MM (24h) format")
    duration_minutes: int = Field(
        default=30,
        description="Duration in minutes",
        ge=5,
        le=480,
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional event description",
    )


# ── Tool factory ───────────────────────────────────────────────

def create_google_tools(user_id: str) -> List[StructuredTool]:
    """Create Google Calendar tools bound to a specific user.

    Returns an empty list if the user has no Google credentials,
    so callers can safely do `STATIC_TOOLS + create_google_tools(uid)`.
    """
    from app.services.calendar_service import get_user_google_credentials

    # Fast guard: skip if user has no Google connected
    creds = get_user_google_credentials(user_id)
    if not creds:
        return []

    # ── read_calendar closure ──────────────────────────────────
    def _read_calendar(days_ahead: int = 3) -> str:
        """Read upcoming Google Calendar events."""
        from app.services.calendar_service import get_calendar_context

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, get_calendar_context(user_id, days_ahead)
                ).result()
        else:
            result = asyncio.run(get_calendar_context(user_id, days_ahead))

        return result if result else "No upcoming events found."

    # ── create_calendar_event closure ──────────────────────────
    def _create_calendar_event(
        title: str,
        date: str,
        start_time: str,
        duration_minutes: int = 30,
        description: Optional[str] = None,
    ) -> str:
        """Create a new Google Calendar event."""
        from datetime import datetime, timedelta
        from app.services.calendar_service import (
            get_user_google_credentials,
            _build_calendar_service,
        )

        creds = get_user_google_credentials(user_id)
        if not creds:
            return "Error: Google Calendar is not connected."

        service = _build_calendar_service(creds)

        try:
            start_dt = datetime.fromisoformat(f"{date}T{start_time}:00")
        except ValueError:
            return f"Error: Invalid date/time format. Use YYYY-MM-DD and HH:MM. Got date='{date}', start_time='{start_time}'."

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }
        if description:
            event_body["description"] = description

        try:
            result = (
                service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )
            link = result.get("htmlLink", "")
            return (
                f"Created event '{title}' on {date} at {start_time} "
                f"({duration_minutes} min). Link: {link}"
            )
        except Exception as e:
            return f"Error creating calendar event: {e}"

    # ── Build tool objects ─────────────────────────────────────
    from app.agent.tools.crud import load_tool_description

    read_cal_tool = StructuredTool.from_function(
        func=_read_calendar,
        name="read_calendar",
        description=load_tool_description("read_calendar"),
        args_schema=ReadCalendarInput,
    )

    create_event_tool = StructuredTool.from_function(
        func=_create_calendar_event,
        name="create_calendar_event",
        description=load_tool_description("create_calendar_event"),
        args_schema=CreateCalendarEventInput,
    )

    return [read_cal_tool, create_event_tool]
