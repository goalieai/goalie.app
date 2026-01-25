# Backend - FastAPI + LangGraph

Python backend with FastAPI, LangGraph for agent orchestration, and Gemini as the LLM.

## Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── api/              # API route handlers
│   │   └── routes.py
│   ├── agent/            # LangGraph agent
│   │   ├── graph.py      # Agent workflow definition
│   │   ├── nodes.py      # Agent nodes/actions
│   │   └── state.py      # Agent state schema
│   └── core/
│       └── config.py     # Configuration/env vars
```

## Commands

```bash
# Development
uvicorn app.main:app --reload

# With specific port
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

Create a `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key
OPIK_API_KEY=your_opik_api_key
```

## Key Dependencies

- **FastAPI:** Web framework
- **LangChain + LangGraph:** Agent orchestration
- **langchain-google-genai:** Gemini integration
- **Opik:** Observability and tracing

## API Endpoints

- `POST /api/chat` - Send message to agent
- `GET /api/health` - Health check

## Opik Integration

Opik tracer is configured in `app/main.py` to automatically trace all LangChain/LangGraph operations.
