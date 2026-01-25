from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.agent.state import AgentState
from app.agent.nodes import coach_node

# Build the agent graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("coach", coach_node)

# Set entry point
workflow.set_entry_point("coach")

# Add edges
workflow.add_edge("coach", END)

# Compile the graph
graph = workflow.compile()


async def run_agent(message: str) -> str:
    """Run the agent with a user message."""
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_goal": ""
    }

    result = await graph.ainvoke(initial_state)

    # Extract the last AI message
    ai_messages = [m for m in result["messages"] if m.type == "ai"]
    if ai_messages:
        return ai_messages[-1].content
    return "I'm here to help you achieve your goals!"
