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
            session = SessionState(
                session_id=data["id"],
                user_id=data["user_id"],
                user_profile=UserProfile(**data["user_profile"]),
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
            
            # Load plans and tasks
            plan_res = supabase.table("plans").select("*, tasks(*)").eq("session_id", session_id).execute()
            for p in plan_res.data:
                tasks = [MicroTask(**t) for t in p["tasks"]]
                plan = ProjectPlan(
                    project_name=p["project_name"],
                    smart_goal_summary=p["smart_goal_summary"],
                    deadline=p["deadline"],
                    tasks=tasks
                )
                session.active_plans.append(plan)
                
            return session
        
        # 2. Create new session if not found
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            user_profile=user_profile or UserProfile(),
        )
        
        supabase.table("sessions").upsert({
            "id": session_id,
            "user_id": user_id,
            "user_profile": session.user_profile.model_dump(),
            "last_active": datetime.now().isoformat()
        }).execute()
        
        return session

    def save(self, session: SessionState) -> None:
        """Save session state to Supabase."""
        if not supabase or not session.user_id: return

        # Update session metadata
        supabase.table("sessions").update({
            "user_profile": session.user_profile.model_dump(),
            "last_active": datetime.now().isoformat()
        }).eq("id", session.session_id).execute()

        # Update plans (simplified: just save the active plans)
        for plan in session.active_plans:
            plan_data = {
                "session_id": session.session_id,
                "user_id": session.user_id, # Added for optimized schema
                "project_name": plan.project_name,
                "smart_goal_summary": plan.smart_goal_summary,
                "deadline": plan.deadline
            }
            # Upsert plan based on project_name + session_id or similar?
            # For hackathon simplicity, let's just insert/update if we had IDs
            # but we'll stick to basic sync for now.
            res = supabase.table("plans").upsert(plan_data, on_conflict="session_id,project_name").execute()
            
            if res.data:
                plan_id = res.data[0]["id"]
                for task in plan.tasks:
                    task_data = {
                        "plan_id": plan_id,
                        "user_id": session.user_id, # Added for optimized schema
                        "task_name": task.task_name,
                        "estimated_minutes": task.estimated_minutes,
                        "energy_required": task.energy_required,
                        "assigned_anchor": task.assigned_anchor,
                        "rationale": task.rationale
                    }
                    supabase.table("tasks").upsert(task_data, on_conflict="plan_id,task_name").execute()

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
