"""
Execution tracking for Opik - monitors task completion and goal adherence.
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any
try:
    from opik import Opik
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    Opik = None

from app.core.config import settings

# Initialize client
try:
    if OPIK_AVAILABLE and settings.opik_api_key:
        opik_client = Opik(api_key=settings.opik_api_key)
    else:
        opik_client = None
except Exception:
    opik_client = None


class ExecutionTracker:
    """
    Tracks task execution events and logs them to Opik as feedback.
    
    This enables measuring:
    - Task completion rate
    - On-time completion rate  
    - Goal adherence (sessions/week)
    - Rescheduling effectiveness
    """
    
    @staticmethod
    def log_task_completion(
        task_id: str,
        task_name: str,
        user_id: str,
        goal_id: Optional[str],
        scheduled_date: Optional[str],
        completed_date: str,
        was_rescheduled: bool = False
    ):
        """Log when a task is completed."""
        if not opik_client:
            return
            
        try:
            # Calculate if completed on time
            on_time = scheduled_date == completed_date if scheduled_date else True
            
            # Create a trace for this execution event
            trace = opik_client.trace(
                name="task_execution",
                input={"task_id": task_id, "event": "completion"},
                output={"status": "completed", "on_time": on_time},
                metadata={
                    "task_name": task_name,
                    "user_id_hash": str(abs(hash(user_id)))[:8],
                    "goal_id": goal_id,
                    "scheduled_date": scheduled_date,
                    "completed_date": completed_date,
                    "was_rescheduled": was_rescheduled,
                    "event_type": "completion"
                }
            )
            trace.end()
            
            print(f"[OPIK] Logged task completion: {task_name} | on_time={on_time}")
            
        except Exception as e:
            print(f"[OPIK] Error logging completion: {e}")
    
    @staticmethod
    def log_task_missed(
        task_id: str,
        task_name: str,
        user_id: str,
        goal_id: Optional[str],
        scheduled_date: str,
        missed_date: str
    ):
        """Log when a task is missed/skipped."""
        if not opik_client:
            return
            
        try:
            trace = opik_client.trace(
                name="task_execution",
                input={"task_id": task_id, "event": "miss"},
                output={"status": "missed"},
                metadata={
                    "task_name": task_name,
                    "user_id_hash": str(abs(hash(user_id)))[:8],
                    "goal_id": goal_id,
                    "scheduled_date": scheduled_date,
                    "missed_date": missed_date,
                    "event_type": "miss"
                }
            )
            trace.end()
            
            print(f"[OPIK] Logged task miss: {task_name}")
            
        except Exception as e:
            print(f"[OPIK] Error logging miss: {e}")
    
    @staticmethod
    def log_reschedule(
        task_id: str,
        task_name: str,
        user_id: str,
        goal_id: Optional[str],
        original_date: str,
        new_date: str,
        reason: str = "user_missed_session"
    ):
        """Log when Goalie reschedules a task adaptively."""
        if not opik_client:
            return
            
        try:
            trace = opik_client.trace(
                name="adaptive_reschedule",
                input={"task_id": task_id, "original_date": original_date},
                output={"new_date": new_date, "reason": reason},
                metadata={
                    "task_name": task_name,
                    "user_id_hash": str(abs(hash(user_id)))[:8],
                    "goal_id": goal_id,
                    "event_type": "reschedule"
                }
            )
            trace.end()
            
            print(f"[OPIK] Logged reschedule: {task_name} | {original_date} → {new_date}")
            
        except Exception as e:
            print(f"[OPIK] Error logging reschedule: {e}")
    
    @staticmethod
    def calculate_completion_metrics(tasks: list) -> Dict[str, Any]:
        """
        Calculate execution metrics from a list of tasks.
        
        Returns:
            - completion_rate: % of tasks completed vs total
            - on_time_rate: % completed on scheduled date
            - reschedule_success_rate: % of rescheduled tasks completed
        """
        total = len(tasks)
        if total == 0:
            return {"completion_rate": 0, "on_time_rate": 0, "reschedule_success_rate": 0}
        
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        on_time = sum(1 for t in tasks if t.get("status") == "completed" and t.get("completed_on_time"))
        rescheduled = [t for t in tasks if t.get("was_rescheduled")]
        rescheduled_completed = sum(1 for t in rescheduled if t.get("status") == "completed")
        
        return {
            "completion_rate": round(completed / total * 100, 1),
            "on_time_rate": round(on_time / completed * 100, 1) if completed > 0 else 0,
            "reschedule_success_rate": round(rescheduled_completed / len(rescheduled) * 100, 1) if rescheduled else 0,
            "total_tasks": total,
            "completed_tasks": completed,
            "rescheduled_tasks": len(rescheduled)
        }


# Singleton instance
execution_tracker = ExecutionTracker()
