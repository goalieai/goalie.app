"""
Verification script to test Gemini structured output compatibility.
Run from backend directory: python verify_structured_output.py
"""

import asyncio
from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings


# Test schema (simplified version of what we'll use)
class SmartGoalSchema(BaseModel):
    summary: str = Field(description="The refined, concise goal statement")
    deadline: str = Field(description="Target date or timeframe")
    metrics: List[str] = Field(description="How success will be measured")


class TaskList(BaseModel):
    tasks: List[str] = Field(description="A list of 3-5 atomic task names")


class MicroTask(BaseModel):
    task_name: str = Field(description="Actionable task name")
    estimated_minutes: int = Field(description="Time needed, under 15 mins")
    energy_required: str = Field(description="high, medium, or low")
    assigned_anchor: Optional[str] = Field(description="User habit this attaches to")
    rationale: str = Field(description="Why this anchor was chosen")


class ProjectPlan(BaseModel):
    project_name: str
    smart_goal_summary: str
    deadline: str
    tasks: List[MicroTask]


async def test_structured_output():
    print("=" * 60)
    print("Gemini Structured Output Verification")
    print("=" * 60)

    # Check API key
    if not settings.google_api_key:
        print("\n[FAIL] GOOGLE_API_KEY not set in .env")
        return False
    print(f"\n[OK] API key found (ends with ...{settings.google_api_key[-4:]})")

    # Initialize LLM with settings recommended for structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.google_api_key,
        temperature=0,
        max_retries=2,
        convert_system_message_to_human=True,
    )
    print("[OK] LLM initialized")

    # Test 1: SmartGoalSchema
    print("\n--- Test 1: SmartGoalSchema ---")
    try:
        structured_llm = llm.with_structured_output(SmartGoalSchema)
        result = await structured_llm.ainvoke([
            HumanMessage(content="I want to learn Spanish this year")
        ])
        print(f"[OK] SmartGoalSchema works!")
        print(f"     Summary: {result.summary}")
        print(f"     Deadline: {result.deadline}")
        print(f"     Metrics: {result.metrics}")
    except Exception as e:
        print(f"[FAIL] SmartGoalSchema failed: {e}")
        return False

    # Test 2: TaskList
    print("\n--- Test 2: TaskList ---")
    try:
        structured_llm = llm.with_structured_output(TaskList)
        result = await structured_llm.ainvoke([
            HumanMessage(content="Break down 'Launch a portfolio website' into 3-5 small tasks")
        ])
        print(f"[OK] TaskList works!")
        print(f"     Tasks: {result.tasks}")
    except Exception as e:
        print(f"[FAIL] TaskList failed: {e}")
        return False

    # Test 3: ProjectPlan (complex nested schema)
    print("\n--- Test 3: ProjectPlan (nested) ---")
    try:
        structured_llm = llm.with_structured_output(ProjectPlan)
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are a productivity coach. Create a plan with 2-3 micro-tasks."),
            HumanMessage(content="Goal: Build a portfolio website by next Friday. User anchors: Morning Coffee, After Lunch")
        ])
        print(f"[OK] ProjectPlan works!")
        print(f"     Project: {result.project_name}")
        print(f"     Deadline: {result.deadline}")
        print(f"     Tasks:")
        for task in result.tasks:
            print(f"       - {task.task_name} ({task.estimated_minutes}min, {task.energy_required} energy)")
            print(f"         Anchor: {task.assigned_anchor}")
    except Exception as e:
        print(f"[FAIL] ProjectPlan failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED - Structured output is working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_structured_output())
    exit(0 if success else 1)
