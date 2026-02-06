
import asyncio
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.graph import planning_graph
from app.agent.opik_utils import trace_plan_execution
from app.agent.schema import UserProfile
from app.core.config import settings

# Hardcoded fallback scenarios
FALLBACK_SCENARIOS = [
    {"goal": "Launch my portfolio website", "role": "Designer", "anchors": ["Morning", "After Lunch", "Night"]},
    {"goal": "Run 5k without stopping", "role": "Beginner Runner", "anchors": ["Morning", "Evening"]},
    {"goal": "Learn basic Spanish phrases", "role": "Traveler", "anchors": ["Commute", "Evening"]},
]

async def run_turn(state, mode="experiment"):
    """Helper to run a single turn with tracing."""
    return await trace_plan_execution(
        goal=state.get("user_input", ""),
        user_profile=state.get("user_profile"),
        mode=mode,
        execution_fn=planning_graph.ainvoke,
        input=state
    )

async def run_experiment():
    print(f"Starting Experiment: Goalie Planner V1 Evaluation (Multi-turn)")
    print(f"Time: {datetime.now()}")
    
    if not settings.opik_api_key:
        print("WARNING: OPIK_API_KEY is not set. Traces will NOT be logged.")

    scenarios = FALLBACK_SCENARIOS
    results = []
    
    for i, scenario in enumerate(scenarios):
        print(f"\n--- Scenario {i+1}/{len(scenarios)} ---")
        print(f"Goal: {scenario['goal']}")
        
        user_profile = UserProfile(
            name="Test User",
            role=scenario["role"],
            anchors=scenario["anchors"]
        )
        
        # Initial State
        state = {
            "messages": [],
            "user_input": scenario["goal"],
            "user_profile": user_profile,
            "session_id": "experiment-session",
            "pending_context": None
        }
        
        try:
            start_time = datetime.now()
            
            # --- Turn 1 ---
            print("Running Turn 1...")
            result = await run_turn(state)
            
            # Check for clarification
            if result.get("pending_context"):
                question = result.get("response", "No question asked")
                print(f"Agent asked: {question}")
                
                # Simulate User Response
                simulated_response = "I can spend 45 minutes daily and want to finish in 2 weeks."
                print(f"Simulating User: {simulated_response}")
                
                # --- Turn 2 (with context) ---
                state["user_input"] = simulated_response
                state["pending_context"] = result["pending_context"]
                state["clarification_attempts"] = 1
                
                print("Running Turn 2...")
                result = await run_turn(state)

            duration = (datetime.now() - start_time).total_seconds()
            
            final_plan = result.get("final_plan")
            tasks_count = len(final_plan.tasks) if final_plan else 0
            
            if final_plan:
                print(f"Result: Success | {tasks_count} tasks created | {duration:.2f}s")
                status = "success"
            else:
                print(f"Result: Incomplete (still asking questions) | {duration:.2f}s")
                status = "incomplete"

            results.append({
                "scenario": scenario["goal"],
                "status": status,
                "tasks": tasks_count,
                "duration": duration
            })
            
        except Exception as e:
            print(f"Result: Failed | Error: {e}")
            results.append({"scenario": scenario["goal"], "status": "failed", "error": str(e)})
            
    # Summary
    print("\n=== Experiment Summary ===")
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"Total Scenarios: {len(results)}")
    print(f"Successful Runs: {success_count}")
    print(f"See Opik Dashboard for trace details and LLM-as-judge scores.")

if __name__ == "__main__":
    asyncio.run(run_experiment())
