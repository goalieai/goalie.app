from typing import List, Optional, Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import traceback

from app.agent.graph import run_agent, run_planning_pipeline, run_orchestrator
from app.agent.schema import UserProfile, MicroTask

router = APIRouter()


# ============================================================
# UNIFIED CHAT ENDPOINT (with Orchestrator)
# ============================================================


class UnifiedChatRequest(BaseModel):
    """Request for the unified chat endpoint with session support."""

    message: str = Field(description="The user's message")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for conversation continuity"
    )
    user_id: Optional[str] = Field(
        default=None, description="Optional user ID for persistent storage in Supabase"
    )
    user_profile: Optional[dict] = Field(
        default=None,
        description="User profile with name and anchors",
        examples=[{"name": "Jose", "anchors": ["Morning", "Lunch", "Evening"]}],
    )


class ProgressResponse(BaseModel):
    """Progress information for active plans."""

    completed: int
    total: int
    percentage: float


class ActionPayload(BaseModel):
    """Payload for an action to be performed by the frontend."""

    type: Literal["create_task", "complete_task", "create_goal", "update_task"]
    data: dict


class UnifiedChatResponse(BaseModel):
    """Response from the unified chat endpoint."""

    session_id: str
    intent_detected: str
    response: str
    plan: Optional[dict] = None
    progress: Optional[ProgressResponse] = None
    actions: List[ActionPayload] = []


@router.post("/chat", response_model=UnifiedChatResponse)
async def chat(request: UnifiedChatRequest):
    """
    Unified chat endpoint with intelligent routing.

    The orchestrator classifies user intent and routes to:
    - **casual**: Greetings, small talk, general questions
    - **planning**: Create a new goal/plan
    - **coaching**: Review progress, handle setbacks, motivation
    - **modify**: Adjust existing plans (routes to coaching for now)

    Session ID enables conversation memory across requests.
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid4())

        # Parse user profile if provided
        user_profile = None
        if request.user_profile:
            user_profile = UserProfile(
                name=request.user_profile.get("name", "User"),
                role=request.user_profile.get("role", "Professional"),
                anchors=request.user_profile.get(
                    "anchors", ["Morning Coffee", "After Lunch", "End of Day"]
                ),
            )

        # Run orchestrator
        result = await run_orchestrator(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
            user_profile=user_profile,
        )

        # Build response
        response = UnifiedChatResponse(
            session_id=result["session_id"],
            intent_detected=result["intent_detected"],
            response=result["response"],
            plan=result["plan"].model_dump() if result.get("plan") else None,
            progress=(
                ProgressResponse(**result["progress"])
                if result.get("progress")
                else None
            ),
            actions=result.get("actions", []),
        )

        return response

    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# LEGACY CHAT ENDPOINT (for backwards compatibility)
# ============================================================


class LegacyChatRequest(BaseModel):
    message: str


class LegacyChatResponse(BaseModel):
    response: str


@router.post("/chat/legacy", response_model=LegacyChatResponse)
async def legacy_chat(request: LegacyChatRequest):
    """Send a message to the Goally agent (legacy mode without orchestrator)."""
    try:
        response = await run_agent(request.message)
        return LegacyChatResponse(response=response)
    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- Planning Pipeline Endpoint ---
class PlanRequest(BaseModel):
    goal: str = Field(description="The user's goal (e.g., 'Launch my portfolio website')")
    user_name: Optional[str] = "User"
    user_role: Optional[str] = "Professional"
    anchors: Optional[List[str]] = Field(
        default=["Morning Coffee", "After Lunch", "End of Day"],
        description="User's daily habit anchors",
    )


class TaskResponse(BaseModel):
    task_name: str
    estimated_minutes: int
    energy_required: str
    assigned_anchor: str
    rationale: str


class PlanResponse(BaseModel):
    project_name: str
    smart_goal_summary: str
    deadline: str
    tasks: List[TaskResponse]
    # Include intermediate artifacts for debugging/observability
    raw_smart_goal: Optional[dict] = None


@router.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """
    Run the full planning pipeline: SMART Refiner -> Task Splitter -> Context Matcher.

    Returns a complete ProjectPlan with micro-tasks assigned to user anchors.
    """
    try:
        user_profile = UserProfile(
            name=request.user_name,
            role=request.user_role,
            anchors=request.anchors,
        )

        result = await run_planning_pipeline(
            goal=request.goal,
            user_profile=user_profile,
        )

        final_plan = result["final_plan"]
        smart_goal = result["smart_goal"]

        return PlanResponse(
            project_name=final_plan.project_name,
            smart_goal_summary=final_plan.smart_goal_summary,
            deadline=final_plan.deadline,
            tasks=[
                TaskResponse(
                    task_name=task.task_name,
                    estimated_minutes=task.estimated_minutes,
                    energy_required=task.energy_required,
                    assigned_anchor=task.assigned_anchor,
                    rationale=task.rationale,
                )
                for task in final_plan.tasks
            ],
            raw_smart_goal=smart_goal.model_dump() if smart_goal else None,
        )
    except Exception as e:
        print(f"Planning error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
