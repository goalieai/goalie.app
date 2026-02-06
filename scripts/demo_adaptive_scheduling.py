"""
Adaptive Rescheduling Simulation for Opik Demo

This demonstrates Goalie's core value prop:
- User sets goal (Learn Spanish)
- Misses a scheduled session
- Goalie adaptively reschedules
- Logs all events to Opik
- Shows improved completion rate vs static scheduling
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.execution_tracker import execution_tracker


class User:
    """Simulated user with realistic completion probabilities."""
    def __init__(self, name, completion_probability=0.7, reschedule_boost=0.15):
        self.name = name
        self.base_completion = completion_probability
        self.reschedule_boost = reschedule_boost
        self.tasks_completed = []
        self.tasks_missed = []
        self.tasks_rescheduled = []
    
    def attempt_task(self, task, was_rescheduled=False):
        """Simulate attempting a task."""
        import random
        prob = self.base_completion
        if was_rescheduled:
            prob += self.reschedule_boost  # Rescheduled tasks have higher completion
        
        completed = random.random() < prob
        if completed:
            self.tasks_completed.append(task)
        else:
            self.tasks_missed.append(task)
        
        return completed


async def run_static_schedule_simulation(weeks=4):
    """
    Simulates a user with STATIC scheduling (no adaptive rescheduling).
    Like a traditional calendar app.
    """
    print("=" * 60)
    print("SIMULATION 1: Static Schedule (Traditional Calendar)")
    print("=" * 60)
    
    user = User(name="Static User", completion_probability=0.65)
    goal_id = "spanish-001"
    user_id = "user-static"
    
    # Schedule: Mon/Wed/Fri for 4 weeks
    sessions_per_week = 3
    total_sessions = weeks * sessions_per_week
    
    start_date = datetime.now()
    
    for week in range(weeks):
        for day_offset in [0, 2, 4]:  # Mon, Wed, Fri
            session_date = start_date + timedelta(weeks=week, days=day_offset)
            task_id = f"task-static-{week}-{day_offset}"
            task_name = f"Spanish Practice - Week {week+1}"
            
            completed = user.attempt_task({
                "id": task_id,
                "name": task_name,
                "date": session_date.strftime("%Y-%m-%d")
            }, was_rescheduled=False)
            
            if completed:
                execution_tracker.log_task_completion(
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    goal_id=goal_id,
                    scheduled_date=session_date.strftime("%Y-%m-%d"),
                    completed_date=session_date.strftime("%Y-%m-%d"),
                    was_rescheduled=False
                )
            else:
                execution_tracker.log_task_missed(
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    goal_id=goal_id,
                    scheduled_date=session_date.strftime("%Y-%m-%d"),
                    missed_date=session_date.strftime("%Y-%m-%d")
                )
    
    metrics = execution_tracker.calculate_completion_metrics([
        {"status": "completed" if t in user.tasks_completed else "missed", "completed_on_time": True, "was_rescheduled": False}
        for t in (user.tasks_completed + user.tasks_missed)
    ])
    
    print(f"\n📊 Results (Static Schedule):")
    print(f"   Total Sessions: {total_sessions}")
    print(f"   Completed: {len(user.tasks_completed)}")
    print(f"   Missed: {len(user.tasks_missed)}")
    print(f"   Completion Rate: {metrics['completion_rate']}%")
    print()
    
    return metrics


async def run_adaptive_schedule_simulation(weeks=4):
    """
    Simulates a user with ADAPTIVE scheduling (Goalie's approach).
    When a session is missed, it's automatically rescheduled.
    """
    print("=" * 60)
    print("SIMULATION 2: Adaptive Schedule (Goalie AI)")
    print("=" * 60)
    
    user = User(name="Adaptive User", completion_probability=0.65, reschedule_boost=0.20)
    goal_id = "spanish-002"
    user_id = "user-adaptive"
    
    sessions_per_week = 3
    total_sessions = weeks * sessions_per_week
    
    start_date = datetime.now()
    
    all_tasks = []
    
    for week in range(weeks):
        for day_offset in [0, 2, 4]:  # Mon, Wed, Fri
            session_date = start_date + timedelta(weeks=week, days=day_offset)
            task_id = f"task-adaptive-{week}-{day_offset}"
            task_name = f"Spanish Practice - Week {week+1}"
            
            task = {
                "id": task_id,
                "name": task_name,
                "date": session_date.strftime("%Y-%m-%d"),
                "was_rescheduled": False
            }
            
            # Attempt original schedule
            completed = user.attempt_task(task, was_rescheduled=False)
            
            if completed:
                execution_tracker.log_task_completion(
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    goal_id=goal_id,
                    scheduled_date=session_date.strftime("%Y-%m-%d"),
                    completed_date=session_date.strftime("%Y-%m-%d"),
                    was_rescheduled=False
                )
                all_tasks.append({"status": "completed", "completed_on_time": True, "was_rescheduled": False})
            else:
                # MISSED - Log it
                execution_tracker.log_task_missed(
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    goal_id=goal_id,
                    scheduled_date=session_date.strftime("%Y-%m-%d"),
                    missed_date=session_date.strftime("%Y-%m-%d")
                )
                
                # ADAPTIVE RESCHEDULING - Goalie reschedules to next available slot
                new_date = session_date + timedelta(days=1)
                execution_tracker.log_reschedule(
                    task_id=task_id,
                    task_name=task_name,
                    user_id=user_id,
                    goal_id=goal_id,
                    original_date=session_date.strftime("%Y-%m-%d"),
                    new_date=new_date.strftime("%Y-%m-%d"),
                    reason="user_missed_session"
                )
                
                # Attempt rescheduled task (with boost)
                rescheduled_task = {**task, "date": new_date.strftime("%Y-%m-%d"), "was_rescheduled": True}
                completed_after_reschedule = user.attempt_task(rescheduled_task, was_rescheduled=True)
                
                if completed_after_reschedule:
                    execution_tracker.log_task_completion(
                        task_id=task_id,
                        task_name=task_name + " (Rescheduled)",
                        user_id=user_id,
                        goal_id=goal_id,
                        scheduled_date=new_date.strftime("%Y-%m-%d"),
                        completed_date=new_date.strftime("%Y-%m-%d"),
                        was_rescheduled=True
                    )
                    all_tasks.append({"status": "completed", "completed_on_time": False, "was_rescheduled": True})
                    user.tasks_rescheduled.append(rescheduled_task)
                else:
                    all_tasks.append({"status": "missed", "completed_on_time": False, "was_rescheduled": True})
    
    metrics = execution_tracker.calculate_completion_metrics(all_tasks)
    
    print(f"\n📊 Results (Adaptive Schedule):")
    print(f"   Total Sessions: {total_sessions}")
    print(f"   Completed: {metrics['completed_tasks']}")
    print(f"   Rescheduled: {metrics['rescheduled_tasks']}")
    print(f"   Completion Rate: {metrics['completion_rate']}%")
    print(f"   Reschedule Success Rate: {metrics['reschedule_success_rate']}%")
    print()
    
    return metrics


async def main():
    print("\n🎯 GOALIE AI - ADAPTIVE SCHEDULING EXPERIMENT")
    print("Demonstrating execution accountability with Opik\n")
    
    # Run both simulations
    static_metrics = await run_static_schedule_simulation(weeks=4)
    await asyncio.sleep(1)
    adaptive_metrics = await run_adaptive_schedule_simulation(weeks=4)
    
    # Compare results
    print("=" * 60)
    print("📈 COMPARISON: Static vs. Adaptive Scheduling")
    print("=" * 60)
    print(f"\nStatic Schedule:   {static_metrics['completion_rate']}% completion")
    print(f"Adaptive Schedule: {adaptive_metrics['completion_rate']}% completion")
    
    improvement = adaptive_metrics['completion_rate'] - static_metrics['completion_rate']
    print(f"\n✨ Improvement: +{improvement}% with adaptive rescheduling")
    print(f"\n💡 Insight: Goalie's adaptive scheduling helps users complete {improvement}% more tasks")
    print("   by automatically rescheduling missed sessions to optimal times.")
    
    print("\n🔍 View detailed traces and metrics in your Opik dashboard:")
    print("   https://www.comet.com/opik/")
    print()


if __name__ == "__main__":
    asyncio.run(main())
