from pathlib import Path
from typing import Optional, Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Load description from .md file
def load_tool_description(name: str) -> str:
    desc_path = Path(__file__).parent / "descriptions" / f"{name}.md"
    if desc_path.exists():
        return desc_path.read_text()
    return f"Tool: {name}"

class CreateTaskInput(BaseModel):
    """Input schema for create_task tool."""
    action: str = Field(description="Task description (verb + object)")
    time: Optional[str] = Field(default=None, description="Scheduled time or deadline")
    energy: Optional[Literal["high", "medium", "low"]] = Field(
        default="medium", description="Energy level required for the task"
    )

@tool("create_task", args_schema=CreateTaskInput)
def create_task(action: str, time: Optional[str] = None, energy: str = "medium") -> dict:
    """Create a new task for the user in their task list."""
    return {
        "type": "create_task",
        "data": {"action": action, "time": time, "energy": energy}
    }

class CreateGoalInput(BaseModel):
    """Input schema for create_goal tool."""
    title: str = Field(description="Goal title/description")
    description: Optional[str] = Field(default=None, description="Optional detailed description")
    emoji: str = Field(default="🎯", description="Emoji representing the goal")

@tool("create_goal", args_schema=CreateGoalInput)
def create_goal(title: str, description: Optional[str] = None, emoji: str = "🎯") -> dict:
    """Create a new goal or objective for the user."""
    return {
        "type": "create_goal",
        "data": {"title": title, "description": description, "emoji": emoji}
    }

class CompleteTaskInput(BaseModel):
    """Input schema for complete_task tool."""
    task_id: Optional[str] = Field(default=None, description="ID of the task to complete")
    task_name: Optional[str] = Field(default=None, description="Name of the task to complete if ID is unknown")

@tool("complete_task", args_schema=CompleteTaskInput)
def complete_task(task_id: Optional[str] = None, task_name: Optional[str] = None) -> dict:
    """Mark a task as completed."""
    return {
        "type": "complete_task",
        "data": {"task_id": task_id, "task_name": task_name}
    }

# List of all available tools
ALL_TOOLS = [create_task, create_goal, complete_task]
