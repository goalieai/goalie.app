Create a new task for the user in their task list.

## When to Use

- User explicitly asks to create/add a task
- User mentions something they need to do today or in the future
- User describes an action they want to track

## Examples

User: "Add a task to study Spanish"
→ create_task(action="Study Spanish")

User: "Remind me to call mom at 5pm"  
→ create_task(action="Call mom", time="5:00 PM")

User: "I need to buy milk tomorrow morning"
→ create_task(action="Buy milk", time="Tomorrow morning", energy="low")
