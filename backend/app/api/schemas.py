from typing import Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# --- TASKS ---


class TaskCreate(BaseModel):
    task_name: str
    goal_id: Optional[str] = None
    scheduled_text: Optional[str] = None  # "Tomorrow morning"
    scheduled_at: Optional[datetime] = None  # Sortable timestamp
    estimated_minutes: int = 15
    energy_required: Literal["high", "medium", "low"] = "medium"
    rationale: Optional[str] = None
    assigned_anchor: Optional[str] = None


class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    scheduled_text: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[Literal["pending", "in_progress", "completed"]] = None
    energy_required: Optional[Literal["high", "medium", "low"]] = None
    estimated_minutes: Optional[int] = None
    assigned_anchor: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    user_id: Optional[str]
    goal_id: Optional[str]
    session_id: Optional[str]
    task_name: str
    scheduled_text: Optional[str]
    scheduled_at: Optional[datetime]
    estimated_minutes: int
    energy_required: str
    assigned_anchor: Optional[str]
    rationale: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


# --- GOALS ---


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    emoji: str = "🎯"
    target_date: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None
    status: Optional[Literal["active", "achieved", "archived"]] = None
    target_date: Optional[datetime] = None


class GoalResponse(BaseModel):
    id: str
    user_id: Optional[str]
    session_id: Optional[str]
    title: str
    description: Optional[str]
    emoji: str
    status: str
    target_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# --- PROFILES ---


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None  # timezone, anchors, etc.


class ProfileResponse(BaseModel):
    id: str
    first_name: Optional[str]
    preferences: Optional[Dict[str, Any]]
    updated_at: datetime
