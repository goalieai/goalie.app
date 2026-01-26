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
    planning_response_node,
    legacy_coach_node,
)
from app.agent.memory import session_store


# ============================================================
# PLANNING PIPELINE GRAPH (unchanged)
# ============================================================
# Linear flow: SMART Refiner -> Task Splitter -> Context Matcher

planning_workflow = StateGraph(AgentState)

planning_workflow.add_node("smart_refiner", smart_refiner_node)
planning_workflow.add_node("task_splitter", task_splitter_node)
planning_workflow.add_node("context_matcher", context_matcher_node)

planning_workflow.set_entry_point("smart_refiner")
planning_workflow.add_edge("smart_refiner", "task_splitter")
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
    return result


# ============================================================
# ORCHESTRATOR GRAPH
# ============================================================


def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate node based on classified intent."""
    intent = state.get("intent")
    if intent is None:
        return "casual"

    intent_type = intent.intent
    if intent_type == "planning":
        return "planning_pipeline"
    elif intent_type == "coaching":
        return "coaching"
    elif intent_type == "modify":
        # For now, route modify to coaching (future: dedicated modify flow)
        return "coaching"
    else:
        return "casual"


async def planning_subgraph(state: AgentState) -> dict:
    """Run the planning pipeline as a subgraph."""
    result = await planning_graph.ainvoke(state)
    return {
        "smart_goal": result.get("smart_goal"),
        "raw_tasks": result.get("raw_tasks"),
        "final_plan": result.get("final_plan"),
    }


# Build the orchestrator workflow
orchestrator_workflow = StateGraph(AgentState)

# Add nodes
orchestrator_workflow.add_node("intent_router", intent_router_node)
orchestrator_workflow.add_node("casual", casual_node)
orchestrator_workflow.add_node("coaching", coaching_node)
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
        "planning_pipeline": "planning_pipeline",
    },
)

# Terminal edges
orchestrator_workflow.add_edge("casual", END)
orchestrator_workflow.add_edge("coaching", END)
orchestrator_workflow.add_edge("planning_pipeline", "planning_response")
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
    # Get or create session
    session = session_store.get_or_create(session_id, user_id, user_profile)

    # Add user message to history (and persist to Supabase if user_id present)
    session_store.add_message(session, "user", message)

    # Build initial state with session context
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_input": message,
        "user_profile": session.user_profile,
        "session_id": session_id,
        "user_id": user_id,  # Pass user_id for fetching global context from DB
        "active_plans": session.active_plans,
        "completed_tasks": session.completed_tasks,
        "intent": None,
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

    # If a plan was created, add it to session
    if result.get("final_plan"):
        session.add_plan(result["final_plan"])

    # Final save for profile updates or plan changes
    session_store.save(session)

    # Build response
    response = {
        "session_id": session_id,
        "intent_detected": result["intent"].intent if result.get("intent") else "unknown",
        "response": result.get("response", "I'm here to help you achieve your goals!"),
        "plan": result.get("final_plan"),
        "progress": session.get_progress() if session.active_plans else None,
        "actions": result.get("actions", []),
    }

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
