from typing import TypedDict, Annotated, List, Optional, Literal
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
    active_plans: Optional[List[ProjectPlan]]
    completed_tasks: Optional[List[str]]

    # Orchestrator output
    intent: Optional[IntentClassification]

    # Pipeline Artifacts (The "Memory" of the chain)
    smart_goal: Optional[SmartGoalSchema]
    raw_tasks: Optional[List[str]]
    final_plan: Optional[ProjectPlan]

    # Final response
    response: Optional[str]
