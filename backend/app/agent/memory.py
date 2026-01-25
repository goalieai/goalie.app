"""In-memory session store for conversation persistence."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.agent.schema import UserProfile, ProjectPlan


class Message(BaseModel):
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionState(BaseModel):
    """Persistent state for a user session."""

    session_id: str
    user_profile: UserProfile = Field(default_factory=UserProfile)
    message_history: List[Message] = Field(default_factory=list)
    active_plans: List[ProjectPlan] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)

    def add_message(self, role: str, content: str) -> None:
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
    """In-memory session storage (MVP implementation)."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(
        self,
        session_id: str,
        user_profile: Optional[UserProfile] = None,
    ) -> SessionState:
        """Get existing session or create a new one."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                user_profile=user_profile or UserProfile(),
            )
        else:
            # Update user profile if provided
            if user_profile:
                self._sessions[session_id].user_profile = user_profile
            self._sessions[session_id].last_active = datetime.now()

        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID, or None if not found."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        return list(self._sessions.keys())

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours. Returns count of removed."""
        now = datetime.now()
        old_sessions = [
            sid
            for sid, session in self._sessions.items()
            if (now - session.last_active).total_seconds() > max_age_hours * 3600
        ]
        for sid in old_sessions:
            del self._sessions[sid]
        return len(old_sessions)


# Global session store instance
session_store = SessionStore()
