
import os
import json
from typing import Any, Dict, List, Optional

import os
import json
from typing import Any, Dict, List, Optional
try:
    from opik import Opik
    from opik.evaluation.metrics import BaseMetric, score_result
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    Opik = None
    
from app.core.config import settings
from app.agent.schema import ProjectPlan, UserProfile
from langchain_google_genai import ChatGoogleGenerativeAI
import asyncio

# Initialize Opik client
try:
    if OPIK_AVAILABLE and settings.opik_api_key:
        opik_client = Opik(api_key=settings.opik_api_key)
    else:
        opik_client = None
except Exception:
    opik_client = None

# =============================================================================
# HELPER: LLM JUDGE
# =============================================================================

llm_judge = None

def get_judge():
    global llm_judge
    if llm_judge is None:
        llm_judge = ChatGoogleGenerativeAI(
            model=settings.llm_primary_model,
            google_api_key=settings.google_api_key,
            temperature=0.0
        )
    return llm_judge

async def run_llm_judge(prompt: str) -> float:
    """Run a simple LLM check and return a 0.0-1.0 score."""
    try:
        judge = get_judge()
        response = await judge.ainvoke(prompt)
        content = response.content
        
        # Simple heuristic parsing
        content_lower = str(content).lower()
        if "score: 1" in content_lower or "score:1" in content_lower: return 1.0
        if "score: 0" in content_lower or "score:0" in content_lower: return 0.0
        
        # Check for numbers
        import re
        match = re.search(r"(\d+(\.\d+)?)", str(content))
        if match:
            val = float(match.group(1))
            if val > 1.0: val = val / 10.0 # Handle 1-10 scale
            if val > 1.0: val = 1.0
            return val
            
        return 0.8 # Default optimistic fallback
    except Exception as e:
        print(f"Judge error: {e}")
        return 0.5

# =============================================================================
# TRACING HELPER
# =============================================================================

async def trace_plan_execution(
    goal: str,
    user_profile: UserProfile | None,
    mode: str,
    execution_fn, # Async function to run
    *args, **kwargs
):
    """
    Wraps an execution function with Opik tracing and evaluation.
    """
    if not opik_client:
        return await execution_fn(*args, **kwargs)
        
    trace_name = "goalie.plan.run"
    
    # Prepare metadata
    metadata = {
        "user_id_hash": str(abs(hash(user_profile.name if user_profile else "anon")))[:8],
        "timezone": "UTC",
        "model_name": settings.llm_primary_model,
        "mode": mode,
        "prompt_version": "v1" # Hardcoded for now, could be dynamic
    }
    
    # Start Trace
    trace = opik_client.trace(
        name=trace_name,
        input={"goal": goal, "profile": user_profile.model_dump() if user_profile else {}},
        metadata=metadata
    )
    
    try:
        # Run Execution
        result = await execution_fn(*args, **kwargs)
        
        # Extract Plan Data
        final_plan = result.get("final_plan")
        
        if final_plan:
            # It might be a ProjectPlan object or dict
            tasks = []
            if hasattr(final_plan, "tasks"):
                tasks = [t.model_dump() if hasattr(t, "model_dump") else t for t in final_plan.tasks]
            elif isinstance(final_plan, dict):
                tasks = final_plan.get("tasks", [])
                
            project_name = getattr(final_plan, "project_name", lambda: final_plan.get("project_name", "Unknown Plan"))
            if callable(project_name): project_name = project_name()
            
            # Serialize for output
            output_data = {
                "project_name": project_name,
                "tasks_count": len(tasks),
                "tasks": tasks
            }
            
            trace.end(output=output_data)
            
            # --- ONLINE EVALUATION ---
            # Fire and forget (create task) to avoid blocking response? 
            # For hackathon, await it to ensure it logs.
            
            # 1. Constraint Adherence
            s1 = await run_llm_judge(f"""
                Example specific constraint: "No meetings after 5pm" or "Lunch break at 12".
                Did the following plan respect implied or standard constraints?
                Goal: {goal}
                Tasks: {json.dumps(tasks)[:1000]}
                Return 'Score: 1.0' (Yes) or 'Score: 0.0' (No).
            """)
            trace.log_feedback_score(name="Constraint Adherence", value=s1)
            
            # 2. Feasibility
            s2 = await run_llm_judge(f"""
                Is this plan realistically achievable?
                Tasks: {json.dumps(tasks)[:1000]}
                Return 'Score: 1.0' (Yes) or 'Score: 0.0' (No).
            """)
            trace.log_feedback_score(name="Feasibility", value=s2)
            
            # 3. Task Coverage
            s3 = await run_llm_judge(f"""
                Does this plan fully cover the user's goal?
                Goal: {goal}
                Tasks: {json.dumps(tasks)[:1000]}
                Return 'Score: 1.0' (Yes) or 'Score: 0.0' (No).
            """)
            trace.log_feedback_score(name="Task Coverage", value=s3)
            
        else:
             trace.end(output={"warning": "No final plan produced"})
             
        return result
        
    except Exception as e:
        trace.end(output={"error": str(e)})
        raise e
