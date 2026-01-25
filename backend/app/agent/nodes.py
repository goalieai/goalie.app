from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage

from app.core.config import settings
from app.agent.state import AgentState

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.google_api_key
)

SYSTEM_PROMPT = """You are Goally, an AI assistant that helps people achieve their New Year's resolutions.

Your role is to:
1. Understand the user's goals and resolutions
2. Break down large goals into actionable steps
3. Provide motivation and accountability
4. Suggest practical strategies for success
5. Track progress and celebrate wins

Be encouraging, practical, and specific in your advice. Focus on sustainable habits rather than quick fixes."""


async def coach_node(state: AgentState) -> dict:
    """Main coaching node that responds to user messages."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}
