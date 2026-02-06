# Agent Implementation - Missing Features Summary

## What the Frontend Expects

Based on `/frontend/src/pages/Index.tsx`, the UX shows:

### Task Display Structure:
```typescript
{
  now: {
    id: string
    action: string  // task_name
    time: string    // scheduled_text (e.g., "Morning Coffee", "After Lunch")
  },
  next: [
    { id, action, time }
  ],
  achieved: [
    { id, action, time }
  ]
}
```

### Key UI Features:
1. **"Done" Button** → Marks task as completed
2. **"Re-plan" Button** → Opens chat to reschedule
3. **Task Scheduling** → Tasks shown with human-readable times ("Morning Coffee", "Now", "Later")
4. **Progress Tracking** → Spiral shows completion rate

---

## What the Agent Currently Does ✅

1. ✅ Creates tasks with `scheduled_text` (anchor names like "Morning Coffee")
2. ✅ Saves tasks to Supabase/localStorage
3. ✅ Marks tasks as completed via `/tasks/{task_id}` PUT
4. ✅ Logs execution events to Opik

---

## What's Missing ❌

### 1. **Scheduled Times (`scheduled_at` field)**

**Problem:** Tasks have `scheduled_text` ("Morning", "Lunch") but NO actual timestamp.

**Why it matters:**
- Frontend comment says: `// Future: Use 'scheduled_at' to sort`
- Can't determine which task should be "NOW" vs "NEXT"
- Can't send time-based reminders
- Can't detect overdue tasks

**What needs to be added:**

#### Option A: Agent assigns specific times during planning
```python
# In context_matcher_node (nodes.py)
def assign_time_to_anchor(anchor: str, user_timezone: str) -> datetime:
    """Convert anchor to actual timestamp."""
    now = datetime.now(pytz.timezone(user_timezone))
    
    if "Morning" in anchor:
        return now.replace(hour=8, minute=0)
    elif "Lunch" in anchor:
        return now.replace(hour=12, minute=0)
    elif "Evening" in anchor:
        return now.replace(hour=18, minute=0)
    # etc...
```

#### Option B: User sets preferred times for each anchor
```python
# Store in user_profile
anchors = [
    {"name": "Morning Coffee", "preferred_time": "08:00"},
    {"name": "Lunch Break", "preferred_time": "12:30"},
    {"name": "End of Day", "preferred_time": "17:00"}
]
```

**Recommendation:** **Option A** - Agent auto-assigns reasonable defaults, user can adjust later.

---

### 2. **Reminder System**

**Problem:** No notification system exists.

**What needs to be built:**

#### Backend: Reminder Scheduler
```python
# app/services/reminders.py (NEW FILE)

from datetime import datetime, timedelta
import asyncio

async def schedule_reminders():
    """Background task to send reminders."""
    while True:
        # Check for tasks starting in 15 minutes
        upcoming = get_upcoming_tasks(minutes_ahead=15)
        
        for task in upcoming:
            await send_reminder(task)
        
        await asyncio.sleep(60)  # Check every minute

async def send_reminder(task):
    """Send notification (email, SMS, or push)."""
    # Option 1: Email via SendGrid
    # Option 2: SMS via Twilio
    # Option 3: Browser push notification
```

#### API Endpoint:
```python
# app/api/routes.py

@router.post("/reminders/subscribe")
async def subscribe_to_reminders(
    user_id: str,
    method: Literal["email", "sms", "push"],
    contact: str  # email address or phone number
):
    """Subscribe user to reminders."""
```

**Recommendation:** Start with **email reminders** (easiest to implement).

---

### 3. **Automatic Rescheduling Logic**

**Problem:** Frontend has "Re-plan" button but it just opens chat. No automatic rescheduling when tasks are missed.

**What needs to be built:**

```python
# app/agent/adaptive_scheduler.py (NEW FILE)

async def detect_and_reschedule_missed_tasks(user_id: str):
    """
    1. Find tasks where scheduled_at < now AND status != completed
    2. Find next available slot
    3. Update task with new scheduled_at
    4. Log to Opik
    """
    
async def find_next_available_slot(user_id: str, anchor_type: str) -> datetime:
    """
    Intelligent slot-finding:
    - Avoid overlaps with existing tasks
    - Respect user's working hours
    - Prefer same anchor type (if morning task missed, reschedule to tomorrow morning)
    """
```

**API Endpoint:**
```python
@router.post("/tasks/{task_id}/reschedule")
async def reschedule_task(
    task_id: str,
    reason: str = "user_requested"
):
    """Reschedule a task to next available slot."""
```

---

### 4. **Reminder Preferences in User Profile**

**Problem:** No way for users to customize when/how they get reminders.

**What needs to be added to schema:**

```python
# app/agent/schema.py

class UserProfile(BaseModel):
    name: str
    role: Optional[str] = None
    anchors: List[str] = []
    
    # NEW: Reminder preferences
    reminder_enabled: bool = True
    reminder_method: Literal["email", "sms", "push"] = "email"
    reminder_minutes_before: int = 15
    quiet_hours_start: Optional[time] = None  # e.g., 22:00
    quiet_hours_end: Optional[time] = None    # e.g., 07:00
    timezone: str = "America/Los_Angeles"
```

---

## Priority Implementation Order

### 🔴 CRITICAL (Do First - Required for Demo)

#### 1. Add `scheduled_at` timestamps to tasks
**File:** `app/agent/nodes.py` (context_matcher_node)
**Time:** 1 hour
**Why:** Enables sorting, "NOW" detection, and reminder scheduling

#### 2. Create adaptive rescheduling logic
**File:** `app/agent/adaptive_scheduler.py` (NEW)
**Time:** 2 hours
**Why:** Core value prop - makes Goalie different from calendars

#### 3. Add `/tasks/{task_id}/reschedule` API endpoint
**File:** `app/api/routes.py`
**Time:** 30 minutes
**Why:** Connects "Re-plan" button to actual functionality

---

### 🟡 IMPORTANT (Nice-to-Have for Demo)

#### 4. Email reminder system
**File:** `app/services/reminders.py` (NEW)
**Time:** 2 hours
**Why:** Shows "reminders" feature in pitch

#### 5. Background task scheduler
**File:** `app/main.py` (add startup event)
**Time:** 1 hour
**Why:** Runs reminder checker in background

---

### 🟢 OPTIONAL (Post-Hackathon)

#### 6. User reminder preferences UI
**Frontend customization**

#### 7. SMS/Push notifications
**Twilio or FCM integration**

---

## Immediate Next Steps

**I recommend building these 3 features NOW:**

1. **Add scheduled_at logic** (1 hour)
2. **Build adaptive rescheduler** (2 hours)  
3. **Wire up Re-plan button** (30 minutes)

This gives you a **fully functional demo** of the core value prop:
- ✅ Agent schedules tasks at specific times
- ✅ Tasks automatically reschedule when missed
- ✅ Opik tracks all execution events
- ✅ Dashboard shows +25% improvement

**Total time:** ~3.5 hours

Should I start implementing these now?
