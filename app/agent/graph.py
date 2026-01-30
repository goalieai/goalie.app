from typing import Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.agent.state import AgentState
from app.agent.schema import UserProfile
from app.agent.nodes import (
    smart_refiner_node,
    task_splitter_node,
    context_matcher_node,
    intent_router_node,
    casual_node,
    coaching_node,
    confirmation_node,
    planning_response_node,
    legacy_coach_node,
)
from app.agent.memory import session_store


# ============================================================
# PLANNING PIPELINE GRAPH (with Socratic Gatekeeper)
# ============================================================
# Conditional flow: SMART Refiner -> (needs_clarification? END : Task Splitter -> Context Matcher)


def route_after_refiner(state: AgentState) -> str:
    """Route based on whether the refiner needs more context or is ready to plan.

    SOCRATIC GATEKEEPER: If pending_context is set, the refiner asked a clarifying
    question and we should return to the user. Otherwise, proceed to task splitting.
    """
    if state.get("pending_context"):
        print("[AGENT] route_after_refiner | SOCRATIC: pending_context exists -> END (waiting for user)")
        return END
    print("[AGENT] route_after_refiner | Goal is ready -> task_splitter")
    return "task_splitter"


planning_workflow = StateGraph(AgentState)

planning_workflow.add_node("smart_refiner", smart_refiner_node)
planning_workflow.add_node("task_splitter", task_splitter_node)
planning_workflow.add_node("context_matcher", context_matcher_node)

planning_workflow.set_entry_point("smart_refiner")

# SOCRATIC GATEKEEPER: Conditional edge after refiner
planning_workflow.add_conditional_edges(
    "smart_refiner",
    route_after_refiner,
    {
        END: END,
        "task_splitter": "task_splitter",
    },
)

planning_workflow.add_edge("task_splitter", "context_matcher")
planning_workflow.add_edge("context_matcher", END)

planning_graph = planning_workflow.compile()


async def run_planning_pipeline(
    goal: str,
    user_profile: UserProfile | None = None,
) -> dict:
    """
    Run the full planning pipeline for a user goal.

    Args:
        goal: The user's raw goal input (e.g., "Launch my portfolio website")
        user_profile: Optional user profile with anchors. Uses defaults if not provided.

    Returns:
        dict with 'final_plan' containing the ProjectPlan
    """
    print(f"[AGENT] run_planning_pipeline START | goal='{goal[:50]}...' | user_profile={user_profile}")

    if user_profile is None:
        user_profile = UserProfile()

    initial_state = {
        "messages": [],
        "user_input": goal,
        "user_profile": user_profile,
        "session_id": None,
        "active_plans": None,
        "completed_tasks": None,
        "intent": None,
        "smart_goal": None,
        "raw_tasks": None,
        "final_plan": None,
        "response": None,
    }

    result = await planning_graph.ainvoke(initial_state)
    print(f"[AGENT] run_planning_pipeline END | final_plan={result.get('final_plan')}")
    return result


# ============================================================
# ORCHESTRATOR GRAPH
# ============================================================


def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate node based on classified intent."""
    intent = state.get("intent")
    if intent is None:
        print("[AGENT] route_by_intent | intent=None -> routing to 'casual'")
        return "casual"

    intent_type = intent.intent
    print(f"[AGENT] route_by_intent | intent={intent_type} | confidence={getattr(intent, 'confidence', 'N/A')}")

    if intent_type == "planning":
        return "planning_pipeline"
    elif intent_type == "planning_continuation":
        # SOCRATIC GATEKEEPER: User is responding to a clarifying question
        return "planning_pipeline"
    elif intent_type == "coaching":
        return "coaching"
    elif intent_type == "modify":
        # For now, route modify to coaching (future: dedicated modify flow)
        return "coaching"
    elif intent_type == "confirm":
        return "confirmation"
    else:
        return "casual"


async def planning_subgraph(state: AgentState) -> dict:
    """Run the planning pipeline as a subgraph.

    SOCRATIC GATEKEEPER: This subgraph may return early if the refiner
    needs clarification. In that case, pending_context will be set and
    final_plan will be None.
    """
    print("[AGENT] planning_subgraph START")
    result = await planning_graph.ainvoke(state)

    # Check if we got a clarification request (Socratic Gatekeeper)
    if result.get("pending_context"):
        print(f"[AGENT] planning_subgraph END | SOCRATIC: needs clarification")
        return {
            "response": result.get("response"),
            "pending_context": result.get("pending_context"),
            "clarification_attempts": result.get("clarification_attempts", 0),
            "smart_goal": None,
            "raw_tasks": None,
            "final_plan": None,
        }

    print(f"[AGENT] planning_subgraph END | tasks_count={len(result.get('final_plan').tasks) if result.get('final_plan') else 0}")
    return {
        "smart_goal": result.get("smart_goal"),
        "raw_tasks": result.get("raw_tasks"),
        "final_plan": result.get("final_plan"),
        "pending_context": None,  # Clear any previous pending context
        "clarification_attempts": 0,
    }


# Build the orchestrator workflow
orchestrator_workflow = StateGraph(AgentState)

# Add nodes
orchestrator_workflow.add_node("intent_router", intent_router_node)
orchestrator_workflow.add_node("casual", casual_node)
orchestrator_workflow.add_node("coaching", coaching_node)
orchestrator_workflow.add_node("confirmation", confirmation_node)
orchestrator_workflow.add_node("planning_pipeline", planning_subgraph)
orchestrator_workflow.add_node("planning_response", planning_response_node)

# Set entry point
orchestrator_workflow.set_entry_point("intent_router")

# Add conditional routing from intent_router
orchestrator_workflow.add_conditional_edges(
    "intent_router",
    route_by_intent,
    {
        "casual": "casual",
        "coaching": "coaching",
        "confirmation": "confirmation",
        "planning_pipeline": "planning_pipeline",
    },
)

def route_after_planning_pipeline(state: AgentState) -> str:
    """Route after planning pipeline based on whether we need clarification.

    SOCRATIC GATEKEEPER: If pending_context exists, we asked a clarifying question
    and should end. Otherwise, proceed to planning_response to present the plan.
    """
    if state.get("pending_context"):
        print("[AGENT] route_after_planning_pipeline | SOCRATIC: clarification needed -> END")
        return END
    print("[AGENT] route_after_planning_pipeline | Plan ready -> planning_response")
    return "planning_response"


# Terminal edges
orchestrator_workflow.add_edge("casual", END)
orchestrator_workflow.add_edge("coaching", END)
orchestrator_workflow.add_edge("confirmation", END)

# SOCRATIC GATEKEEPER: Conditional edge after planning_pipeline
orchestrator_workflow.add_conditional_edges(
    "planning_pipeline",
    route_after_planning_pipeline,
    {
        END: END,
        "planning_response": "planning_response",
    },
)

orchestrator_workflow.add_edge("planning_response", END)

orchestrator_graph = orchestrator_workflow.compile()


async def run_orchestrator(
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
    user_profile: UserProfile | None = None,
) -> dict:
    """
    Run the orchestrator with session memory.

    Args:
        message: The user's message
        session_id: Unique session identifier
        user_id: Optional user identifier for persistent storage
        user_profile: Optional user profile (used to update session)

    Returns:
        dict with 'response', 'intent_detected', and optionally 'plan'
    """
    print(f"[AGENT] run_orchestrator START | session_id={session_id} | user_id={user_id}")
    print(f"[AGENT] run_orchestrator | message='{message[:100]}...' " if len(message) > 100 else f"[AGENT] run_orchestrator | message='{message}'")

    # Get or create session
    session = session_store.get_or_create(session_id, user_id, user_profile)
    print(f"[AGENT] run_orchestrator | session loaded | active_plans={len(session.active_plans)} | history_len={len(session.message_history)}")

    # Add user message to history (and persist to Supabase if user_id present)
    session_store.add_message(session, "user", message)

    # Build initial state with session context
    # SOCRATIC GATEKEEPER: Include pending_context from session if it exists
    # HITL: Include staging_plan from session if user hasn't confirmed yet
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_input": message,
        "user_profile": session.user_profile,
        "session_id": session_id,
        "user_id": user_id,  # Pass user_id for fetching global context from DB
        "active_plans": session.active_plans,
        "completed_tasks": session.completed_tasks,
        "intent": None,
        # Socratic Gatekeeper state
        "pending_context": getattr(session, "pending_context", None),
        "clarification_attempts": getattr(session, "clarification_attempts", 0),
        "goal_context_tags": None,
        # HITL state
        "staging_plan": getattr(session, "staging_plan", None),
        "smart_goal": None,
        "raw_tasks": None,
        "final_plan": None,
        "response": None,
        "actions": [],
    }

    # Run the orchestrator
    result = await orchestrator_graph.ainvoke(initial_state)

    # Save assistant response to history
    if result.get("response"):
        session_store.add_message(session, "assistant", result["response"])

    # SOCRATIC GATEKEEPER: Save pending context to session for next turn
    if result.get("pending_context"):
        session.pending_context = result["pending_context"]
        session.clarification_attempts = result.get("clarification_attempts", 0)
        print(f"[AGENT] run_orchestrator | SOCRATIC: Saved pending_context to session")
    else:
        # Clear pending context if goal was successfully processed
        session.pending_context = None
        session.clarification_attempts = 0

    # HUMAN-IN-THE-LOOP (HITL): Handle plan staging and confirmation
    # Plans are now staged first, then only committed on explicit confirmation

    # If confirmation_node promoted a staged plan to active_plans
    if result.get("active_plans"):
        for plan in result["active_plans"]:
            # Check if not already in session (avoid duplicates)
            existing_titles = [p.project_name for p in session.active_plans]
            if plan.project_name not in existing_titles:
                session.add_plan(plan)
                print(f"[AGENT] run_orchestrator | HITL COMMIT: Plan '{plan.project_name}' added to active_plans")

    # If planning_response_node staged a new plan
    if result.get("staging_plan"):
        session.staging_plan = result["staging_plan"]
        print(f"[AGENT] run_orchestrator | HITL STAGED: Plan '{result['staging_plan'].project_name}' awaiting confirmation")
    elif result.get("staging_plan") is None and hasattr(session, "staging_plan"):
        # Clear staging if explicitly set to None (after confirmation)
        if session.staging_plan is not None:
            print(f"[AGENT] run_orchestrator | HITL: Cleared staging_plan after confirmation")
            session.staging_plan = None

    # Final save for profile updates or plan changes
    session_store.save(session)

    # Build response
    # Include staging_plan info for frontend to show preview vs committed state
    staging_plan_data = None
    if result.get("staging_plan"):
        staging_plan_data = result["staging_plan"].model_dump() if hasattr(result["staging_plan"], 'model_dump') else result["staging_plan"]

    response = {
        "session_id": session_id,
        "intent_detected": result["intent"].intent if result.get("intent") else "unknown",
        "response": result.get("response", "I'm here to help you achieve your goals!"),
        "plan": result.get("final_plan"),
        "progress": session.get_progress() if session.active_plans else None,
        "actions": result.get("actions", []),
        # HITL: Include staging info for frontend
        "staging_plan": staging_plan_data,
        "awaiting_confirmation": staging_plan_data is not None,
    }

    print(f"[AGENT] run_orchestrator END | intent={response['intent_detected']} | staged={response['awaiting_confirmation']} | actions={len(response['actions'])}")
    return response


# ============================================================
# LEGACY CHAT GRAPH (for backwards compatibility)
# ============================================================

chat_workflow = StateGraph(AgentState)
chat_workflow.add_node("coach", legacy_coach_node)
chat_workflow.set_entry_point("coach")
chat_workflow.add_edge("coach", END)

chat_graph = chat_workflow.compile()


async def run_agent(message: str) -> str:
    """Run the chat agent with a user message (legacy endpoint)."""
    print(f"[AGENT] run_agent (legacy) START | message='{message[:50]}...'")
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_input": message,
        "user_profile": UserProfile(),
        "session_id": None,
        "active_plans": None,
        "completed_tasks": None,
        "intent": None,
        "smart_goal": None,
        "raw_tasks": None,
        "final_plan": None,
        "response": None,
    }

    result = await chat_graph.ainvoke(initial_state)

    ai_messages = [m for m in result["messages"] if m.type == "ai"]
    if ai_messages:
        return ai_messages[-1].content
    return "I'm here to help you achieve your goals!"
