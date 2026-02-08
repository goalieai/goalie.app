"""
Adaptive Task Scheduling and Rescheduling Logic

This module handles:
1. Converting anchor names to actual timestamps
2. Finding next available slots for tasks
3. Automatic rescheduling of missed tasks
4. Logging reschedule events to Opik
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from zoneinfo import ZoneInfo
from app.core.supabase import supabase
from app.agent.execution_tracker import execution_tracker


# Default time mappings for common anchors
ANCHOR_TIME_MAP = {
    "Morning Coffee": {"hour": 8, "minute": 0},
    "Morning": {"hour": 8, "minute": 0},
    "Start Laptop": {"hour": 9, "minute": 0},
    "Mid-Morning": {"hour": 10, "minute": 30},
    "Before Lunch": {"hour": 11, "minute": 30},
    "Lunch Break": {"hour": 12, "minute": 30},
    "After Lunch": {"hour": 13, "minute": 30},
    "Afternoon": {"hour": 14, "minute": 0},
    "Mid-Afternoon": {"hour": 15, "minute": 30},
    "End of Day": {"hour": 17, "minute": 0},
    "Evening": {"hour": 18, "minute": 0},
    "After Dinner": {"hour": 19, "minute": 30},
    "Before Bed": {"hour": 21, "minute": 0},
    "Night": {"hour": 21, "minute": 0},
}


async def get_available_anchors(
    user_id: str,
    anchors: List[str],
    days_ahead: int = 7,
    task_duration_minutes: int = 20,
    timezone: str = "America/Los_Angeles",
) -> Dict[str, List[str]]:
    """
    Build an availability map: for each day, which anchors are free.

    Checks each anchor timeslot against both:
    - Google Calendar events (external conflicts)
    - Existing Goally tasks (internal conflicts)

    Returns:
        {"2026-02-07": ["Morning Coffee", "End of Day"], "2026-02-08": [...], ...}
        If no Google Calendar, all anchors are returned as available (only Goally task conflicts checked).
    """
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    start_date = now.date()

    # Fetch Google Calendar events
    calendar_events: list[dict] = []
    try:
        from app.services.calendar_service import fetch_raw_calendar_events
        calendar_events = await fetch_raw_calendar_events(user_id, days_ahead)
    except Exception as e:
        print(f"[SCHEDULER] Failed to fetch calendar events: {e}")

    # Fetch existing Goally tasks
    goally_tasks: list[dict] = []
    if supabase:
        try:
            res = supabase.table("tasks").select("scheduled_at,estimated_minutes").eq(
                "user_id", user_id
            ).neq("status", "completed").execute()
            goally_tasks = res.data or []
        except Exception as e:
            print(f"[SCHEDULER] Failed to fetch Goally tasks: {e}")

    # Parse Goally tasks into start/end intervals
    goally_intervals: list[dict] = []
    for t in goally_tasks:
        if t.get("scheduled_at"):
            try:
                t_start = datetime.fromisoformat(
                    t["scheduled_at"].replace("Z", "+00:00")
                )
                t_end = t_start + timedelta(minutes=t.get("estimated_minutes", 15))
                goally_intervals.append({"start": t_start, "end": t_end})
            except (ValueError, TypeError):
                continue

    # All blocking intervals (Google + Goally)
    all_busy = calendar_events + goally_intervals

    # Build availability map
    availability: Dict[str, List[str]] = {}
    for day_offset in range(days_ahead):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.isoformat()

        # Filter busy intervals for this day
        days_busy = []
        for event in all_busy:
            event_start = event["start"]
            # Handle timezone-aware vs naive comparison
            if hasattr(event_start, "date"):
                if event_start.date() == current_date:
                    days_busy.append(event)

        available_anchors = []
        for anchor_name in anchors:
            # Get anchor timestamp for this day
            anchor_dt = anchor_to_timestamp(anchor_name, timezone, datetime(
                current_date.year, current_date.month, current_date.day,
                tzinfo=tz,
            ))
            anchor_end = anchor_dt + timedelta(minutes=task_duration_minutes)

            # Check overlap with any busy interval
            is_blocked = False
            for busy in days_busy:
                busy_start = busy["start"]
                busy_end = busy["end"]
                # Make timezone-aware if needed for comparison
                if busy_start.tzinfo is None:
                    busy_start = busy_start.replace(tzinfo=tz)
                if busy_end.tzinfo is None:
                    busy_end = busy_end.replace(tzinfo=tz)
                # Standard overlap: (StartA < EndB) and (EndA > StartB)
                if anchor_dt < busy_end and anchor_end > busy_start:
                    is_blocked = True
                    break

            if not is_blocked:
                available_anchors.append(anchor_name)

        availability[date_str] = available_anchors

    return availability


def format_availability_for_prompt(availability: Dict[str, List[str]]) -> str:
    """Format the availability map as a concise string for the LLM prompt."""
    from datetime import date as date_type

    lines = ["## Available Time Slots (anchors with NO calendar conflicts)"]
    for date_str, anchors in availability.items():
        try:
            d = datetime.fromisoformat(date_str)
            day_label = d.strftime("%A %b %d")
        except ValueError:
            day_label = date_str

        if anchors:
            slots = ", ".join(anchors)
            lines.append(f"- **{day_label}:** {slots}")
        else:
            lines.append(f"- **{day_label}:** NO available slots")

    return "\n".join(lines)


def anchor_to_timestamp(
    anchor: str,
    timezone: str = "America/Los_Angeles",
    base_date: Optional[datetime] = None
) -> datetime:
    """
    Convert an anchor name to an actual timestamp.
    
    Args:
        anchor: Anchor name like "Morning Coffee" or "After Lunch"
        timezone: User's timezone
        base_date: Base date to use (defaults to today)
    
    Returns:
        Timestamp for the anchor
    """
    if base_date is None:
        base_date = datetime.now(ZoneInfo(timezone))
    
    # Find matching time in map
    time_config = None
    for key, config in ANCHOR_TIME_MAP.items():
        if key.lower() in anchor.lower():
            time_config = config
            break
    
    # Default to afternoon if no match
    if time_config is None:
        time_config = {"hour": 14, "minute": 0}
    
    # Create timestamp
    scheduled_time = base_date.replace(
        hour=time_config["hour"],
        minute=time_config["minute"],
        second=0,
        microsecond=0
    )
    
    return scheduled_time


async def find_next_available_slot(
    user_id: str,
    anchor_preference: str,
    estimated_minutes: int = 15,
    timezone: str = "America/Los_Angeles"
) -> Dict[str, any]:
    """
    Find the next available time slot for a task.
    
    Tries to match the original anchor type (morning → morning, evening → evening).
    Checks for conflicts with existing scheduled tasks.
    
    Args:
        user_id: User ID
        anchor_preference: Original anchor (to prefer similar times)
        estimated_minutes: Task duration
        timezone: User's timezone
    
    Returns:
        dict with 'scheduled_at' (datetime) and 'scheduled_text' (str)
    """
    if not supabase:
        # Fallback for tests
        now = datetime.now(ZoneInfo(timezone))
        return {
            "scheduled_at": now + timedelta(days=1),
            "scheduled_text": anchor_preference
        }
    
    try:
        # Get user's existing tasks
        response = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
        existing_tasks = response.data or []
        
        # Determine time of day for anchor
        anchor_lower = anchor_preference.lower()
        is_morning = any(word in anchor_lower for word in ["morning", "breakfast", "coffee"])
        is_afternoon = any(word in anchor_lower for word in ["lunch", "afternoon"])
        is_evening = any(word in anchor_lower for word in ["evening", "dinner", "night", "bed"])
        
        # Start searching from tomorrow
        now = datetime.now(ZoneInfo(timezone))
        search_date = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Try next 7 days
        for day_offset in range(7):
            candidate_date = search_date + timedelta(days=day_offset)
            
            # Try slots matching original time of day first
            time_slots = []
            if is_morning:
                time_slots = ["Morning Coffee", "Mid-Morning"]
            elif is_afternoon:
                time_slots = ["After Lunch", "Mid-Afternoon"]
            elif is_evening:
                time_slots = ["End of Day", "Evening", "After Dinner"]
            else:
                time_slots = ["After Lunch", "Mid-Afternoon", "End of Day"]
            
            for slot_name in time_slots:
                slot_time = anchor_to_timestamp(slot_name, timezone, candidate_date)
                
                # Check for conflicts
                has_conflict = False
                for task in existing_tasks:
                    if task.get("scheduled_at"):
                        task_time = datetime.fromisoformat(task["scheduled_at"].replace("Z", "+00:00"))
                        task_duration = task.get("estimated_minutes", 15)
                        
                        # Simple overlap check (±task duration buffer)
                        if abs((task_time - slot_time).total_seconds()) < (task_duration + estimated_minutes) * 60:
                            has_conflict = True
                            break
                
                if not has_conflict:
                    return {
                        "scheduled_at": slot_time,
                        "scheduled_text": slot_name
                    }
        
        # Fallback: just use tomorrow at the original anchor time
        fallback_time = anchor_to_timestamp(anchor_preference, timezone, search_date)
        return {
            "scheduled_at": fallback_time,
            "scheduled_text": anchor_preference
        }
        
    except Exception as e:
        print(f"[SCHEDULER] Error finding slot: {e}")
        # Fallback
        now = datetime.now(ZoneInfo(timezone))
        return {
            "scheduled_at": now + timedelta(days=1),
            "scheduled_text": anchor_preference
        }


async def reschedule_task(
    task_id: str,
    user_id: str,
    reason: str = "user_requested",
    timezone: str = "America/Los_Angeles"
) -> bool:
    """
    Reschedule a task to the next available slot.
    
    Args:
        task_id: Task ID to reschedule
        user_id: User ID
        reason: Reason for rescheduling
        timezone: User's timezone
    
    Returns:
        True if successful
    """
    if not supabase:
        print("[SCHEDULER] Supabase not available")
        return False
    
    try:
        # Get task details
        response = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
        if not response.data:
            print(f"[SCHEDULER] Task {task_id} not found")
            return False
        
        task = response.data[0]
        original_anchor = task.get("assigned_anchor", "After Lunch")
        original_date = task.get("scheduled_at")
        estimated_minutes = task.get("estimated_minutes", 15)
        
        # Find next slot
        new_slot = await find_next_available_slot(user_id, original_anchor, estimated_minutes, timezone)
        
        # Update task
        update_data = {
            "scheduled_at": new_slot["scheduled_at"].isoformat(),
            "scheduled_text": new_slot["scheduled_text"],
            "was_rescheduled": True
        }
        
        supabase.table("tasks").update(update_data).eq("id", task_id).execute()
        
        # Log to Opik
        execution_tracker.log_reschedule(
            task_id=task_id,
            task_name=task.get("task_name", "Unknown Task"),
            user_id=user_id,
            goal_id=task.get("goal_id"),
            original_date=original_date or "unknown",
            new_date=new_slot["scheduled_at"].strftime("%Y-%m-%d %H:%M"),
            reason=reason
        )
        
        print(f"[SCHEDULER] Rescheduled task {task_id}: {original_date} → {new_slot['scheduled_at']}")
        return True
        
    except Exception as e:
        print(f"[SCHEDULER] Error rescheduling task: {e}")
        return False


async def detect_and_reschedule_missed_tasks(
    user_id: str,
    timezone: str = "America/Los_Angeles"
) -> List[str]:
    """
    Detect overdue tasks and automatically reschedule them.
    
    Args:
        user_id: User ID
        timezone: User's timezone
    
    Returns:
        List of rescheduled task IDs
    """
    if not supabase:
        return []
    
    try:
        now = datetime.now(ZoneInfo(timezone))
        
        # Find tasks that are overdue and not completed
        response = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
        tasks = response.data or []
        
        rescheduled = []
        for task in tasks:
            # Skip completed tasks
            if task.get("status") == "completed":
                continue
            
            # Check if task is overdue
            scheduled_at = task.get("scheduled_at")
            if scheduled_at:
                task_time = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                
                # If task was scheduled more than 1 hour ago and not completed
                if task_time < (now - timedelta(hours=1)):
                    success = await reschedule_task(
                        task_id=task["id"],
                        user_id=user_id,
                        reason="auto_missed_deadline",
                        timezone=timezone
                    )
                    if success:
                        rescheduled.append(task["id"])
        
        if rescheduled:
            print(f"[SCHEDULER] Auto-rescheduled {len(rescheduled)} missed tasks for user {user_id}")
        
        return rescheduled
        
    except Exception as e:
        print(f"[SCHEDULER] Error detecting missed tasks: {e}")
        return []
