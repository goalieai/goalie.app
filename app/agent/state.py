from typing import TypedDict, Annotated, List, Optional, Literal, Dict, Any
from langgraph.graph.message import add_messages

from app.agent.schema import UserProfile, SmartGoalSchema, ProjectPlan, IntentClassification


class AgentState(TypedDict):
    """State schema for the Goally agent pipeline."""

    # Conversation History (Standard LangGraph)
    messages: Annotated[list, add_messages]

    # Input Data
    user_input: str
    user_profile: UserProfile

    # Session context (from memory)
    session_id: Optional[str]
    user_id: Optional[str]  # For fetching user data from Supabase
    active_plans: Optional[List[ProjectPlan]]
    completed_tasks: Optional[List[str]]

    # Orchestrator output
    intent: Optional[IntentClassification]

    # SOCRATIC GATEKEEPER STATE
    # Stores the draft goal and what's missing (e.g. {"draft_goal": "Run marathon", "missing_info": "fitness_level"})
    pending_context: Optional[Dict[str, Any]]
    # Safety counter to prevent infinite clarification loops
    clarification_attempts: int
    # Context tags from Refiner for Task Splitter (e.g. ["beginner", "sedentary"])
    goal_context_tags: Optional[List[str]]

    # Pipeline Artifacts (The "Memory" of the chain)
    smart_goal: Optional[SmartGoalSchema]
    raw_tasks: Optional[List[str]]
    final_plan: Optional[ProjectPlan]

    # HUMAN-IN-THE-LOOP (HITL) STAGING
    # Holds the unconfirmed plan awaiting user approval
    # Only moves to active_plans after explicit "confirm" intent
    staging_plan: Optional[ProjectPlan]

    # Final response
    response: Optional[str]
    actions: Optional[List[dict]]
