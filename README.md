# Goally

AI-powered agent to help you achieve your New Year's resolutions through intelligent micro-task management and motivational coaching.

Built for the [Comet Resolution V2 Hackathon](https://www.encodeclub.com/programmes/comet-resolution-v2-hackathon) by Encode Club.

## Features

- **Socratic Goal Refinement** — Agent asks clarifying questions to transform vague ideas into SMART goals
- **Smart Task Breakdown** — Goals broken into 3-7 atomic micro-tasks (5-20 min each)
- **Coach vs Secretary** — Beginners get specific curriculum (Week 0 philosophy); experts get optimization tasks
- **Human-in-the-Loop** — Plans are staged for review before saving; users can modify or confirm
- **Anchor-Based Scheduling** — Tasks matched to daily routines (Morning Coffee, Lunch Break, End of Day) by energy level
- **Real-Time Streaming** — SSE pipeline shows progress as the agent thinks (Intent → Smart Goal → Tasks → Schedule → Plan)
- **AI Coach Chat** — Conversational support for motivation, setbacks, and progress review
- **ADHD-Friendly Dashboard** — Three sections (NOW / NEXT / ACHIEVED), large touch targets, medal celebrations
- **Guest & Auth Modes** — Use instantly without signup (localStorage), or sign in for Supabase persistence
- **Progress Visualization** — Circular spiral tracker with completion metrics

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19 + TypeScript 5.9 + Vite 7 |
| **UI** | Tailwind CSS 3.4 + Radix UI (49 primitives) + Lucide Icons |
| **Data Fetching** | TanStack React Query 5 + React Router 7 |
| **Backend** | FastAPI + LangGraph + LangChain |
| **LLM (Primary)** | Google Gemini (`gemini-3-flash-preview`, temp=0.0) |
| **LLM (Fallback)** | Ollama (`llama3.2:1b` local) |
| **Database & Auth** | Supabase (PostgreSQL + Auth + RLS) |
| **Streaming** | SSE via sse-starlette |
| **Observability** | Comet Opik |
| **Frontend Hosting** | Vercel |
| **Backend Hosting** | Heroku (Procfile) / Google Cloud Run (CI/CD) |

## Getting Started

### Prerequisites

- Node.js 20+ / pnpm
- Python 3.11+
- Google Gemini API key
- Supabase project (optional — guest mode works without it)
- Comet Opik account (optional)

### Backend

```bash
# From project root
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

Create `.env` at project root:
```env
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_key
OPIK_API_KEY=your_opik_api_key          # optional
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev  # http://localhost:5173
```

Create `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_url         # optional — guest mode if missing
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key  # optional — guest mode if missing
```

## Architecture

### Project Structure

```
goalie.app/
├── app/                            # FastAPI + LangGraph backend
│   ├── main.py                     # App entry: CORS, Opik, routes
│   ├── api/
│   │   ├── routes.py               # REST + SSE streaming endpoints
│   │   └── schemas.py              # API request/response models
│   ├── agent/
│   │   ├── graph.py                # Orchestrator + Planning subgraph (LangGraph)
│   │   ├── nodes.py                # All node implementations + LLM helpers
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── schema.py               # Domain models (Intent, SmartGoal, Plan, etc.)
│   │   ├── prompts.py              # Prompt template loader
│   │   ├── memory.py               # Session stores (Memory, Supabase, Hybrid)
│   │   ├── prompts/                # 8 markdown prompt templates
│   │   └── tools/                  # LangChain tools (create_task, create_goal, complete_task)
│   └── core/
│       ├── config.py               # Settings (env vars, LLM config, rate limits)
│       └── supabase.py             # Supabase client init
├── frontend/                       # React 19 SPA
│   └── src/
│       ├── pages/                  # Index (dashboard), NotFound
│       ├── components/             # 15 business components + 49 Radix UI primitives
│       ├── contexts/               # AuthContext (magic link + guest mode)
│       ├── hooks/                  # useStreamingChat, useTasks, useGoals
│       ├── services/               # API client + unified store factory
│       ├── lib/                    # utils (cn), Supabase client
│       └── types/                  # TypeScript interfaces
├── docs/                           # Architecture docs
├── workflows/                      # CI/CD (backend.yml, frontend.yml, preview.yml)
├── supabase/                       # DB migrations
├── scripts/                        # Utility scripts
├── Procfile                        # Heroku deployment
├── vercel.json                     # Vercel SPA rewrites
├── requirements.txt                # Python dependencies
└── runtime.txt                     # Python 3.11.9
```

### Agent Workflow

```
User Message
  │
  ▼
Intent Router ─── classifies intent ───┐
  │                                     │
  ├─→ casual ─────────────────────────→ Response
  ├─→ coaching ───────────────────────→ Response + Actions
  ├─→ confirm (HITL) ────────────────→ Commit staged plan → Actions
  ├─→ modify ─────────────────────────→ Update staging plan
  └─→ planning ──→ Planning Pipeline
                        │
                        ▼
                   Smart Refiner (Socratic Gatekeeper)
                        │
                   ┌────┴────┐
                   │         │
              needs info   ready
                   │         │
                   ▼         ▼
              Ask user    Task Splitter (Coach vs Secretary)
              (save ctx)      │
                              ▼
                         Context Matcher (energy → anchors)
                              │
                              ▼
                         Planning Response (HITL: stage plan, ask confirmation)
```

**Intent types:** `casual` | `planning` | `planning_continuation` | `coaching` | `modify` | `confirm`

### Key Patterns

**Socratic Gatekeeper** — The Smart Refiner detects missing information (ability level, time horizon, specificity) and asks one clarifying question at a time, saving context across turns. A safety counter prevents infinite loops.

**Human-in-the-Loop (HITL)** — Generated plans are staged (not saved). The agent presents the plan with a "Shall I save this?" CTA. Only on explicit confirmation does the plan commit to active storage and create tasks.

**Coach vs Secretary** — Context tags (`beginner`/`expert`, `sedentary`/`active`) determine the approach. Beginners get specific curriculum with Week 0 philosophy (environment design, identity building, habit stacking). Experts get higher-level optimization tasks.

**SSE Streaming** — `/api/chat/stream` emits real-time events (`status`, `progress`, `clarification`, `complete`, `error`) so the frontend can show pipeline progress and prevent timeout on long-running planning operations.

**Hybrid Session Store** — Authenticated users get Supabase persistence. Anonymous users get in-memory sessions. The frontend mirrors this with a unified store factory (`getStore(userId)`) that switches between localStorage and Supabase.

**LLM Fallback** — Primary model (`gemini-3-flash-preview`, temp=0.0) with automatic fallback to Ollama (`llama3.2:1b`) on rate limits (HTTP 429) or parse errors. Conversational calls use temp=0.7.

### Database Schema (Supabase)

| Table | Purpose |
|-------|---------|
| `profiles` | User preferences, daily anchors, display name |
| `goals` | Goals with emoji, status (active/achieved/archived), target date |
| `tasks` | Micro-tasks with time estimates, energy level, assigned anchor, rationale |
| `sessions` | Conversation sessions with last_active tracking |
| `messages` | Chat history with role, content, metadata (tokens, model, tool_calls) |

All tables use `user_id` for Row-Level Security (RLS).

## API Endpoints

### Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Unified chat with session support |
| POST | `/api/chat/stream` | Streaming chat via SSE (real-time pipeline progress) |
| POST | `/api/chat/legacy` | Legacy chat endpoint (backwards compat) |
| POST | `/api/plan` | Direct planning pipeline (no orchestrator) |

### Resources

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/tasks` | List / create tasks |
| PUT/DELETE | `/api/tasks/{id}` | Update / delete task |
| GET/POST | `/api/goals` | List / create goals |
| PUT/DELETE | `/api/goals/{id}` | Update / delete goal |
| GET/PUT | `/api/profile/{user_id}` | Get / update user profile |
| GET | `/api/health` | Health check |

## Frontend Dashboard

```
┌──────────────────────────────────────┬──────────────────┐
│  DashboardHeader (greeting + auth)   │                  │
├──────────────────────────────────────┤   AgentChat      │
│  YOUR GOALIE (NOW)                   │   (sidebar)      │
│  - Current goal + task               │                  │
│  - Done / Re-plan buttons            │  - SSE streaming │
│  - ProgressSpiral                    │  - Pipeline viz  │
├──────────────────────────────────────┤  - Plan preview  │
│  NEXT                                │  - HITL confirm  │
│  - Upcoming task grid                │  - Clarification │
│  - Add Task                          │                  │
├──────────────────────────────────────┤                  │
│  ACHIEVED                            │                  │
│  - Medal tasks + celebrations        │                  │
└──────────────────────────────────────┴──────────────────┘
                                    [Chat Toggle FAB]
```

### Design System

- **Primary (Orange):** `hsl(25 95% 53%)` — Energy, motivation
- **Secondary (Cream):** `hsl(35 40% 94%)` — Calm backgrounds
- **Success (Green):** `hsl(140 50% 45%)` — Completed tasks
- **Fonts:** Nunito (body), Space Grotesk (display)
- **UX:** Miller's Law (3 sections), Fitts' Law (56-64px buttons), micro-tasks with time estimates

## Deployment

### Frontend (Vercel)

Auto-deploys on push to `main`. SPA routing configured via `vercel.json`. Set `VITE_*` environment variables in Vercel dashboard.

### Backend (Heroku / Cloud Run)

**Heroku:** Configured via `Procfile` and `runtime.txt` (Python 3.11.9).

**Cloud Run:** CI/CD in `workflows/backend.yml` deploys to `us-central1` on push to `main`. Requires GCP workload identity and environment variables.

## Observability

This project uses [Comet Opik](https://www.comet.com/site/products/opik/) for LLM observability. All LangGraph operations are automatically traced when `OPIK_API_KEY` is configured, allowing you to debug agent reasoning, tool usage, and latency. Initialization is optional and gracefully skipped if unconfigured.

## License

MIT
