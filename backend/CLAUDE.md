# Backend Guide - Goally

## Overview

Goally's backend is a specialized AI agent service built with **FastAPI** and **LangGraph**, using **Google Gemini** as the LLM. It features a sophisticated planning pipeline and an orchestrator to manage user intent, state, and goal execution.

## Tech Stack

- **Framework**: FastAPI (Async)
- **Agent Orchestration**: LangGraph + LangChain
- **LLM**: Google Gemini (`gemini-3-flash-preview`) via `langchain-google-genai`
- **Database**: Supabase (PostgreSQL via `supabase-py`)
- **Observability**: Comet Opik (Traces all LangChain/LangGraph calls)
- **Validation**: Pydantic v2

## Architecture

```
backend/
├── app/
│   ├── main.py           # Entry point, CORS, Opik configuration
│   ├── api/
│   │   ├── routes.py     # Endpoints: /chat, /plan, /tasks, /goals, /profile
│   │   └── schemas.py    # Pydantic models for API request/response
│   ├── agent/
│   │   ├── graph.py      # StateGraph definitions (Orchestrator & Planning)
│   │   ├── nodes.py      # Logic for each graph node (intent, casual, coaching)
│   │   ├── state.py      # AgentState TypedDict definition
│   │   ├── schema.py     # Pydantic schemas (UserProfile, ProjectPlan, MicroTask)
│   │   ├── memory.py     # Session persistence (HybridSessionStore)
│   │   ├── prompts/      # Markdown prompt templates
│   │   │   ├── casual.md
│   │   │   ├── coaching.md
│   │   │   └── orchestrator.md
│   │   └── tools/        # LangChain tools
│   │       ├── crud.py   # create_task, create_goal, complete_task
│   │       └── descriptions/  # Tool description markdown files
│   └── core/
│       ├── config.py     # Environment variables (pydantic-settings)
│       └── supabase.py   # Supabase client singleton
├── scripts/              # Utility scripts
└── requirements.txt
```

## Database Schema (Supabase)

### Tables

**`profiles`**
| Column | Type | Description |
|--------|------|-------------|
| id | uuid (PK) | User ID (from Supabase Auth) |
| first_name | text | User's display name |
| preferences | jsonb | `{anchors: [], role: "..."}` |
| updated_at | timestamp | Last update |

**`goals`**
| Column | Type | Description |
|--------|------|-------------|
| id | uuid (PK) | Goal ID |
| user_id | uuid (FK) | Owner |
| session_id | uuid | Session that created it |
| title | text | Goal title |
| description | text | SMART goal summary |
| emoji | text | Display emoji |
| status | text | `active`, `achieved`, `archived` |
| target_date | timestamp | Optional deadline |
| created_at | timestamp | Creation time |

**`tasks`**
| Column | Type | Description |
|--------|------|-------------|
| id | uuid (PK) | Task ID |
| user_id | uuid (FK) | Owner |
| goal_id | uuid (FK) | Parent goal (optional) |
| task_name | text | Task description |
| estimated_minutes | int | Time estimate (5-20) |
| energy_required | text | `high`, `medium`, `low` |
| assigned_anchor | text | Daily anchor (e.g., "Morning Coffee") |
| rationale | text | Why this anchor fits |
| status | text | `pending`, `in_progress`, `completed` |
| scheduled_text | text | Human-readable schedule |
| created_at | timestamp | Creation time |

**`sessions`** / **`messages`** - Conversation persistence

## Key Workflows

### 1. Orchestrator (`app/agent/graph.py`)

The unified `/api/chat` endpoint uses a `StateGraph` to route messages:

```
User Message -> Intent Router -> [casual | coaching | planning_pipeline]
                                        |
                                        v
                              Planning Response -> Actions
```

**Intent Types:**
- `casual` - Greetings, small talk, general questions
- `planning` - Create new goals/plans (triggers full pipeline)
- `coaching` - Progress review, motivation, setback handling
- `modify` - Adjust existing plans (routes to coaching)

### 2. Planning Pipeline

Linear graph for goal decomposition:

```
Smart Refiner -> Task Splitter -> Context Matcher
     |                |                |
     v                v                v
 SMART Goal      3-7 Tasks      MicroTasks with Anchors
```

**Output:** `ProjectPlan` with tasks assigned to user's daily anchors.

### 3. Session Memory (`app/agent/memory.py`)

**HybridSessionStore:**
- Guest users: In-memory storage
- Authenticated users: Supabase persistence

**Persisted data:**
- Conversation history (messages table)
- Active goals and tasks
- User profile from `profiles` table

## Agent Tools (`app/agent/tools/crud.py`)

Tools are LangChain `@tool` decorated functions that return action payloads:

| Tool | Parameters | Action Type |
|------|------------|-------------|
| `create_task` | action, time, energy | `create_task` |
| `create_goal` | title, description, emoji | `create_goal` |
| `complete_task` | task_id, task_name | `complete_task` |

**Action Response Format:**
```python
{
    "type": "create_goal",
    "data": {"title": "...", "description": "...", "emoji": "🎯"}
}
```

Actions are returned in the `/api/chat` response for frontend processing.

## API Endpoints

### Chat & Agent
- `POST /api/chat` - Unified endpoint with orchestrator
  - Request: `{message, session_id?, user_id?, user_profile?}`
  - Response: `{session_id, intent_detected, response, plan?, actions[]}`

### Resources (CRUD)
- `GET/POST /api/tasks?user_id=` - List/create tasks
- `PUT/DELETE /api/tasks/{id}?user_id=` - Update/delete task
- `GET/POST /api/goals?user_id=` - List/create goals
- `PUT/DELETE /api/goals/{id}?user_id=` - Update/delete goal
- `GET/PUT /api/profile/{id}` - User profile

## Commands

```bash
# Development
uvicorn app.main:app --reload --port 8000

# With specific host (for network access)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon key |
| `OPIK_API_KEY` | No | Comet Opik tracing |
| `LLM_PRIMARY_MODEL` | No | Default: `gemini-3-flash-preview` |
| `LLM_FALLBACK_MODEL` | No | Default: `gpt-4o-mini` |

## Code Conventions

- **Async/Await**: All route handlers and database calls
- **Pydantic**: Models for all structured data
- **LangGraph**: Separate graph definition (`graph.py`) from node logic (`nodes.py`)
- **Prompts**: Store in `prompts/*.md`, load with `load_prompt()`
- **Tools**: Define in `tools/crud.py`, descriptions in `tools/descriptions/*.md`
- **Error Handling**: Wrap in `try/except`, raise `HTTPException`

## Future Enhancements (Planned)

- [ ] Google Calendar integration for context
- [ ] User confirmation before DB writes
- [ ] More conversational flow (gather info before creating tasks)
- [ ] Webhook support for external integrations
