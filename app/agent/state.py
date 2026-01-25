from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State schema for the Goally agent."""
    messages: Annotated[list, add_messages]
    user_goal: str
