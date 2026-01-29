from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.core.config import settings


def extract_text_content(content) -> str:
    """Extract text from LLM response content.

    Handles both string content and list of content blocks (Gemini 3 format).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Extract text from content blocks
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "".join(texts)
    return str(content)
from app.agent.state import AgentState
from app.agent.schema import SmartGoalSchema, TaskList, ProjectPlan, IntentClassification
from app.agent.prompts import build_system_prompt, load_prompt
from app.agent.tools.crud import ALL_TOOLS
from app.core.supabase import supabase


# =============================================================================
# LLM Instances (configured via settings)
# =============================================================================

def create_llm(model_name: str, temperature: float, max_retries: int):
    """Factory to create the appropriate LLM instance."""
    if "gemini" in model_name.lower():
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
            max_retries=max_retries,
            convert_system_message_to_human=True,
        )
    elif "gpt" in model_name.lower() or "openai" in model_name.lower():
        return ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
            max_retries=max_retries,
        )
    elif "ollama:" in model_name.lower():
        # Format: "ollama:model_name" e.g. "ollama:llama3.2" or "ollama:mistral"
        ollama_model = model_name.split(":", 1)[1]
        return ChatOllama(
            model=ollama_model,
            temperature=temperature,
        )
    else:
        # Default fallback or error
        raise ValueError(f"Unsupported model provider for: {model_name}")


llm_primary = create_llm(
    settings.llm_primary_model,
    settings.llm_primary_temperature,
    settings.llm_primary_max_retries,
)

llm_fallback = create_llm(
    settings.llm_fallback_model,
    settings.llm_fallback_temperature,
    settings.llm_fallback_max_retries,
)

llm_conversational_primary = create_llm(
    settings.llm_primary_model,
    settings.llm_conversational_temperature,
    settings.llm_primary_max_retries,
).bind_tools(ALL_TOOLS)

llm_conversational_fallback = create_llm(
    settings.llm_fallback_model,
    settings.llm_conversational_temperature,
    settings.llm_fallback_max_retries,
).bind_tools(ALL_TOOLS)


async def invoke_with_fallback(llm_primary, llm_fallback, messages, structured_output=None):
    """
    Try primary model, fall back to secondary on rate limit or parsing errors.

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

    output_type = structured_output.__name__ if structured_output else "text"
    print(f"[AGENT] LLM call START | model={settings.llm_primary_model} | output_type={output_type}")

    try:
        result = await primary.ainvoke(messages)
        print(f"[AGENT] LLM call END | model={settings.llm_primary_model} | success=True")
        return result
    except Exception as e:
        error_str = str(e).upper()
        error_type = type(e).__name__
        print(f"[DEBUG] Primary LLM error: {e}")
        print(f"[DEBUG] Error type: {error_type}")

        # Fall back on rate limits, output parsing errors, or empty responses
        should_fallback = (
            any(x in error_str for x in ["429", "RESOURCE_EXHAUSTED", "RATE_LIMIT"]) or
            isinstance(e, OutputParserException) or
            "INVALID JSON" in error_str or
            "OUTPUTPARSERERROR" in error_str
        )

        if should_fallback:
            print(f"[DEBUG] Falling back from {settings.llm_primary_model} to {settings.llm_fallback_model}")
            return await fallback.ainvoke(messages)
        raise


# ============================================================
# USER CONTEXT FROM DATABASE
# ============================================================


async def get_user_context(user_id: str) -> dict:
    """
    Fetch user's tasks and goals from Supabase.

    This gives the agent awareness of ALL user data, not just session-created plans.
    """
    if not supabase or not user_id:
        return {"active_tasks": [], "completed_tasks": [], "goals": []}

    try:
        # Fetch tasks
        tasks_res = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
        tasks = tasks_res.data or []

        # Fetch goals
        goals_res = supabase.table("goals").select("*").eq("user_id", user_id).execute()
        goals = goals_res.data or []

        # Separate active vs completed tasks
        active_tasks = [t for t in tasks if t.get("status") != "completed"]
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]

        return {
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "goals": goals,
        }
    except Exception as e:
        print(f"[DEBUG] Error fetching user context: {e}")
        return {"active_tasks": [], "completed_tasks": [], "goals": []}


def format_user_context_for_prompt(context: dict) -> str:
    """Format user context as a string for injection into system prompts."""
    parts = []

    # Active tasks
    active = context.get("active_tasks", [])
    if active:
        task_lines = []
        for t in active[:10]:  # Limit to 10 to avoid prompt bloat
            name = t.get("task_name", "Unnamed task")
            scheduled = t.get("scheduled_text", "")
            energy = t.get("energy_required", "")
            task_lines.append(f"  - {name}" + (f" ({scheduled})" if scheduled else "") + (f" [{energy} energy]" if energy else ""))
        parts.append(f"Active tasks ({len(active)}):\n" + "\n".join(task_lines))
    else:
        parts.append("Active tasks: None")

    # Completed tasks
    completed = context.get("completed_tasks", [])
    if completed:
        recent = completed[:5]  # Show last 5 completed
        task_names = [t.get("task_name", "Unnamed") for t in recent]
        parts.append(f"Recently completed ({len(completed)} total): {', '.join(task_names)}")

    # Goals
    goals = context.get("goals", [])
    if goals:
        goal_lines = []
        for g in goals[:5]:  # Limit to 5
            title = g.get("title", "Unnamed goal")
            emoji = g.get("emoji", "🎯")
            status = g.get("status", "active")
            goal_lines.append(f"  - {emoji} {title} ({status})")
        parts.append(f"Goals ({len(goals)}):\n" + "\n".join(goal_lines))
    else:
        parts.append("Goals: None set yet")

    return "\n\n".join(parts)


# ============================================================
# ORCHESTRATOR NODES
# ============================================================


async def intent_router_node(state: AgentState) -> dict:
    """Classify user intent to route to the appropriate agent."""
    print(f"[AGENT] intent_router_node START")
    user_message = state["user_input"]
    user_id = state.get("user_id")

    # Build context from database + session
    context_parts = []

    # Fetch real data from database
    if user_id:
        db_context = await get_user_context(user_id)
        active_tasks = db_context.get("active_tasks", [])
        completed_tasks = db_context.get("completed_tasks", [])
        goals = db_context.get("goals", [])

        if active_tasks:
            context_parts.append(f"User has {len(active_tasks)} active task(s) in database.")
        if completed_tasks:
            context_parts.append(f"User has completed {len(completed_tasks)} task(s).")
        if goals:
            context_parts.append(f"User has {len(goals)} goal(s) set.")

    # Also include session-specific plans
    if state.get("active_plans"):
        context_parts.append(
            f"User has {len(state['active_plans'])} active session plan(s)."
        )

    context = "\n".join(context_parts) if context_parts else "No existing tasks or plans."

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

    print(f"[AGENT] intent_router_node END | intent={result.intent} | confidence={result.confidence} | reasoning={result.reasoning[:50]}...")
    return {"intent": result}


async def casual_node(state: AgentState) -> dict:
    """Handle casual conversation, greetings, and general questions."""
    print(f"[AGENT] casual_node START")
    user_message = state["user_input"]
    user_name = state["user_profile"].name
    user_id = state.get("user_id")

    system_prompt = build_system_prompt("system_base", "casual")

    # Fetch global user context from database
    db_context = await get_user_context(user_id)
    context_str = format_user_context_for_prompt(db_context)

    # Build full system prompt with user context
    user_context = f"User's name: {user_name}\n\n{context_str}"
    full_system = f"{system_prompt}\n\n## Current User\n{user_context}"

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    # Extract tool calls (actions)
    actions = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        actions = [
            {"type": call["name"], "data": call["args"]}
            for call in response.tool_calls
        ]

    print(f"[AGENT] casual_node END | response_len={len(extract_text_content(response.content))} | actions={len(actions)}")
    return {"response": extract_text_content(response.content), "actions": actions}


async def coaching_node(state: AgentState) -> dict:
    """Handle progress reviews, motivation, and setback discussions."""
    print(f"[AGENT] coaching_node START")
    user_message = state["user_input"]
    user_name = state["user_profile"].name
    user_id = state.get("user_id")
    active_plans = state.get("active_plans", [])
    session_completed = state.get("completed_tasks", [])

    system_prompt = build_system_prompt("system_base", "coaching")

    # Fetch global user context from database
    db_context = await get_user_context(user_id)
    context_str = format_user_context_for_prompt(db_context)

    # Build progress context combining session plans + DB data
    progress_parts = [f"User's name: {user_name}"]

    # Add database context (tasks and goals from Supabase)
    progress_parts.append(f"\n## From Database\n{context_str}")

    # Add session-specific plans (if any)
    if active_plans:
        progress_parts.append("\n## Session Plans")
        for plan in active_plans:
            total = len(plan.tasks)
            done = sum(1 for t in plan.tasks if t.task_name in session_completed)
            progress_parts.append(
                f"\nPlan: {plan.project_name}"
                f"\n- Progress: {done}/{total} tasks ({round(done/total*100) if total else 0}%)"
                f"\n- Deadline: {plan.deadline}"
                f"\n- Tasks: {', '.join(t.task_name for t in plan.tasks)}"
                f"\n- Completed: {', '.join(session_completed) if session_completed else 'None yet'}"
            )

    full_system = f"{system_prompt}\n\n## User Context\n{''.join(progress_parts)}"

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    # Extract tool calls (actions)
    actions = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        actions = [
            {"type": call["name"], "data": call["args"]}
            for call in response.tool_calls
        ]

    print(f"[AGENT] coaching_node END | response_len={len(extract_text_content(response.content))} | actions={len(actions)}")
    return {"response": extract_text_content(response.content), "actions": actions}


async def confirmation_node(state: AgentState) -> dict:
    """
    Handle the 'confirm' intent.

    Since plans are saved automatically by the orchestrator in the previous turn,
    this node simply acknowledges the action and triggers a UI refresh.
    """
    print(f"[AGENT] confirmation_node START")

    # Get the most recent plan from the session context
    active_plans = state.get("active_plans", [])
    latest_plan = active_plans[-1] if active_plans else None

    if latest_plan:
        task_count = len(latest_plan.tasks)
        project_name = latest_plan.project_name

        response = (
            f"Done! Your **{project_name}** plan is now active. "
            f"All {task_count} tasks are ready in your task list.\n\n"
            f"Would you like to start with the first one?"
        )

        print(f"[AGENT] confirmation_node END | confirmed plan='{project_name}' | tasks={task_count}")
        return {
            "response": response,
            "actions": [{"type": "refresh_ui", "data": {"project_name": project_name}}]
        }
    else:
        # Fallback if no plan exists in session
        print(f"[AGENT] confirmation_node END | no active plan found")
        return {
            "response": "I'm ready to help, but I don't see a pending plan. What goal would you like to work on?",
            "actions": []
        }


async def planning_response_node(state: AgentState) -> dict:
    """Generate a friendly response presenting the created plan."""
    print(f"[AGENT] planning_response_node START")
    final_plan = state["final_plan"]
    user_name = state["user_profile"].name

    system_prompt = build_system_prompt("system_base", "planning")

    # Format the plan for presentation
    tasks_formatted = []
    anchor_emojis = {
        "morning": "sunrise",
        "coffee": "sunrise",
        "lunch": "sunny",
        "midday": "sunny",
        "afternoon": "sunny",
        "evening": "crescent_moon",
        "night": "crescent_moon",
        "end of day": "crescent_moon",
    }

    for task in final_plan.tasks:
        anchor_lower = task.assigned_anchor.lower()
        emoji = "sunrise"  # Default
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

Present this plan to the user in a friendly, encouraging way."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    # Convert plan tasks into create_task actions for the frontend
    actions = []
    for task in final_plan.tasks:
        actions.append({
            "type": "create_task",
            "data": {
                "task_name": task.task_name,
                "estimated_minutes": task.estimated_minutes,
                "energy_required": task.energy_required,
                "assigned_anchor": task.assigned_anchor,
                "rationale": task.rationale,
            }
        })

    print(f"[AGENT] planning_response_node END | response_len={len(extract_text_content(response.content))} | actions={len(actions)}")
    return {"response": extract_text_content(response.content), "actions": actions}


# ============================================================
# PLANNING PIPELINE NODES
# ============================================================


# --- Node 1: The Project Manager ---
async def smart_refiner_node(state: AgentState) -> dict:
    """Refines vague input into a strict SMART goal."""
    print(f"[AGENT] smart_refiner_node START")
    goal_text = state["user_input"]

    system_prompt = """You are a pragmatic Project Manager.
    Analyze the user's goal. If it is vague, make reasonable assumptions to make it S.M.A.R.T.
    You MUST output a concrete deadline (e.g. 'End of this week', 'Next Friday') if none is provided.
    Be concise and action-oriented."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=goal_text)]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=SmartGoalSchema
    )

    print(f"[AGENT] smart_refiner_node END | summary={result.summary[:50]}... | deadline={result.deadline}")
    return {"smart_goal": result}


# --- Node 2: The Architect ---
async def task_splitter_node(state: AgentState) -> dict:
    """Breaks the SMART goal into atomic micro-tasks."""
    print(f"[AGENT] task_splitter_node START")
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

    print(f"[AGENT] task_splitter_node END | tasks_count={len(result.tasks)} | tasks={result.tasks}")
    return {"raw_tasks": result.tasks}


# --- Node 3: The Tiny Habits Coach ---
async def context_matcher_node(state: AgentState) -> dict:
    """Matches tasks to user anchors based on energy levels."""
    print(f"[AGENT] context_matcher_node START")
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

    print(f"[AGENT] context_matcher_node END | project={result.project_name} | tasks_count={len(result.tasks)}")
    return {"final_plan": result}


# ============================================================
# LEGACY NODE (for backwards compatibility with /api/chat old behavior)
# ============================================================


async def legacy_coach_node(state: AgentState) -> dict:
    """Main coaching node that responds to user messages (legacy)."""
    print(f"[AGENT] legacy_coach_node START")
    system_prompt = build_system_prompt("system_base")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    print(f"[AGENT] legacy_coach_node END")
    return {"messages": [response]}
