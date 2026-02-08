# Goally

AI-powered agent to help you achieve your New Year's resolutions through intelligent micro-task management and motivational coaching.

Built for the [Comet Resolution V2 Hackathon](https://www.encodeclub.com/programmes/comet-resolution-v2-hackathon) by Encode Club.

## Features

- **Socratic Goal Refinement** — Agent asks clarifying questions to transform vague ideas into SMART goals
- **Smart Task Breakdown** — Goals broken into 3-7 atomic micro-tasks (5-20 min each)
- **Coach vs Secretary** — Beginners get specific curriculum (Week 0 philosophy); experts get optimization tasks
- **Human-in-the-Loop** — Plans are staged for review before saving; users can modify or confirm
- **Anchor-Based Scheduling** — Tasks matched to daily routines (Morning Coffee, Lunch Break, End of Day) by energy level
- **Adaptive Rescheduling** — Missed or skipped tasks automatically find the next available slot
- **Real-Time Streaming** — SSE pipeline shows progress as the agent thinks (Intent → Smart Goal → Tasks → Schedule → Plan)
- **AI Coach Chat** — Conversational support for motivation, setbacks, and progress review (with tool use)
- **Google Calendar Sync** — OAuth-based calendar integration: auto-creates events on plan confirmation, reads calendar for context and conflict avoidance
- **Email Reminders** — Task reminders via Resend when tasks are due
- **ADHD-Friendly Dashboard** — Three sections (NOW / NEXT / ACHIEVED), large touch targets, medal celebrations
- **Guest & Auth Modes** — Use instantly without signup (localStorage), or sign in for Supabase persistence
- **Progress Visualization** — Circular spiral tracker with completion metrics
- **LLM Observability** — Full tracing and online LLM-judge evaluation via Comet Opik

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
| **Google Integration** | Google Calendar API (OAuth 2.0) |
| **Email** | Resend |
| **Observability** | Comet Opik |
| **Frontend Hosting** | Vercel |
| **Backend Hosting** | Heroku (Procfile) / Google Cloud Run (CI/CD) |

## Getting Started

### Prerequisites

- Node.js 20+ / pnpm
- Python 3.11+
- Google Gemini API key
- Supabase project (optional — guest mode works without it)
- Google Cloud project with Calendar API enabled (optional — for calendar sync)
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
OPIK_API_KEY=your_opik_api_key                # optional
RESEND_API_KEY=your_resend_api_key             # optional

# Google Calendar OAuth (optional)
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/google/callback
FRONTEND_ORIGIN=http://localhost:5173
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

### Google Calendar Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Calendar API**
3. Create OAuth 2.0 credentials (Web application)
4. Add `http://localhost:8000/api/google/callback` as an authorized redirect URI
5. Set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, and `FRONTEND_ORIGIN` in your `.env`

## Architecture

### Project Structure

```
goalie.app/
├── app/                            # FastAPI + LangGraph backend
│   ├── main.py                     # App entry: CORS, Opik, routes
│   ├── api/
│   │   ├── routes.py               # REST + SSE streaming endpoints
│   │   ├── schemas.py              # API request/response models
│   │   └── google_routes.py        # Google OAuth flow endpoints
│   ├── agent/
│   │   ├── graph.py                # Orchestrator + Planning subgraph (LangGraph)
│   │   ├── nodes.py                # All node implementations + LLM helpers
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── schema.py               # Domain models (Intent, SmartGoal, Plan, etc.)
│   │   ├── prompts.py              # Prompt template loader
│   │   ├── memory.py               # Session stores (Memory, Supabase, Hybrid)
│   │   ├── adaptive_scheduler.py   # Anchor-to-timestamp + rescheduling
│   │   ├── execution_tracker.py    # Task completion/miss tracking
│   │   ├── opik_utils.py           # Opik tracing + LLM-judge evaluation
│   │   ├── prompts/                # 8 markdown prompt templates
│   │   └── tools/
│   │       ├── crud.py             # LangChain tools (create_task, create_goal, complete_task)
│   │       └── descriptions/       # Tool description markdown files
│   ├── services/
│   │   ├── calendar_service.py     # Google Calendar API wrapper
│   │   └── reminders.py            # Email reminders via Resend
│   └── core/
│       ├── config.py               # Settings (env vars, LLM config, Google OAuth)
│       └── supabase.py             # Supabase client init
├── frontend/                       # React 19 SPA
│   └── src/
│       ├── pages/                  # Index (dashboard), GoogleConnected, NotFound
│       ├── components/             # 17 business components + 49 Radix UI primitives
│       ├── contexts/               # AuthContext (magic link + guest mode)
│       ├── hooks/                  # useStreamingChat, useGoogleCalendar, useTasks, useGoals
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
  ├─→ casual ─────────────────────────→ Response + Tool Actions
  ├─→ coaching ───────────────────────→ Response + Tool Actions
  ├─→ confirm (HITL) ────────────────→ Commit staged plan → Task Actions + Calendar Sync
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
                         Context Matcher (energy → anchors + calendar conflict check)
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

**Google Calendar Integration** — Three integration points: (1) calendar context injected into agent prompts for awareness, (2) conflict avoidance during task scheduling, (3) auto-creation of calendar events on plan confirmation.

### Database Schema (Supabase)

| Table | Purpose |
|-------|---------|
| `profiles` | User preferences, daily anchors, display name |
| `goals` | Goals with emoji, status (active/achieved/archived), target date |
| `tasks` | Micro-tasks with time estimates, energy level, assigned anchor, scheduled_at, rationale |
| `sessions` | Conversation sessions with last_active tracking |
| `messages` | Chat history with role, content, metadata (tokens, model, tool_calls) |
| `google_tokens` | Google OAuth tokens (access_token, refresh_token, google_email, scopes, expiry) |

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
| POST | `/api/tasks/{id}/reschedule` | Adaptive task rescheduling |
| GET/POST | `/api/goals` | List / create goals |
| PUT/DELETE | `/api/goals/{id}` | Update / delete goal |
| GET/PUT | `/api/profile/{user_id}` | Get / update user profile |
| GET | `/api/health` | Health check |

### Google Calendar

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/google/auth-url` | Generate OAuth consent URL |
| GET | `/api/google/callback` | OAuth callback (token exchange + storage) |
| GET | `/api/google/status` | Check connection status |
| POST | `/api/google/disconnect` | Remove stored tokens |

### Reminders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reminders/test` | Send test reminder email |
| POST | `/api/reminders/check` | Manually trigger reminder check |

## Frontend Dashboard

```
┌──────────────────────────────────────┬──────────────────┐
│  DashboardHeader (greeting + auth    │                  │
│    + Google Calendar)                │                  │
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

This project uses [Comet Opik](https://www.comet.com/site/products/opik/) for LLM observability:

- **Plan tracing** — All LangGraph planning operations are traced with input/output logging
- **Online evaluation** — LLM-judge scores plans on Constraint Adherence, Feasibility, and Task Coverage
- **Execution tracking** — Task completions and misses are logged for behavioral analytics

Initialization is optional and gracefully skipped if `OPIK_API_KEY` is unconfigured.

## License

MIT
