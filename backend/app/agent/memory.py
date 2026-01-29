from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
import json

from app.agent.schema import UserProfile, ProjectPlan, MicroTask
from app.core.supabase import supabase


class Message(BaseModel):
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str | List
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionState(BaseModel):
    """Persistent state for a user session."""

    session_id: str
    user_id: Optional[str] = None
    user_profile: UserProfile = Field(default_factory=UserProfile)
    message_history: List[Message] = Field(default_factory=list)
    active_plans: List[ProjectPlan] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)

    def add_message(self, role: str, content: str | List) -> None:
        """Add a message to the history."""
        self.message_history.append(Message(role=role, content=content))
        self.last_active = datetime.now()

    def add_plan(self, plan: ProjectPlan) -> None:
        """Add a new plan to active plans."""
        self.active_plans.append(plan)
        self.last_active = datetime.now()

    def complete_task(self, task_name: str) -> None:
        """Mark a task as completed."""
        if task_name not in self.completed_tasks:
            self.completed_tasks.append(task_name)
        self.last_active = datetime.now()

    def get_progress(self) -> dict:
        """Calculate overall progress across all active plans."""
        total_tasks = sum(len(plan.tasks) for plan in self.active_plans)
        completed = len(self.completed_tasks)
        percentage = (completed / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "completed": completed,
            "total": total_tasks,
            "percentage": round(percentage, 1),
        }

    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get the most recent messages."""
        return self.message_history[-limit:]


class SessionStore:
    """Base session store interface."""

    def get_or_create(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> SessionState:
        raise NotImplementedError

    def save(self, session: SessionState) -> None:
        pass


class MemorySessionStore(SessionStore):
    """In-memory session storage (Old Implementation)."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                user_id=user_id,
                user_profile=user_profile or UserProfile(),
            )
        else:
            if user_profile:
                self._sessions[session_id].user_profile = user_profile
            self._sessions[session_id].last_active = datetime.now()

        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)


class SupabaseSessionStore(SessionStore):
    """Persistent storage using Supabase."""

    def _load_user_profile(self, user_id: str) -> UserProfile:
        """Load user profile from profiles table (source of truth for preferences)."""
        if not supabase or not user_id:
            return UserProfile()

        try:
            res = supabase.table("profiles").select("first_name, preferences").eq("id", user_id).execute()
            if res.data:
                data = res.data[0]
                prefs = data.get("preferences") or {}
                profile = UserProfile(
                    name=data.get("first_name") or "User",
                    role=prefs.get("role", "Professional"),
                    anchors=prefs.get("anchors", ["Morning Coffee", "After Lunch", "End of Day"]),
                )
                print(f"[MEMORY] Loaded profile for user {user_id[:8]}... | name={profile.name} | anchors={profile.anchors}")
                return profile
        except Exception as e:
            print(f"[MEMORY] Error loading user profile: {e}")

        print(f"[MEMORY] No profile found for user {user_id[:8]}..., using defaults")
        return UserProfile()

    def get_or_create(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> SessionState:
        if not supabase:
            print("Warning: Supabase not initialized, falling back to MemorySessionStore")
            return MemorySessionStore().get_or_create(session_id, user_id, user_profile)

        # 1. Try to fetch session
        res = supabase.table("sessions").select("*").eq("id", session_id).execute()
        
        if res.data:
            # Load existing session
            data = res.data[0]
            # Fetch user profile from profiles table (source of truth)
            loaded_profile = self._load_user_profile(user_id) if user_id else UserProfile()
            # Merge with provided profile (frontend may send updated name)
            if user_profile:
                loaded_profile.name = user_profile.name or loaded_profile.name
            session = SessionState(
                session_id=data["id"],
                user_id=data["user_id"],
                user_profile=loaded_profile,
            )
            
            # Load messages
            msg_res = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
            for m in msg_res.data:
                # Handle possible JSON/String conversion for text column
                content = m["content"]
                try:
                    if content.startswith('[') or content.startswith('{'):
                        content = json.loads(content)
                except:
                    pass
                    
                session.message_history.append(Message(
                    role=m["role"],
                    content=content,
                    timestamp=datetime.fromisoformat(m["created_at"])
                ))
            
            # Load goals and their associated tasks
            goals_res = supabase.table("goals").select("*").eq("user_id", user_id).eq("status", "active").execute()
            for g in goals_res.data:
                # Fetch tasks linked to this goal
                tasks_res = supabase.table("tasks").select("*").eq("goal_id", g["id"]).execute()
                tasks = []
                for t in tasks_res.data:
                    tasks.append(MicroTask(
                        task_name=t["task_name"],
                        estimated_minutes=t.get("estimated_minutes", 15),
                        energy_required=t.get("energy_required", "medium"),
                        assigned_anchor=t.get("assigned_anchor", ""),
                        rationale=t.get("rationale", "")
                    ))
                plan = ProjectPlan(
                    project_name=g["title"],
                    smart_goal_summary=g.get("description") or g["title"],
                    deadline=str(g.get("target_date") or ""),
                    tasks=tasks
                )
                session.active_plans.append(plan)
                
            return session
        
        # 2. Create new session if not found
        # Load profile from profiles table (source of truth)
        loaded_profile = self._load_user_profile(user_id) if user_id else UserProfile()
        # Merge with provided profile (frontend may send updated name)
        if user_profile:
            loaded_profile.name = user_profile.name or loaded_profile.name
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            user_profile=loaded_profile,
        )
        
        supabase.table("sessions").upsert({
            "id": session_id,
            "user_id": user_id,
            "last_active": datetime.now().isoformat()
        }).execute()
        
        return session

    def save(self, session: SessionState) -> None:
        """Save session state to Supabase."""
        if not supabase or not session.user_id: return

        # Update session metadata (user_profile stored in profiles table, not here)
        supabase.table("sessions").update({
            "last_active": datetime.now().isoformat()
        }).eq("id", session.session_id).execute()

        # Save new goals from active plans (skip if already persisted)
        for plan in session.active_plans:
            # Check if goal already exists for this user with same title
            existing = supabase.table("goals").select("id").eq("user_id", session.user_id).eq("title", plan.project_name).execute()

            if existing.data:
                # Goal already exists, skip
                continue

            # Try to parse deadline as datetime, otherwise store as None
            # (deadline is often human-readable like "End of this week")
            target_date = None
            if plan.deadline:
                try:
                    # Try ISO format parsing
                    target_date = datetime.fromisoformat(plan.deadline.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    # Not a valid datetime, store description in the description field instead
                    pass

            goal_data = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": plan.project_name,
                "description": f"{plan.smart_goal_summary} (Deadline: {plan.deadline})" if plan.deadline and not target_date else plan.smart_goal_summary,
                "target_date": target_date.isoformat() if target_date else None,
                "status": "active"
            }
            res = supabase.table("goals").insert(goal_data).execute()

            if res.data:
                goal_id = res.data[0]["id"]
                for task in plan.tasks:
                    task_data = {
                        "goal_id": goal_id,
                        "user_id": session.user_id,
                        "task_name": task.task_name,
                        "estimated_minutes": task.estimated_minutes,
                        "energy_required": task.energy_required,
                        "assigned_anchor": task.assigned_anchor,
                        "rationale": task.rationale
                    }
                    supabase.table("tasks").insert(task_data).execute()

    def add_message(self, session_id: str, user_id: str, role: str, content: str | List):
        """Helper to save message directly."""
        if not supabase or not user_id: return
        
        # Convert List content to string for TEXT column if necessary
        save_content = content
        if not isinstance(content, str):
            save_content = json.dumps(content)
            
        supabase.table("messages").insert({
            "session_id": session_id,
            "user_id": user_id, # Added for optimized schema
            "role": role,
            "content": save_content
        }).execute()


class HybridSessionStore:
    """Routes sessions to Memory or Supabase based on user_id."""

    def __init__(self):
        self.memory_store = MemorySessionStore()
        self.supabase_store = SupabaseSessionStore()

    def get_or_create(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> SessionState:
        if user_id:
            return self.supabase_store.get_or_create(session_id, user_id, user_profile)
        return self.memory_store.get_or_create(session_id, user_id, user_profile)

    def save(self, session: SessionState) -> None:
        if session.user_id:
            self.supabase_store.save(session)
        # In-memory is handled by object reference

    def add_message(self, session: SessionState, role: str, content: str | List):
        """Unified message adding with optional persistence."""
        session.add_message(role, content)
        if session.user_id and supabase:
            self.supabase_store.add_message(session.session_id, session.user_id, role, content)


# Global session store instance (Updated to Hybrid)
session_store = HybridSessionStore()
