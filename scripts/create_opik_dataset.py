
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opik import Opik
from app.core.config import settings

def create_dataset():
    if not settings.opik_api_key:
        print("Opik API Key not set. Skipping dataset creation.")
        return

    client = Opik(api_key=settings.opik_api_key)
    
    dataset_name = "goalie_weekly_planning_v1"
    
    # Check if exists (naive check or just try logic)
    # client.get_dataset(name=dataset_name) might raise or return None
    
    try:
        # Create or get dataset
        dataset = client.get_or_create_dataset(name=dataset_name, description="20 realistic weekly planning scenarios")
        print(f"Dataset '{dataset_name}' ready.")
    except Exception as e:
        print(f"Error creating dataset: {e}")
        return

    # 20 Scenarios
    scenarios = [
        # Professional / Career
        {"goal": "Launch my portfolio website", "role": "Designer", "anchors": ["Morning", "After Lunch", "Night"]},
        {"goal": "Prepare for Python certification", "role": "Developer", "anchors": ["Early Morning", "Evening"]},
        {"goal": "Write 3 blog posts about AI", "role": "Content Creator", "anchors": ["Coffee Break", "Afternoon"]},
        {"goal": "Update LinkedIn profile and CV", "role": "Job Seeker", "anchors": ["Midday", "Evening"]},
        {"goal": "Prepare quarterly team presentation", "role": "Manager", "anchors": ["Morning", "Lunch"]},
        
        # Health / Fitness
        {"goal": "Run 5k without stopping", "role": "Beginner Runner", "anchors": ["Morning", "Evening"]},
        {"goal": "Meal prep for the whole week", "role": "Busy Parent", "anchors": ["Sunday Night", "Wednesday Night"]},
        {"goal": "Start a yoga routine", "role": "Office Worker", "anchors": ["Before Work", "Before Bed"]},
        {"goal": "Drink 2L of water daily", "role": "Student", "anchors": ["Every Hour", "Meals"]},
        {"goal": "Lose 2 lbs this week", "role": "Accountant", "anchors": ["Morning Cardio", "Lunch Walk"]},

        # Learning / Hobby
        {"goal": "Learn basic Spanish phrases", "role": "Traveler", "anchors": ["Commute", "Evening"]},
        {"goal": "Practice guitar 20 mins daily", "role": "Musician", "anchors": ["After Work", "Weekend"]},
        {"goal": "Read one book this week", "role": "Bookworm", "anchors": ["Bedtime", "Commute"]},
        {"goal": "Learn to make sourdough bread", "role": "Baker", "anchors": ["Weekend Morning", "Evening check"]},
        {"goal": "Start a small vegetable garden", "role": "Gardener", "anchors": ["Weekend", "After Work"]},
        
        # Wellness / Mindfulness
        {"goal": "Meditate 10 mins daily", "role": "Stressed Exec", "anchors": ["Morning", "Night"]},
        {"goal": "Digital detox after 8pm", "role": "Tech Worker", "anchors": ["Evening"]},
        {"goal": "Journal every evening", "role": "Writer", "anchors": ["Bedtime"]},
        {"goal": "Call one family member daily", "role": "Expat", "anchors": ["Lunch Break"]},
        {"goal": "Organize home office", "role": "Remote Worker", "anchors": ["Weekend", "Friday Afternoon"]}
    ]
    
    # Insert items
    items = []
    for s in scenarios:
        items.append({
            "input": s,
            "expected_output": {"type": "plan", "criteria": "balanced schedule"}
        })
        
    try:
        dataset.insert(items)
        print(f"Successfully inserted {len(items)} items into {dataset_name}.")
    except Exception as e:
        print(f"Error inserting items: {e}")

if __name__ == "__main__":
    create_dataset()
