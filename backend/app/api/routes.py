from typing import List, Optional, Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import traceback
from datetime import datetime

from app.agent.graph import run_agent, run_planning_pipeline, run_orchestrator
from app.agent.schema import UserProfile, MicroTask
from app.core.supabase import supabase
from app.api import schemas

router = APIRouter()


@router.get("/")
async def api_root():
    """Root API endpoint."""
    return {"message": "Goally API", "status": "running"}


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


# ============================================================
# CRUD ENDPOINTS
# ============================================================

# --- PROFILES ---

@router.get("/profile/{user_id}", response_model=schemas.ProfileResponse)
async def get_profile(user_id: str):
    """Get user profile."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        response = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return response.data[0]
    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile/{user_id}", response_model=schemas.ProfileResponse)
async def update_profile(user_id: str, profile: schemas.ProfileUpdate):
    """Update user profile."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        # Prepare update data, removing None values
        update_data = {k: v for k, v in profile.model_dump().items() if v is not None}
        
        response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        
        if not response.data:
            # Try inserting if not found (upsert behavior)
            response = supabase.table("profiles").insert({"id": user_id, **update_data}).execute()
            
        return response.data[0]
    except Exception as e:
        print(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- TASKS ---

@router.get("/tasks", response_model=List[schemas.TaskResponse])
async def list_tasks(user_id: str = Query(..., description="User ID to fetch tasks for")):
    """List all tasks for a user."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        response = supabase.table("tasks").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks", response_model=schemas.TaskResponse)
async def create_task(task: schemas.TaskCreate, user_id: str = Query(..., description="User ID")):
    """Create a new task."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        task_data = task.model_dump()
        task_data["user_id"] = user_id
        
        response = supabase.table("tasks").insert(task_data).execute()
        return response.data[0]
    except Exception as e:
        print(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
async def update_task(task_id: str, task: schemas.TaskUpdate, user_id: str = Query(..., description="User ID for authorization")):
    """Update a task."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        update_data = {k: v for k, v in task.model_dump().items() if v is not None}
        
        # Verify ownership ensuring user_id matches (basic check)
        response = supabase.table("tasks").update(update_data).eq("id", task_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Task not found or unauthorized")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user_id: str = Query(..., description="User ID for authorization")):
    """Delete a task."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        response = supabase.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()
        
        if not response.data:
             raise HTTPException(status_code=404, detail="Task not found or unauthorized")
             
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- GOALS ---

@router.get("/goals", response_model=List[schemas.GoalResponse])
async def list_goals(user_id: str = Query(..., description="User ID")):
    """List all goals for a user."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        response = supabase.table("goals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goals", response_model=schemas.GoalResponse)
async def create_goal(goal: schemas.GoalCreate, user_id: str = Query(..., description="User ID")):
    """Create a new goal."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        goal_data = goal.model_dump()
        goal_data["user_id"] = user_id
        
        response = supabase.table("goals").insert(goal_data).execute()
        return response.data[0]
    except Exception as e:
        print(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/goals/{goal_id}", response_model=schemas.GoalResponse)
async def update_goal(goal_id: str, goal: schemas.GoalUpdate, user_id: str = Query(..., description="User ID")):
    """Update a goal."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        update_data = {k: v for k, v in goal.model_dump().items() if v is not None}
        
        response = supabase.table("goals").update(update_data).eq("id", goal_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Goal not found or unauthorized")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user_id: str = Query(..., description="User ID")):
    """Delete a goal."""
    try:
        if not supabase:
             raise HTTPException(status_code=503, detail="Database unavailable")

        response = supabase.table("goals").delete().eq("id", goal_id).eq("user_id", user_id).execute()
        
        if not response.data:
             raise HTTPException(status_code=404, detail="Goal not found or unauthorized")
             
        return {"message": "Goal deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
