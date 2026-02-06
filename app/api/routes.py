from typing import List, Optional, Literal
from uuid import uuid4
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import traceback
from datetime import datetime
from langchain_core.messages import HumanMessage

from app.agent.graph import run_agent, run_planning_pipeline, run_orchestrator, orchestrator_graph
from app.agent.schema import UserProfile, MicroTask
from app.agent.memory import session_store
from app.core.supabase import supabase
from app.api import schemas

router = APIRouter()


def format_sse(event_type: str, payload) -> str:
    """Helper to format SSE string."""
    if isinstance(payload, str):
        data = {"type": event_type, "message": payload}
    else:
        data = {"type": event_type, "data": payload}
    return f"data: {json.dumps(data)}\n\n"


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

    type: Literal["create_task", "complete_task", "create_goal", "update_task", "refresh_ui"]
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
# STREAMING CHAT ENDPOINT (SSE)
# ============================================================

# Map node names to step IDs and user-facing messages
NODE_TO_STEP = {
    # Orchestrator nodes
    "intent_router": ("intent", "Understanding your intent..."),
    "casual": ("response", "Thinking..."),
    "coaching": ("response", "Reviewing your progress..."),
    "confirmation": ("response", "Confirming your plan..."),
    "planning_response": ("response", "Preparing your plan..."),
    # Planning subgraph nodes
    "smart_refiner": ("smart", "Analyzing goal context..."),
    "task_splitter": ("tasks", "Breaking into micro-tasks..."),
    "context_matcher": ("schedule", "Scheduling your tasks..."),
}


@router.post("/chat/stream")
async def chat_stream(request: UnifiedChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.

    Emits progress updates as the LangGraph executes each node,
    keeping the connection alive and providing real-time feedback.
    This prevents Heroku H12 timeout errors on long-running planning flows.
    """

    async def event_generator():
        try:
            # Generate session ID if not provided
            session_id = request.session_id or str(uuid4())

            # Parse user profile
            user_profile = None
            if request.user_profile:
                user_profile = UserProfile(
                    name=request.user_profile.get("name", "User"),
                    role=request.user_profile.get("role", "Professional"),
                    anchors=request.user_profile.get(
                        "anchors", ["Morning Coffee", "After Lunch", "End of Day"]
                    ),
                )

            # Get or create session
            session = session_store.get_or_create(session_id, request.user_id, user_profile)
            session_store.add_message(session, "user", request.message)

            # Build initial state (including Socratic Gatekeeper and HITL fields)
            initial_state = {
                "messages": [HumanMessage(content=request.message)],
                "user_input": request.message,
                "user_profile": session.user_profile,
                "session_id": session_id,
                "user_id": request.user_id,
                "active_plans": session.active_plans,
                "completed_tasks": session.completed_tasks,
                "intent": None,
                # Socratic Gatekeeper state (from session for multi-turn flow)
                "pending_context": getattr(session, "pending_context", None),
                "clarification_attempts": getattr(session, "clarification_attempts", 0),
                "goal_context_tags": None,
                # HITL state (from session for confirmation flow)
                "staging_plan": getattr(session, "staging_plan", None),
                "smart_goal": None,
                "raw_tasks": None,
                "final_plan": None,
                "response": None,
                "actions": [],
            }

            # Emit initial status
            yield format_sse("status", "Processing your request...")

            final_result = None

            # Stream events from LangGraph
            async for event in orchestrator_graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
                name = event.get("name", "")
                data = event.get("data", {})

                # --- Node started ---
                if kind == "on_chain_start" and name in NODE_TO_STEP:
                    step_id, message = NODE_TO_STEP[name]
                    yield format_sse("status", message)

                # --- Node completed with intermediate data ---
                elif kind == "on_chain_end" and name in NODE_TO_STEP:
                    step_id, _ = NODE_TO_STEP[name]
                    output = data.get("output", {})

                    # SOCRATIC GATEKEEPER: Detect clarification request from smart_refiner
                    if name == "smart_refiner" and output.get("pending_context"):
                        # Emit special "clarification" event for frontend to handle differently
                        clarification_data = {
                            "question": output.get("response", "Could you tell me more about your goal?"),
                            "context": output["pending_context"],
                            "attempts": output.get("clarification_attempts", 1)
                        }
                        yield format_sse("clarification", clarification_data)

                    # Send progress preview for planning steps (when goal is ready)
                    elif name == "smart_refiner" and output.get("smart_goal"):
                        smart_goal = output["smart_goal"]
                        yield format_sse("progress", {
                            "step": "smart_goal",
                            "data": {
                                "summary": smart_goal.summary if hasattr(smart_goal, 'summary') else str(smart_goal)
                            }
                        })
                    elif name == "task_splitter" and output.get("raw_tasks"):
                        raw_tasks = output["raw_tasks"]
                        yield format_sse("progress", {
                            "step": "raw_tasks",
                            "data": raw_tasks
                        })

                # --- Graph completed ---
                elif kind == "on_chain_end" and name == "LangGraph":
                    final_result = data.get("output", {})

            # Save to session and emit final response
            if final_result:
                if final_result.get("response"):
                    session_store.add_message(session, "assistant", final_result["response"])

                # SOCRATIC GATEKEEPER: Save pending context for next turn
                if final_result.get("pending_context"):
                    session.pending_context = final_result["pending_context"]
                    session.clarification_attempts = final_result.get("clarification_attempts", 0)
                else:
                    # Clear pending context if goal was successfully processed
                    session.pending_context = None
                    session.clarification_attempts = 0

                # HITL: Handle staging_plan and active_plans from confirmation
                if final_result.get("staging_plan"):
                    session.staging_plan = final_result["staging_plan"]
                elif final_result.get("staging_plan") is None and hasattr(session, "staging_plan"):
                    session.staging_plan = None  # Clear after confirmation

                # If confirmation_node promoted staging to active
                if final_result.get("active_plans"):
                    for plan in final_result["active_plans"]:
                        existing_titles = [p.project_name for p in session.active_plans]
                        if plan.project_name not in existing_titles:
                            session.add_plan(plan)

                session_store.save(session)

                # Build final response
                plan_data = None
                if final_result.get("final_plan"):
                    plan = final_result["final_plan"]
                    plan_data = plan.model_dump() if hasattr(plan, 'model_dump') else plan

                # HITL: Include staging_plan data
                staging_plan_data = None
                if final_result.get("staging_plan"):
                    staging = final_result["staging_plan"]
                    staging_plan_data = staging.model_dump() if hasattr(staging, 'model_dump') else staging

                # Determine if we're waiting for clarification or confirmation
                is_clarification = final_result.get("pending_context") is not None
                is_awaiting_confirmation = staging_plan_data is not None

                yield format_sse("complete", {
                    "session_id": session_id,
                    "intent_detected": final_result.get("intent").intent if final_result.get("intent") else "unknown",
                    "response": final_result.get("response", ""),
                    "plan": plan_data,
                    "progress": session.get_progress() if session.active_plans else None,
                    "actions": final_result.get("actions", []),
                    # SOCRATIC GATEKEEPER: Include clarification state
                    "awaiting_clarification": is_clarification,
                    "pending_context": final_result.get("pending_context") if is_clarification else None,
                    # HITL: Include staging state
                    "staging_plan": staging_plan_data,
                    "awaiting_confirmation": is_awaiting_confirmation
                })

        except Exception as e:
            print(f"Streaming error: {e}")
            traceback.print_exc()
            yield format_sse("error", f"Agent error: {str(e)}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Important for Nginx/Heroku
        }
    )


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
        
        # Fetch original task to check status change
        original = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).execute()
        if not original.data:
            raise HTTPException(status_code=404, detail="Task not found or unauthorized")
        
        original_task = original.data[0]
        
        # Update task
        response = supabase.table("tasks").update(update_data).eq("id", task_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Task not found or unauthorized")
        
        updated_task = response.data[0]
        
        # --- OPIK EXECUTION TRACKING ---
        from app.agent.execution_tracker import execution_tracker
        from datetime import datetime as dt
        
        # Check if status changed to completed
        if updated_task.get("status") == "completed" and original_task.get("status") != "completed":
            execution_tracker.log_task_completion(
                task_id=task_id,
                task_name=updated_task.get("task_name", "Unnamed Task"),
                user_id=user_id,
                goal_id=updated_task.get("goal_id"),
                scheduled_date=updated_task.get("scheduled_date"),
                completed_date=dt.now().isoformat(),
                was_rescheduled=updated_task.get("was_rescheduled", False)
            )
        
        # Check if status changed to skipped/missed
        elif updated_task.get("status") in ["skipped", "missed"] and original_task.get("status") not in ["skipped", "missed"]:
            execution_tracker.log_task_missed(
                task_id=task_id,
                task_name=updated_task.get("task_name", "Unnamed Task"),
                user_id=user_id,
                goal_id=updated_task.get("goal_id"),
                scheduled_date=updated_task.get("scheduled_date", "unknown"),
                missed_date=dt.now().isoformat()
            )
            
        return updated_task
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
