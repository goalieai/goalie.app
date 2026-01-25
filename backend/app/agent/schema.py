from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# --- User Context ---
class UserProfile(BaseModel):
    name: str = "User"
    role: str = "Professional"
    anchors: List[str] = Field(
        default=["Morning Coffee", "After Lunch", "End of Day"],
        description="Daily habits like 'Morning Coffee', 'Start Laptop'",
    )


# --- Orchestrator: Intent Classification ---
class IntentClassification(BaseModel):
    """Output of the Intent Router node."""

    intent: Literal["casual", "planning", "coaching", "modify"] = Field(
        description="The classified user intent"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")


# --- Node 1 Output: SMART Goal ---
class SmartGoalSchema(BaseModel):
    summary: str = Field(description="A concise, active-voice summary of the goal")
    specific_outcome: str = Field(description="Exactly what will be built/done")
    measurable_metric: str = Field(
        description="How we know it's finished (e.g. '3 pages', '0 bugs')"
    )
    deadline: str = Field(
        description="A specific date or relative time (e.g. 'Next Friday')"
    )
    constraints: Optional[str] = Field(
        default=None, description="Any limitations mentioned (time, tools, etc)"
    )


# --- Node 2 Output: Raw Task List ---
class TaskList(BaseModel):
    tasks: List[str] = Field(
        description="A list of 3-7 distinct, atomic task names. Each must be doable in <20 mins.",
        min_length=3,
        max_length=7,
    )


# --- Node 3 Output: The Final Plan (MicroTasks) ---
class MicroTask(BaseModel):
    task_name: str = Field(description="Actionable task name")
    estimated_minutes: int = Field(description="Time needed (5-20 mins)", ge=5, le=20)
    energy_required: Literal["high", "medium", "low"]
    assigned_anchor: str = Field(
        description="The specific User Anchor this task is attached to"
    )
    rationale: str = Field(
        description="Why this anchor fits this task (e.g. 'High focus needs morning')"
    )


class ProjectPlan(BaseModel):
    project_name: str
    smart_goal_summary: str = Field(description="The SMART goal summary")
    deadline: str
    tasks: List[MicroTask]
