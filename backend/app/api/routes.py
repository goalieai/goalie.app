from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback

from app.agent.graph import run_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the Goaly agent."""
    try:
        response = await run_agent(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        print(f"Chat error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
