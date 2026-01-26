# Backend Guide - Goally

## Overview

Goally's backend is a specialized AI agent service built with **FastAPI** and **LangGraph**, using **Google Gemini** as the LLM. It features a sophisticated planning pipeline and an orchestrator to manage user intent, state, and goal execution.

## Tech Stack

- **Framework**: FastAPI (Async)
- **Agent Orchestration**: LangGraph + LangChain
- **LLM**: Google Gemini (`gemini-2.5-flash` recommended) -> `langchain-google-genai`
- **Database**: Supabase (via `supabase-py`)
- **Observability**: Comet Opik (Traces all LangChain/LangGraph calls)
- **Validation**: Pydantic v2

## Architecture

```
backend/
├── app/
│   ├── main.py           # Entry point, CORS, Opik configuration
│   ├── api/
│   │   ├── routes.py     # Endpoints: /chat (Unified), /plan, /tasks, /goals
│   │   └── schemas.py    # Pydantic models for API request/response
│   ├── agent/
│   │   ├── graph.py      # StateGraph definitions (Orchestrator & Planning)
│   │   ├── nodes.py      # Logic for each graph node (intent, casual, coaching)
│   │   ├── state.py      # AgentState TypedDict definition
│   │   ├── memory.py     # Session persistence logic
│   │   └── tools/        # Custom tools
│   └── core/
│       ├── config.py     # Environment variables (pydantic-settings)
│       └── supabase.py   # Supabase client singleton
├── scripts/              # Utility scripts (e.g., init_user.py)
├── verify_structured_output.py # Test script for Gemini structured output
└── requirements.txt
```

## Key Workflows

### 1. Orchestrator (`app/agent/graph.py`)
The integrated chat handler (`/api/chat`) uses a `StateGraph` to route messages:
- **Intent Router**: Classifies input as `casual`, `planning`, or `coaching`.
- **Planning Pipeline**: Subgraph for breaking down goals into micro-tasks.
- **Coaching**: General advice and motivation.
- **Session Memory**: Persists conversation history and state in `session_store` (in-memory + syncing).

### 2. Planning Pipeline
Strict linear graph for goal creation:
`Smart Refiner` -> `Task Splitter` -> `Context Matcher` (Assigns anchors)

## Commands

### Development
```bash
# Run server with hot reload
uvicorn app.main:app --reload

# Run on specific port
uvicorn app.main:app --reload --port 8000
```

### Testing & Verification
```bash
# Verify LLM structured output capabilities
python verify_structured_output.py

# Test agent intent routing and CRUD tools
python test_tools.py
```

## Environment Variables (.env)

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Required for Gemini models |
| `OPIK_API_KEY` | Optional. Enables Comet Opik tracing |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service_role key |

## API Endpoints

### Chat & Agent
- `POST /api/chat`: Unified endpoint. Handles session, routing, and execution. Returns `plan`, `response`, `actions`.
- `POST /api/plan`: (Legacy/Direct) Runs just the planning pipeline.

### Resources (CRUD)
- `GET/POST /api/tasks`: Manage micro-tasks.
- `GET/POST /api/goals`: Manage high-level goals.
- `GET/PUT /api/profile/{id}`: Manage user profile (anchors, name).

## Code Style & Conventions

- **Async/Await**: All route handlers and database calls must be async.
- **Pydantic**: Use Pydantic models for all structured data (schemas, state).
- **LangGraph**: separate graph definition (`graph.py`) from node logic (`nodes.py`).
- **Error Handling**: Wrap logic in `try/except` and raise `HTTPException`.
- **Observability**: Do not suppress Opik errors if key is missing (logs warning).
