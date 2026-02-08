from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
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
from app.agent.schema import SmartGoalSchema, TaskList, ProjectPlan, IntentClassification, RefinerOutput
from app.agent.prompts import build_system_prompt, load_prompt
from app.agent.tools.crud import ALL_TOOLS, STATIC_TOOLS
from app.agent.tools.google_tools import create_google_tools
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


def get_conversational_llms(user_id: str = None):
    """Get conversational LLMs with appropriate tools bound.

    If user has Google connected, binds static + Google tools.
    Otherwise returns the module-level defaults (static tools only).
    """
    if not user_id:
        return llm_conversational_primary, llm_conversational_fallback

    google_tools = create_google_tools(user_id)
    if not google_tools:
        return llm_conversational_primary, llm_conversational_fallback

    # User has Google connected — create new LLM instances with all tools
    all_tools = STATIC_TOOLS + google_tools
    primary = create_llm(
        settings.llm_primary_model,
        settings.llm_conversational_temperature,
        settings.llm_primary_max_retries,
    ).bind_tools(all_tools)
    fallback = create_llm(
        settings.llm_fallback_model,
        settings.llm_conversational_temperature,
        settings.llm_fallback_max_retries,
    ).bind_tools(all_tools)

    return primary, fallback


# Google tool names that execute server-side (not frontend actions)
GOOGLE_TOOL_NAMES = {"read_calendar", "create_calendar_event"}


async def execute_google_tools_and_refine(response, messages, conv_primary, conv_fallback, user_id: str):
    """Handle tool calls: execute Google tools server-side, collect static tool actions.

    Two-pass pattern:
    1. Separate Google tool calls from static (frontend action) tool calls
    2. Execute Google tools server-side
    3. If any Google tools were called, do a second LLM call with ToolMessages
    4. Return (response_text, frontend_actions)
    """
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        return extract_text_content(response.content), []

    google_calls = []
    static_calls = []
    for call in response.tool_calls:
        if call["name"] in GOOGLE_TOOL_NAMES:
            google_calls.append(call)
        else:
            static_calls.append(call)

    # Frontend actions from static tools
    frontend_actions = [
        {"type": call["name"], "data": call["args"]}
        for call in static_calls
    ]

    # If no Google tools were called, return immediately
    if not google_calls:
        return extract_text_content(response.content), frontend_actions

    # Execute Google tools server-side
    google_tools = create_google_tools(user_id)
    tool_map = {t.name: t for t in google_tools}

    tool_messages = []
    for call in google_calls:
        tool = tool_map.get(call["name"])
        if tool:
            try:
                result = tool.invoke(call["args"])
                print(f"[AGENT] Google tool '{call['name']}' result: {str(result)[:100]}...")
            except Exception as e:
                result = f"Error: {e}"
                print(f"[AGENT] Google tool '{call['name']}' error: {e}")
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=call["id"])
            )

    # Second LLM call: feed tool results back for a natural response
    refined_messages = messages + [response] + tool_messages
    refined_response = await invoke_with_fallback(
        conv_primary, conv_fallback, refined_messages
    )

    # Check for any additional tool calls in the refined response
    if hasattr(refined_response, "tool_calls") and refined_response.tool_calls:
        for call in refined_response.tool_calls:
            if call["name"] not in GOOGLE_TOOL_NAMES:
                frontend_actions.append({"type": call["name"], "data": call["args"]})

    return extract_text_content(refined_response.content), frontend_actions


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

        # Fetch Google Calendar context
        calendar_context = ""
        try:
            from app.services.calendar_service import get_calendar_context
            calendar_context = await get_calendar_context(user_id)
        except Exception as e:
            print(f"[DEBUG] Error fetching calendar context: {e}")

        return {
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "goals": goals,
            "calendar_context": calendar_context,
        }
    except Exception as e:
        print(f"[DEBUG] Error fetching user context: {e}")
        return {"active_tasks": [], "completed_tasks": [], "goals": [], "calendar_context": ""}


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

    # Google Calendar context
    calendar = context.get("calendar_context", "")
    if calendar:
        parts.append(calendar)

    return "\n\n".join(parts)


# ============================================================
# ORCHESTRATOR NODES
# ============================================================


async def intent_router_node(state: AgentState) -> dict:
    """Classify user intent to route to the appropriate agent.

    SOCRATIC GATEKEEPER: Pre-emptively checks if we're waiting for a clarification
    response before doing standard intent classification.
    """
    print(f"[AGENT] intent_router_node START")
    user_message = state["user_input"]
    user_id = state.get("user_id")

    # PRE-EMPTIVE CHECK: Are we waiting for an answer to a clarifying question?
    # We check attempts < 2 to prevent infinite clarification loops
    pending_context = state.get("pending_context")
    clarification_attempts = state.get("clarification_attempts", 0)

    if pending_context and clarification_attempts < 2:
        print(f"[AGENT] intent_router_node | SOCRATIC: Detected pending_context, routing to planning_continuation")
        print(f"[AGENT] intent_router_node | pending_context={pending_context} | attempts={clarification_attempts}")
        # Return a synthetic IntentClassification to route to planning_continuation
        return {
            "intent": IntentClassification(
                intent="planning_continuation",
                confidence=1.0,
                reasoning="User is responding to a clarifying question about their goal"
            )
        }

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

    # HITL: Include staging_plan context to help detect modify intent
    staging_plan = state.get("staging_plan")
    if staging_plan:
        context_parts.append(
            f"User has a DRAFT PLAN awaiting confirmation: '{staging_plan.project_name}' with {len(staging_plan.tasks)} tasks. "
            f"If user wants to change this plan, classify as 'modify'."
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

    # Get per-user LLMs (with Google tools if connected)
    conv_primary, conv_fallback = get_conversational_llms(user_id)

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(conv_primary, conv_fallback, messages)

    # Handle tool calls: Google tools execute server-side, static tools become frontend actions
    response_text, actions = await execute_google_tools_and_refine(
        response, messages, conv_primary, conv_fallback, user_id
    )

    print(f"[AGENT] casual_node END | response_len={len(response_text)} | actions={len(actions)}")
    return {"response": response_text, "actions": actions}


async def coaching_node(state: AgentState) -> dict:
    """Handle progress reviews, motivation, and setback discussions."""
    print(f"[AGENT] coaching_node START")
    user_message = state["user_input"]
    user_name = state["user_profile"].name
    user_id = state.get("user_id")
    active_plans = state.get("active_plans") or []
    session_completed = state.get("completed_tasks") or []

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

    # Get per-user LLMs (with Google tools if connected)
    conv_primary, conv_fallback = get_conversational_llms(user_id)

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_message),
    ]

    response = await invoke_with_fallback(conv_primary, conv_fallback, messages)

    # Handle tool calls: Google tools execute server-side, static tools become frontend actions
    response_text, actions = await execute_google_tools_and_refine(
        response, messages, conv_primary, conv_fallback, user_id
    )

    print(f"[AGENT] coaching_node END | response_len={len(response_text)} | actions={len(actions)}")
    return {"response": response_text, "actions": actions}


async def confirmation_node(state: AgentState) -> dict:
    """
    Handle the 'confirm' intent.

    HUMAN-IN-THE-LOOP (HITL): This node commits the staged plan to active_plans
    and triggers the actual database persistence. Plans are only saved when
    the user explicitly confirms.
    """
    print(f"[AGENT] confirmation_node START")

    # HITL: Check for staged plan first (new flow)
    staging_plan = state.get("staging_plan")

    if staging_plan:
        # HITL COMMIT: User said "Yes" and we have a draft
        task_count = len(staging_plan.tasks)
        project_name = staging_plan.project_name

        # Convert plan tasks into create_task actions for the frontend
        actions = [{"type": "refresh_ui", "data": {"project_name": project_name}}]
        for task in staging_plan.tasks:
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

        # Auto-add tasks to Google Calendar if user has it connected
        user_id = state.get("user_id")
        calendar_results = []
        if user_id:
            try:
                from app.services.calendar_service import create_calendar_events_for_plan
                calendar_results = await create_calendar_events_for_plan(user_id, staging_plan)
            except Exception as e:
                print(f"[AGENT] confirmation_node | Calendar sync failed: {e}")

        calendar_msg = ""
        if calendar_results:
            calendar_msg = f"\n\nI've also added all {len(calendar_results)} tasks to your **Google Calendar** with reminders."

        response = (
            f"Done! I've committed your **{project_name}** plan. "
            f"All {task_count} tasks are now in your dashboard."
            f"{calendar_msg}\n\n"
            f"Ready to tackle the first one?"
        )

        print(f"[AGENT] confirmation_node END | HITL COMMIT | plan='{project_name}' | tasks={task_count}")
        return {
            "response": response,
            "active_plans": [staging_plan],  # Promote to active (will be saved to DB)
            "staging_plan": None,  # Clear the staging buffer
            "actions": actions,
        }

    # Legacy flow: Check for active plans (backwards compatibility)
    active_plans = state.get("active_plans") or []
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
        print(f"[AGENT] confirmation_node END | no staged or active plan found")
        return {
            "response": "I'm ready to help, but I don't see a pending plan. What goal would you like to work on?",
            "actions": []
        }


async def planning_response_node(state: AgentState) -> dict:
    """Generate a friendly response presenting the created plan.

    HUMAN-IN-THE-LOOP (HITL): This node now stages the plan for user confirmation
    instead of committing it directly. The plan is stored in `staging_plan` and
    only moves to `active_plans` when the user explicitly confirms.
    """
    print(f"[AGENT] planning_response_node START")
    final_plan = state["final_plan"]
    user_name = state["user_profile"].name

    # Get context tags to inform presentation style
    context_tags = state.get("goal_context_tags") or []
    is_beginner = "beginner" in context_tags or "sedentary" in context_tags

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

    # Include context for better presentation
    context_info = ""
    if context_tags:
        context_info = f"\nUser Context Tags: {', '.join(context_tags)}"
        if is_beginner:
            context_info += "\n(User is a BEGINNER - explain WHY these specific tasks are the right starting point)"

    plan_summary = f"""Plan created:
- Project: {final_plan.project_name}
- Goal: {final_plan.smart_goal_summary}
- Deadline: {final_plan.deadline}{context_info}

Tasks:
{chr(10).join(tasks_formatted)}"""

    user_prompt = f"""The user "{user_name}" asked to create a plan and the pipeline generated this:

{plan_summary}

Present this plan to the user. Remember the psychology hooks from your prompt:
1. Explain WHY these tasks fit their level
2. Emphasize how quick and easy the tasks are
3. CRITICAL: End with a clear Call-to-Action asking if they want to save this plan.
   Example: "Shall I save this plan to your profile?" or "Ready to commit to this?"
   Do NOT imply the plan is already saved."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await invoke_with_fallback(
        llm_conversational_primary, llm_conversational_fallback, messages
    )

    # HITL: Stage the plan for confirmation instead of creating tasks immediately
    # The plan will only be persisted when the user confirms
    print(f"[AGENT] planning_response_node END | response_len={len(extract_text_content(response.content))} | STAGED (awaiting confirmation)")
    return {
        "response": extract_text_content(response.content),
        "staging_plan": final_plan,  # Stage for confirmation
        # No actions yet - will be created on confirmation
    }


# ============================================================
# PLANNING PIPELINE NODES
# ============================================================


# --- Node 1: The Project Manager (with Socratic Gatekeeper) ---
async def smart_refiner_node(state: AgentState) -> dict:
    """Refines vague input into a strict SMART goal.

    SOCRATIC GATEKEEPER: This node now acts as both Validator and Refiner.
    It decides whether to ask for clarification or proceed with planning.
    """
    print(f"[AGENT] smart_refiner_node START")
    user_input = state["user_input"]
    pending_context = state.get("pending_context", {})
    clarification_attempts = state.get("clarification_attempts", 0)

    # Load the dual-path prompt
    system_prompt = load_prompt("smart_refiner")

    # Format the prompt with current context
    formatted_prompt = system_prompt.replace("{user_input}", user_input)
    formatted_prompt = formatted_prompt.replace(
        "{pending_context}",
        str(pending_context) if pending_context else "None"
    )

    messages = [
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=f"Process this goal: {user_input}")
    ]

    # Call LLM with RefinerOutput schema for dual-path response
    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=RefinerOutput
    )

    print(f"[AGENT] smart_refiner_node | status={result.status}")

    if result.status == "needs_clarification":
        # PATH A: Ask clarifying question and save context
        print(f"[AGENT] smart_refiner_node | SOCRATIC: Asking clarification | question={result.clarifying_question[:50]}...")
        return {
            "response": result.clarifying_question,
            "pending_context": result.saved_context,
            "clarification_attempts": clarification_attempts + 1,
            # Don't set smart_goal - we're not ready yet
        }
    else:
        # PATH B: Goal is ready, proceed to task splitting
        context_tags = result.context_tags or []
        print(f"[AGENT] smart_refiner_node END | smart_goal={result.smart_goal[:50]}... | context_tags={context_tags}")

        # Convert the string smart_goal to SmartGoalSchema for downstream nodes
        # We create a minimal schema with the refined goal
        smart_goal_schema = SmartGoalSchema(
            summary=result.smart_goal,
            specific_outcome=result.smart_goal,
            measurable_metric="Goal completion",
            deadline="This week",  # Default, will be refined by context
            constraints=None
        )

        return {
            "response": result.response_text,
            "smart_goal": smart_goal_schema,
            "goal_context_tags": context_tags,  # Pass tags to task_splitter
            "pending_context": None,  # Clear context on success
            "clarification_attempts": 0,  # Reset counter
        }


# --- Node 2: The Architect (with Coach Logic) ---
async def task_splitter_node(state: AgentState) -> dict:
    """Breaks the SMART goal into atomic micro-tasks.

    COACH MODE: Uses context_tags to determine whether to act as a Coach
    (providing specific curriculum for beginners) or a Secretary (providing
    higher-level tasks for experienced users).
    """
    print(f"[AGENT] task_splitter_node START")
    smart_goal = state["smart_goal"]
    user = state["user_profile"]

    # Get context tags from the Refiner (determines Coach vs Secretary mode)
    context_tags = state.get("goal_context_tags") or []
    context_tags_str = ", ".join(context_tags) if context_tags else "none specified"

    # Get user anchors for task scheduling context
    user_anchors = ", ".join(user.anchors)

    print(f"[AGENT] task_splitter_node | context_tags={context_tags} | mode={'Coach' if 'beginner' in context_tags or 'sedentary' in context_tags else 'Standard'}")

    # Load the Coach prompt
    system_prompt = load_prompt("task_splitter")

    # Format the prompt with context
    formatted_prompt = system_prompt.replace("{smart_goal}", smart_goal.summary)
    formatted_prompt = formatted_prompt.replace("{context_tags}", context_tags_str)
    formatted_prompt = formatted_prompt.replace("{user_anchors}", user_anchors)

    user_prompt = f"""Break this goal into actionable micro-tasks:

    GOAL: {smart_goal.summary}
    CONTEXT TAGS: {context_tags_str}
    USER ANCHORS: {user_anchors}
    DEADLINE: {smart_goal.deadline}

    Remember: If context_tags include "beginner" or "sedentary", YOU must provide the specific
    curriculum. DO NOT assign "research" or "find a plan" tasks."""

    messages = [
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=user_prompt),
    ]

    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=TaskList
    )

    print(f"[AGENT] task_splitter_node END | tasks_count={len(result.tasks)} | tasks={result.tasks}")
    return {"raw_tasks": result.tasks}


# --- Node 3: The Tiny Habits Coach ---
async def context_matcher_node(state: AgentState) -> dict:
    """Matches tasks to user anchors based on energy levels.

    Uses deterministic anchor availability checking (Python) to enforce
    calendar conflicts, then lets the LLM decide which available slot
    best fits each task based on energy/psychology.
    """
    print(f"[AGENT] context_matcher_node START")
    tasks = state["raw_tasks"]
    smart_goal = state["smart_goal"]
    user = state["user_profile"]
    user_id = state.get("user_id")

    tasks_formatted = "\n".join(f"- {task}" for task in tasks)

    # Compute anchor availability (checks Google Calendar + Goally tasks)
    from app.agent.adaptive_scheduler import (
        get_available_anchors,
        format_availability_for_prompt,
        anchor_to_timestamp,
    )

    availability_section = ""
    if user_id:
        try:
            availability = await get_available_anchors(
                user_id=user_id,
                anchors=user.anchors,
                days_ahead=7,
                task_duration_minutes=20,
            )
            availability_section = format_availability_for_prompt(availability)
            print(f"[AGENT] context_matcher_node | availability computed for {len(availability)} days")
        except Exception as e:
            print(f"[AGENT] context_matcher_node | availability check failed: {e}")

    # Fallback: if no availability data, list all anchors as available
    if not availability_section:
        anchors_formatted = ", ".join(user.anchors)
        availability_section = f"All anchors available: {anchors_formatted}"

    system_prompt = """You are a Behavioral Scientist using the Tiny Habits method.

    INSTRUCTIONS:
    1. Assess each task's cognitive load (high/medium/low).
    2. Assign each task to one of the AVAILABLE anchors listed below.
       - High Focus tasks -> Morning anchors (fresh energy)
       - Medium Focus tasks -> Mid-day anchors
       - Low Focus/Admin tasks -> End of day anchors
    3. You MUST ONLY use anchors marked as available. Never pick a blocked slot.
    4. Estimate realistic time (5-20 minutes each).
    5. Provide a brief rationale for each assignment."""

    user_prompt = f"""Schedule these tasks for the user:

    PROJECT: {smart_goal.summary}
    DEADLINE: {smart_goal.deadline}

    USER PROFILE:
    - Role: {user.role}

    {availability_section}

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

    # Assign actual timestamps to tasks based on their assigned anchors
    from datetime import datetime
    from zoneinfo import ZoneInfo

    base_date = datetime.now(ZoneInfo("America/Los_Angeles"))

    for task in result.tasks:
        scheduled_time = anchor_to_timestamp(
            anchor=task.assigned_anchor,
            timezone="America/Los_Angeles",
            base_date=base_date,
        )
        task.scheduled_at = scheduled_time.isoformat()

    print(f"[AGENT] context_matcher_node END | project={result.project_name} | tasks_count={len(result.tasks)}")
    return {"final_plan": result}


# ============================================================
# MODIFY NODE - Edit Loop for Plan Modifications
# ============================================================


async def modify_node(state: AgentState) -> dict:
    """Modifies an existing plan based on user feedback.

    EDIT LOOP PATTERN: Takes the current staging_plan (or active_plans[0]),
    applies user-requested changes, and returns a NEW staging_plan.
    This keeps the HITL flow intact - user must still confirm after modifications.
    """
    print(f"[AGENT] modify_node START")

    # 1. Get the target plan (prefer staging, fallback to active)
    active_plans = state.get("active_plans") or []
    current_plan = state.get("staging_plan") or (active_plans[0] if active_plans else None)

    if not current_plan:
        print(f"[AGENT] modify_node END | no plan to modify")
        return {
            "response": "I don't see a plan to modify. Would you like to create one? Just tell me your goal!",
            "actions": [],
        }

    # 2. Get user feedback from the last message
    user_feedback = state["user_input"]
    user = state["user_profile"]
    user_anchors = ", ".join(user.anchors)

    # 3. Serialize current plan to JSON for the LLM
    current_plan_json = current_plan.model_dump_json(indent=2)

    print(f"[AGENT] modify_node | plan={current_plan.project_name} | feedback={user_feedback[:50]}...")

    # 4. Load and format the modifier prompt
    system_prompt = load_prompt("modifier")
    system_prompt = system_prompt.replace("{current_plan_json}", current_plan_json)
    system_prompt = system_prompt.replace("{user_feedback}", user_feedback)
    system_prompt = system_prompt.replace("{user_anchors}", user_anchors)

    user_prompt = f"""Please modify this plan based on my feedback:

CURRENT PLAN:
{current_plan_json}

MY FEEDBACK: {user_feedback}

USER ANCHORS: {user_anchors}

Return the complete updated plan with my requested changes applied."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # 5. Run the modifier LLM
    result = await invoke_with_fallback(
        llm_primary, llm_fallback, messages, structured_output=ProjectPlan
    )

    print(f"[AGENT] modify_node END | updated_plan={result.project_name} | tasks_count={len(result.tasks)}")

    # 6. Return the NEW staging plan (triggers UI preview update)
    return {
        "staging_plan": result,
        "response": "I've updated the plan based on your feedback. How does this look?",
        "actions": [],
    }


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
