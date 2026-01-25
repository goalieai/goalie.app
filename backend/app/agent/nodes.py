from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from app.core.config import settings
from app.agent.state import AgentState
from app.agent.schema import SmartGoalSchema, TaskList, ProjectPlan, IntentClassification
from app.agent.prompts import build_system_prompt, load_prompt


# =============================================================================
# LLM Instances (configured via settings)
# =============================================================================

llm_primary = ChatGoogleGenerativeAI(
    model=settings.llm_primary_model,
    google_api_key=settings.google_api_key,
    temperature=settings.llm_primary_temperature,
    max_retries=settings.llm_primary_max_retries,
    convert_system_message_to_human=True,
)

llm_fallback = ChatGoogleGenerativeAI(
    model=settings.llm_fallback_model,
    google_api_key=settings.google_api_key,
    temperature=settings.llm_fallback_temperature,
    max_retries=settings.llm_fallback_max_retries,
    convert_system_message_to_human=True,
)

llm_conversational_primary = ChatGoogleGenerativeAI(
    model=settings.llm_primary_model,
    google_api_key=settings.google_api_key,
    temperature=settings.llm_conversational_temperature,
    max_retries=settings.llm_primary_max_retries,
    convert_system_message_to_human=True,
)

llm_conversational_fallback = ChatGoogleGenerativeAI(
    model=settings.llm_fallback_model,
    google_api_key=settings.google_api_key,
    temperature=settings.llm_conversational_temperature,
    max_retries=settings.llm_fallback_max_retries,
    convert_system_message_to_human=True,
)


async def invoke_with_fallback(llm_primary, llm_fallback, messages, structured_output=None):
    """
    Try primary model, fall back to secondary on rate limit errors.

    Args:
        llm_primary: Primary LLM instance
        llm_fallback: Fallback LLM instance
        messages: Messages to send
        structured_output: Optional Pydantic model for structured output

    Returns:
        LLM response
    """
    primary = llm_primary.with_structured_output(structured_output) if structured_output else llm_primary
    fallback = llm_fallback.with_structured_output(structured_output) if structured_output else llm_fallback

    try:
        return await primary.ainvoke(messages)
    except ChatGoogleGenerativeAIError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"Rate limit on {settings.llm_primary_model}, falling back to {settings.llm_fallback_model}")
            return await fallback.ainvoke(messages)
        raise


# ============================================================
# ORCHESTRATOR NODES
# ============================================================


async def intent_router_node(state: AgentState) -> dict:
    """Classify user intent to route to the appropriate agent."""
    user_message = state["user_input"]

    # Build context from session if available
    context_parts = []
    if state.get("active_plans"):
        context_parts.append(
            f"User has {len(state['active_plans'])} active plan(s)."
        )
    if state.get("completed_tasks"):
        context_parts.append(
            f"User has completed {len(state['completed_tasks'])} task(s)."
        )

    context = "\n".join(context_parts) if context_parts else "No existing plans."

    system_prompt = load_prompt("orchestrator")
    user_prompt = f"""Session context: {context}

User message: "{user_message}"

Classify the intent."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=IntentClassification
    )

    return {"intent": result}


async def casual_node(state: AgentState) -> dict:
    """Handle casual conversation, greetings, and general questions."""
    user_message = state["user_input"]
    user_name = state["user_profile"].name

    system_prompt = build_system_prompt("system_base", "casual")

    # Add user context
    user_context = f"User's name: {user_name}"
    full_system = f"{system_prompt}\n\n## Current User\n{user_context}"

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    return {"response": response.content}


async def coaching_node(state: AgentState) -> dict:
    """Handle progress reviews, motivation, and setback discussions."""
    user_message = state["user_input"]
    user_name = state["user_profile"].name
    active_plans = state.get("active_plans", [])
    completed_tasks = state.get("completed_tasks", [])

    system_prompt = build_system_prompt("system_base", "coaching")

    # Build progress context
    progress_parts = [f"User's name: {user_name}"]

    if active_plans:
        for plan in active_plans:
            total = len(plan.tasks)
            done = sum(1 for t in plan.tasks if t.task_name in completed_tasks)
            progress_parts.append(
                f"\nPlan: {plan.project_name}"
                f"\n- Progress: {done}/{total} tasks ({round(done/total*100) if total else 0}%)"
                f"\n- Deadline: {plan.deadline}"
                f"\n- Tasks: {', '.join(t.task_name for t in plan.tasks)}"
                f"\n- Completed: {', '.join(completed_tasks) if completed_tasks else 'None yet'}"
            )
    else:
        progress_parts.append("\nNo active plans yet.")

    full_system = f"{system_prompt}\n\n## User Context\n{''.join(progress_parts)}"

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    return {"response": response.content}


async def planning_response_node(state: AgentState) -> dict:
    """Generate a friendly response presenting the created plan."""
    final_plan = state["final_plan"]
    user_name = state["user_profile"].name

    system_prompt = build_system_prompt("system_base", "planning")

    # Format the plan for presentation
    tasks_formatted = []
    anchor_emojis = {
        "morning": "sunrise",
        "mañana": "sunrise",
        "coffee": "sunrise",
        "lunch": "sunny",
        "mediodía": "sunny",
        "afternoon": "sunny",
        "evening": "crescent_moon",
        "night": "crescent_moon",
        "noche": "crescent_moon",
        "end of day": "crescent_moon",
    }

    for task in final_plan.tasks:
        anchor_lower = task.assigned_anchor.lower()
        emoji = "sunny"
        for key, value in anchor_emojis.items():
            if key in anchor_lower:
                emoji = value
                break
        tasks_formatted.append(
            f"- {task.assigned_anchor} ({task.estimated_minutes} min): {task.task_name}"
        )

    plan_summary = f"""Plan created:
- Project: {final_plan.project_name}
- Goal: {final_plan.smart_goal_summary}
- Deadline: {final_plan.deadline}

Tasks:
{chr(10).join(tasks_formatted)}"""

    user_prompt = f"""The user "{user_name}" asked to create a plan and the pipeline generated this:

{plan_summary}

Present this plan to the user in a friendly, encouraging way. Use their language (Spanish if they wrote in Spanish)."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    return {"response": response.content}


# ============================================================
# PLANNING PIPELINE NODES
# ============================================================


# --- Node 1: The Project Manager ---
async def smart_refiner_node(state: AgentState) -> dict:
    """Refines vague input into a strict SMART goal."""
    goal_text = state["user_input"]

    system_prompt = """You are a pragmatic Project Manager.
    Analyze the user's goal. If it is vague, make reasonable assumptions to make it S.M.A.R.T.
    You MUST output a concrete deadline (e.g. 'End of this week', 'Next Friday') if none is provided.
    Be concise and action-oriented."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=goal_text)]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=SmartGoalSchema
    )

    return {"smart_goal": result}


# --- Node 2: The Architect ---
async def task_splitter_node(state: AgentState) -> dict:
    """Breaks the SMART goal into atomic micro-tasks."""
    smart_goal = state["smart_goal"]

    system_prompt = """You are a Task Architect. Break projects into atomic, actionable steps.

    RULES:
    1. Create 3 to 7 tasks.
    2. Each task must be doable in one sitting (max 20 mins).
    3. Start each task with a verb (e.g., 'Draft', 'Email', 'Fix', 'Design').
    4. Order tasks logically (dependencies first)."""

    user_prompt = f"""Break this project into atomic steps:

    Project: {smart_goal.summary}
    Specific outcome: {smart_goal.specific_outcome}
    Deadline: {smart_goal.deadline}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=TaskList
    )

    return {"raw_tasks": result.tasks}


# --- Node 3: The Tiny Habits Coach ---
async def context_matcher_node(state: AgentState) -> dict:
    """Matches tasks to user anchors based on energy levels."""
    tasks = state["raw_tasks"]
    smart_goal = state["smart_goal"]
    user = state["user_profile"]

    tasks_formatted = "\n".join(f"- {task}" for task in tasks)
    anchors_formatted = ", ".join(user.anchors)

    system_prompt = """You are a Behavioral Scientist using the Tiny Habits method.

    INSTRUCTIONS:
    1. Assess each task's cognitive load (high/medium/low).
    2. Assign each task to the BEST available User Anchor:
       - High Focus tasks -> Morning anchors (fresh energy)
       - Medium Focus tasks -> Mid-day anchors
       - Low Focus/Admin tasks -> End of day anchors
    3. Estimate realistic time (5-20 minutes each).
    4. Provide a brief rationale for each assignment."""

    user_prompt = f"""Schedule these tasks for the user:

    PROJECT: {smart_goal.summary}
    DEADLINE: {smart_goal.deadline}

    USER PROFILE:
    - Role: {user.role}
    - Available Anchors: {anchors_formatted}

    TASKS TO SCHEDULE:
{tasks_formatted}

    Output project_name as "{smart_goal.summary}" and deadline as "{smart_goal.deadline}"."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=ProjectPlan
    )

    return {"final_plan": result}


# ============================================================
# LEGACY NODE (for backwards compatibility with /api/chat old behavior)
# ============================================================


async def legacy_coach_node(state: AgentState) -> dict:
    """Main coaching node that responds to user messages (legacy)."""
    system_prompt = build_system_prompt("system_base")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    return {"messages": [response]}
