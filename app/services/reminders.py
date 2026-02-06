"""
Email Reminder Service using Resend

Sends task reminders to users when tasks are due.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo
import resend
from app.core.config import settings
from app.core.supabase import supabase


# Initialize Resend (will be set from settings)
def send_task_reminder(
    user_email: str,
    task_name: str,
    scheduled_time: str,
    task_id: str
) -> bool:
    """
    Send a task reminder email.
    
    Args:
        user_email: User's email address
        task_name: Name of the task
        scheduled_time: When the task is scheduled (human-readable)
        task_id: Task ID for tracking
    
    Returns:
        True if email sent successfully
    """
    if not settings.resend_api_key:
        print("[REMINDERS] Resend API key not configured")
        return False
    
    try:
        # Set API key
        resend.api_key = settings.resend_api_key
        
        # Create email content
        subject = f"⏰ Reminder: {task_name}"
        
        html_content = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #10b981; margin: 0; font-size: 24px;">🥅 Goalie AI</h1>
                </div>
                
                <h2 style="color: #1f2937; margin-top: 0;">Time for Your Task!</h2>
                
                <div style="background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #1f2937;">
                        {task_name}
                    </p>
                    <p style="margin: 8px 0 0 0; color: #6b7280; font-size: 14px;">
                        Scheduled for: {scheduled_time}
                    </p>
                </div>
                
                <p style="color: #4b5563; line-height: 1.6;">
                    Ready to make progress on your goals? This task should only take 5-20 minutes.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.frontend_url or 'http://localhost:5173'}" 
                       style="display: inline-block; background-color: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        Open Goalie Dashboard
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                    You're receiving this because you scheduled this task with Goalie AI.<br>
                    Want to reschedule? Just click "Re-plan" in your dashboard.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Send email
        params = {
            "from": settings.resend_from_email,
            "to": [user_email],
            "subject": subject,
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        
        print(f"[REMINDERS] Sent reminder to {user_email} for task: {task_name} | Email ID: {response.get('id')}")
        return True
        
    except Exception as e:
        print(f"[REMINDERS] Failed to send email: {e}")
        return False


async def check_and_send_reminders(
    minutes_before: int = 15,
    timezone: str = "America/Los_Angeles"
) -> int:
    """
    Check for upcoming tasks and send reminders.
    
    Args:
        minutes_before: Send reminder X minutes before task is due
        timezone: User timezone
    
    Returns:
        Number of reminders sent
    """
    if not supabase:
        print("[REMINDERS] Supabase not available")
        return 0
    
    try:
        now = datetime.now(ZoneInfo(timezone))
        target_time = now + timedelta(minutes=minutes_before)
        
        # Find tasks scheduled around the target time (±2 minute window)
        start_window = target_time - timedelta(minutes=2)
        end_window = target_time + timedelta(minutes=2)
        
        # Query tasks
        response = supabase.table("tasks").select(
            "id, task_name, scheduled_at, scheduled_text, user_id, status, reminder_sent"
        ).execute()
        
        tasks = response.data or []
        reminders_sent = 0
        
        for task in tasks:
            # Skip if already completed or reminder already sent
            if task.get("status") == "completed":
                continue
            if task.get("reminder_sent"):
                continue
            
            scheduled_at = task.get("scheduled_at")
            if not scheduled_at:
                continue
            
            # Parse scheduled time
            task_time = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            
            # Check if task is in reminder window
            if start_window <= task_time <= end_window:
                # Get user email
                user_id = task.get("user_id")
                
                # Query user profile for email
                user_response = supabase.table("profiles").select("email").eq("id", user_id).execute()
                
                if not user_response.data:
                    print(f"[REMINDERS] No email found for user {user_id}")
                    continue
                
                user_email = user_response.data[0].get("email")
                if not user_email:
                    continue
                
                # Send reminder
                success = send_task_reminder(
                    user_email=user_email,
                    task_name=task.get("task_name", "Your task"),
                    scheduled_time=task.get("scheduled_text", task_time.strftime("%I:%M %p")),
                    task_id=task["id"]
                )
                
                if success:
                    # Mark reminder as sent
                    supabase.table("tasks").update(
                        {"reminder_sent": True}
                    ).eq("id", task["id"]).execute()
                    
                    reminders_sent += 1
        
        if reminders_sent > 0:
            print(f"[REMINDERS] Sent {reminders_sent} reminders")
        
        return reminders_sent
        
    except Exception as e:
        print(f"[REMINDERS] Error checking reminders: {e}")
        return 0


async def test_reminder(user_email: str) -> bool:
    """
    Send a test reminder to verify email configuration.
    
    Args:
        user_email: Email to send test to
    
    Returns:
        True if successful
    """
    return send_task_reminder(
        user_email=user_email,
        task_name="Test Task - Practice Spanish",
        scheduled_time="Now",
        task_id="test-123"
    )
