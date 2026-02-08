Create a new event on the user's Google Calendar.

## When to Use

- User asks to block time on their calendar
- User wants to schedule a specific event or reminder
- User asks to add something to their calendar

## Examples

User: "Block 30 minutes tomorrow at 9am for reading"
→ create_calendar_event(title="Reading time", date="2026-02-08", start_time="09:00", duration_minutes=30)

User: "Add a meeting on Friday at 2pm for 1 hour"
→ create_calendar_event(title="Meeting", date="2026-02-13", start_time="14:00", duration_minutes=60)

User: "Schedule gym time Monday at 7am"
→ create_calendar_event(title="Gym", date="2026-02-09", start_time="07:00", duration_minutes=60, description="Workout session")
