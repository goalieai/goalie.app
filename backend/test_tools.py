import asyncio
import sys
from uuid import uuid4
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from app.agent.graph import run_orchestrator
from app.agent.schema import UserProfile

async def test_crud_detection():
    print("\n--- Testing CRUD Tool Detection ---")
    
    session_id = str(uuid4()) # Fresh session
    user_id = str(uuid4())    # Fresh user
    user_profile = UserProfile(name="Jose")
    
    test_cases = [
        "Hola Goally!",
        "Añade Comprar leche a mis tareas",
    ]
    
    for message in test_cases:
        print(f"\nUser: {message}")
        result = await run_orchestrator(message, session_id, user_id, user_profile)
        print(f"Intent detected: {result['intent_detected']}")
        print(f"Actions: {result.get('actions', [])}")

if __name__ == "__main__":
    asyncio.run(test_crud_detection())
