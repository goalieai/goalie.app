# Goally

AI agent to help users achieve their New Year's resolutions through micro-task management and motivational coaching. Built on behavioral science principles (Tiny Habits, Socratic questioning, identity-based motivation).

**Hackathon:** Comet Resolution V2 - Encode Club

## Stack

| Component            | Technology                                          |
| -------------------- | --------------------------------------------------- |
| **Frontend**         | React 19 + TypeScript 5.9 + Vite 7                  |
| **Styling**          | Tailwind CSS 3.4 + Radix UI (49 primitives)         |
| **Data Fetching**    | TanStack Query 5                                     |
| **Auth/DB**          | Supabase (PostgreSQL + Auth + RLS)                   |
| **Backend**          | FastAPI + LangGraph + Gemini 3 Flash Preview         |
| **LLM Fallback**     | Ollama (llama3.2:1b local)                           |
| **Streaming**        | SSE via sse-starlette                                |
| **Observability**    | Comet Opik                                           |
| **Email Reminders**  | Resend                                               |
| **Google Integration** | Google Calendar API (OAuth 2.0)                    |
| **Frontend Hosting** | Vercel                                               |
| **Backend Hosting**  | Heroku (Procfile) / Google Cloud Run (CI/CD)         |
| **CI/CD**            | GitHub Actions (in `workflows/` directory)           |

## Project Structure

```
goalie.app/
├── app/                        # FastAPI + LangGraph backend
│   ├── main.py                 # App entry: CORS, Opik, routes
│   ├── api/
│   │   ├── routes.py           # REST + SSE streaming endpoints
│   │   ├── schemas.py          # API request/response Pydantic models
│   │   └── google_routes.py    # Google OAuth flow (auth-url, callback, status, disconnect)
│   ├── agent/
│   │   ├── graph.py            # Orchestrator + Planning subgraph (LangGraph)
│   │   ├── nodes.py            # All node implementations + LLM helpers
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── schema.py           # Domain models (Intent, SmartGoal, Plan, etc.)
│   │   ├── prompts.py          # Prompt template loader utility
│   │   ├── memory.py           # Session stores (Memory, Supabase, Hybrid)
│   │   ├── adaptive_scheduler.py # Anchor-to-timestamp mapping + rescheduling
│   │   ├── execution_tracker.py  # Task completion/miss tracking (Opik)
│   │   ├── opik_utils.py       # Opik tracing + LLM-judge online evaluation
│   │   ├── prompts/            # Markdown prompt templates (8 files)
│   │   │   ├── system_base.md  # Core identity & personality
│   │   │   ├── orchestrator.md # Intent classification rules
│   │   │   ├── smart_refiner.md# Socratic Gatekeeper (dual-path)
│   │   │   ├── task_splitter.md# Coach vs Secretary logic
│   │   │   ├── planning.md     # HITL plan presentation
│   │   │   ├── casual.md       # Casual conversation
│   │   │   ├── coaching.md     # Progress & motivation
│   │   │   └── modifier.md     # Plan modification
│   │   └── tools/
│   │       ├── crud.py         # LangChain tools (create_task, create_goal, complete_task)
│   │       └── descriptions/   # Tool description markdown files
│   ├── services/
│   │   ├── calendar_service.py # Google Calendar API: event creation, context fetch, credentials
│   │   └── reminders.py        # Email reminder service (Resend)
│   └── core/
│       ├── config.py           # Settings (env vars, LLM config, rate limits, Google OAuth)
│       └── supabase.py         # Supabase client init
├── frontend/                   # React 19 SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Index.tsx       # Main dashboard (NOW / NEXT / ACHIEVED + Agent Chat)
│   │   │   ├── GoogleConnected.tsx # OAuth callback landing page
│   │   │   └── NotFound.tsx
│   │   ├── components/
│   │   │   ├── ui/             # 49 Radix-based primitives
│   │   │   ├── AgentChat.tsx   # AI chat sidebar (SSE, pipeline, plan preview)
│   │   │   ├── GoogleConnectButton.tsx # Connect/disconnect Google Calendar
│   │   │   ├── TaskCard.tsx    # Task with Done/Re-plan
│   │   │   ├── PlanPreview.tsx # HITL staged plan display
│   │   │   ├── PipelineProgress.tsx # Visual step indicator
│   │   │   ├── ProgressSpiral.tsx # SVG circular progress
│   │   │   ├── DashboardHeader.tsx # Greeting, auth, Google connect
│   │   │   └── ...
│   │   ├── contexts/           # AuthContext (Supabase magic link + guest mode)
│   │   ├── hooks/
│   │   │   ├── useStreamingChat.ts  # SSE streaming, HITL, Socratic, pipeline
│   │   │   ├── useGoogleCalendar.ts # Google Calendar status, connect, disconnect
│   │   │   ├── useTasks.ts     # TanStack Query CRUD for tasks
│   │   │   └── useGoals.ts     # TanStack Query CRUD for goals
│   │   ├── services/           # api.ts, store.ts, storage.ts, supabaseStore.ts
│   │   ├── lib/                # utils.ts (cn), supabase.ts (client)
│   │   ├── types/              # database.ts (TypeScript interfaces)
│   │   └── test/               # Vitest setup
│   └── ...
├── docs/                       # Architecture docs
├── workflows/                  # CI/CD (backend.yml, frontend.yml, preview.yml)
├── supabase/                   # DB migrations
├── scripts/                    # init_user.py (Supabase test user setup)
├── Procfile                    # Heroku: uvicorn app.main:app
├── vercel.json                 # SPA rewrites
├── requirements.txt            # Python deps
└── runtime.txt                 # Python 3.11.9
```

## Quick Start

### Backend

```bash
# From project root
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev  # http://localhost:5173
```

## Environment Variables

### Backend (`.env` at project root)

```
GOOGLE_API_KEY=           # Gemini API key (primary LLM)
SUPABASE_URL=             # Supabase project URL
SUPABASE_KEY=             # Supabase service role key
OPIK_API_KEY=             # Comet Opik (optional)
RESEND_API_KEY=           # Resend email service (optional)
GOOGLE_OAUTH_CLIENT_ID=   # Google OAuth client ID (for Calendar)
GOOGLE_OAUTH_CLIENT_SECRET= # Google OAuth client secret
GOOGLE_OAUTH_REDIRECT_URI=  # e.g. http://localhost:8000/api/google/callback
FRONTEND_ORIGIN=          # e.g. http://localhost:5173
```

### Frontend (`frontend/.env`)

```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=        # Supabase project URL
VITE_SUPABASE_ANON_KEY=   # Supabase public anon key
```

If Supabase env vars are missing, the frontend runs in **guest-only mode** (localStorage).

## Backend Architecture

### Agent Graph (LangGraph)

**Orchestrator Graph** (main flow):
```
intent_router
  ├─→ casual_node → END
  ├─→ coaching_node → END
  ├─→ confirmation_node (HITL commit + calendar sync) → END
  ├─→ modify_node (edit loop) → END
  └─→ planning_subgraph
        └─→ smart_refiner
              ├─→ END (if needs_clarification — Socratic Gatekeeper)
              └─→ task_splitter → context_matcher → planning_response (HITL stage) → END
```

**Entry points:** `run_orchestrator()` (main), `run_planning_pipeline()` (direct), `run_agent()` (legacy)

### Key Patterns

1. **Socratic Gatekeeper** — `smart_refiner_node` asks clarifying questions for vague goals before planning. Saves `pending_context` across turns. Safety counter `clarification_attempts` prevents loops.

2. **Human-in-the-Loop (HITL)** — Plans are **staged** in `staging_plan`, not saved. Only committed to `active_plans` on explicit "confirm" intent. `planning_response_node` ends with "Shall I save this plan?" CTA.

3. **Coach vs Secretary** — Context tags (`beginner`/`expert`) set the approach. Coach mode gives specific curriculum with Week 0 philosophy (environment design, identity building). Secretary mode gives higher-level optimization tasks.

4. **LLM Fallback Strategy** — Primary: `gemini-3-flash-preview` (temp=0.0). Fallback: `ollama:llama3.2:1b`. Falls back on HTTP 429, rate limits, parse errors. Conversational calls use temp=0.7.

5. **SSE Streaming** — `/api/chat/stream` emits real-time events (`status`, `clarification`, `progress`, `complete`, `error`) to prevent Heroku H12 timeout and improve perceived performance.

6. **Hybrid Session Store** — With `user_id` → Supabase (persistent). Without → in-memory (temporary). Session tracks: messages, active_plans, staging_plan, pending_context, clarification_attempts.

7. **Adaptive Scheduling** — `adaptive_scheduler.py` maps task anchors ("Morning Coffee", "After Lunch") to real timestamps. `context_matcher_node` assigns `scheduled_at` to each task. Rescheduling available via `/api/tasks/{id}/reschedule`.

8. **LLM Tool Binding** — Conversational LLMs (casual, coaching nodes) are bound with `ALL_TOOLS` from `crud.py` at module level. Tools: `create_task`, `create_goal`, `complete_task`. Tool calls return action payloads (`{"type": "create_task", "data": {...}}`) processed by the frontend.

### Google Calendar Integration

**OAuth Flow:**
1. Frontend calls `GET /api/google/auth-url?user_id=X` → gets Google consent URL
2. User authorizes → Google redirects to `GET /api/google/callback?code=Y&state=user_id`
3. Backend exchanges code for tokens, stores in `google_tokens` Supabase table
4. Frontend redirects to `/google-connected` landing page (success/error)

**Calendar Usage:**
- **Context injection** — `get_calendar_context()` fetches upcoming events and injects into system prompts for casual/coaching nodes (read-only awareness)
- **Conflict avoidance** — `context_matcher_node` fetches calendar events to avoid scheduling tasks during existing events
- **Auto-sync on confirm** — `confirmation_node` creates Google Calendar events for all plan tasks via `create_calendar_events_for_plan()`
- **Credentials** — `get_user_google_credentials()` loads from Supabase, auto-refreshes expired tokens

**Current OAuth Scope:** `calendar` only (no Gmail scope)

### Services Layer (`app/services/`)

| Service | File | Purpose |
|---------|------|---------|
| Calendar | `calendar_service.py` | Google Calendar API wrapper: credentials, event creation, context fetch |
| Reminders | `reminders.py` | Email reminders via Resend for upcoming tasks |

### Observability (Comet Opik)

- `opik_utils.py` — Wraps plan execution with Opik tracing + online LLM-judge evaluation (Constraint Adherence, Feasibility, Task Coverage)
- `execution_tracker.py` — Logs task completions and misses for execution analytics
- All tracing is optional and gracefully skipped if `OPIK_API_KEY` is not set

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Unified chat (returns immediate response) |
| POST | `/api/chat/stream` | Streaming chat via SSE |
| POST | `/api/chat/legacy` | Legacy chat (backwards compat) |
| POST | `/api/plan` | Direct planning pipeline |
| GET/PUT | `/api/profile/{user_id}` | User profile CRUD |
| GET/POST/PUT/DELETE | `/api/tasks` | Task CRUD |
| POST | `/api/tasks/{id}/reschedule` | Adaptive task rescheduling |
| GET/POST/PUT/DELETE | `/api/goals` | Goal CRUD |
| POST | `/api/reminders/test` | Send test reminder email |
| POST | `/api/reminders/check` | Manually trigger reminder check |
| GET | `/api/google/auth-url` | Google OAuth consent URL |
| GET | `/api/google/callback` | OAuth callback (token exchange) |
| GET | `/api/google/status` | Check Google Calendar connection status |
| POST | `/api/google/disconnect` | Remove Google tokens |
| GET | `/api/health` | Health check |
| GET | `/` | API status |

### Domain Models (`agent/schema.py`)

- **IntentClassification** — intent (`casual`|`planning`|`coaching`|`modify`|`confirm`|`planning_continuation`), confidence, reasoning
- **RefinerOutput** — status (`needs_clarification`|`ready`), clarifying_question or smart_goal
- **SmartGoalSchema** — summary, specific_outcome, measurable_metric, deadline, constraints
- **TaskList** — 3-7 atomic tasks (<20 min each)
- **MicroTask** — task_name, estimated_minutes (5-20), energy_required (high/medium/low), assigned_anchor, rationale, scheduled_at
- **ProjectPlan** — project_name, smart_goal_summary, deadline, tasks (List[MicroTask])
- **UserProfile** — name, role, anchors (daily habits: "Morning Coffee", "After Lunch", "End of Day")

### Supabase Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Conversation sessions with last_active tracking |
| `messages` | Chat history with role, content, metadata |
| `goals` | Goals with emoji, status, target date |
| `tasks` | Micro-tasks with time estimates, energy, anchor, scheduled_at |
| `profiles` | User preferences, anchors, display name |
| `google_tokens` | Google OAuth tokens (access_token, refresh_token, google_email, scopes) |

All tables use `user_id` for RLS.

## Frontend Architecture

### Key Components

| Component | Purpose |
|-----------|---------|
| **AgentChat** | Sidebar chat with AI coach; SSE streaming, pipeline progress, plan previews |
| **TaskCard** | Individual task with Done/Re-plan actions, time badge, energy indicator |
| **PlanPreview** | Staged plan display with confirm/modify buttons (HITL) |
| **PipelineProgress** | Visual step indicator (Intent → Smart → Tasks → Schedule → Plan) |
| **ProgressSpiral** | SVG circular progress ring with stats |
| **DashboardHeader** | Time-based greeting, date, user name, auth button, Google Calendar button |
| **GoogleConnectButton** | Connect/disconnect Google Calendar (shows email when connected) |
| **AddTaskForm** | Dialog to manually create tasks (name, minutes, energy) |
| **AddGoalForm** | Dialog to create goals (emoji + title) |
| **LoginDialog** | Magic link email auth (Supabase OTP) |
| **AgentFeedback** | Contextual AI suggestions |
| **MedalTask** | Completed tasks with medal badge |

### Hooks

| Hook | Purpose |
|------|---------|
| `useStreamingChat()` | SSE streaming, HITL staging, Socratic clarification, pipeline state |
| `useGoogleCalendar()` | Google Calendar connection status, connect, disconnect |
| `useTasks()` / mutations | TanStack Query CRUD for tasks |
| `useGoals()` / mutations | TanStack Query CRUD for goals |
| `useAuth()` | Auth context (user, isGuest, signIn, signOut, migrateGuestData) |

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| `Index` | `/` | Main dashboard (NOW / NEXT / ACHIEVED + Agent Chat sidebar) |
| `GoogleConnected` | `/google-connected` | OAuth callback landing page (success/error → redirect to dashboard) |
| `NotFound` | `*` | 404 catch-all |

### Action Processing

The agent returns actions that the frontend processes via `processAction()` in `Index.tsx`:

```typescript
switch (action.type) {
  case "create_task"   → store.tasks.create(data) → invalidate ["tasks"]
  case "complete_task"  → store.tasks.complete(id) → invalidate ["tasks"]
  case "create_goal"   → store.goals.create(data) → invalidate ["goals"]
  case "update_task"   → queryClient.invalidateQueries(["tasks"])
  case "refresh_ui"    → invalidate all queries
}
```

### State Management

- **Auth**: React Context (`AuthContext`) — Supabase magic link + guest mode with localStorage migration
- **Data**: TanStack Query 5 — query keys `["goals", userId]`, `["tasks", userId]`, auto-invalidation on mutations
- **Streaming**: Custom `useStreamingChat` hook — SSE buffer, pipeline progress, HITL staging, Socratic state
- **Store Factory**: `getStore(userId)` returns localStorage (guest) or Supabase (authenticated) store — same interface
- **Google**: `useGoogleCalendar(userId)` — TanStack Query for status, connect/disconnect mutations

### Design System

- **Primary:** Orange `hsl(25 95% 53%)` — Energy, motivation
- **Secondary:** Cream `hsl(35 40% 94%)` — Calm, rest
- **Success:** Green `hsl(140 50% 45%)` — Completed tasks
- **Destructive:** Red-Orange `hsl(0 70% 55%)`
- **Warning:** Golden Amber `hsl(45 95% 55%)`
- **Fonts:** Nunito (body), Space Grotesk (display)
- **Border Radius:** 1rem base
- **Dark mode:** Supported via `.dark` class
- **Section backgrounds:** `--now-bg` (orange tint), `--next-bg` (warm tint), `--achieved-bg` (gold tint)

### UX Principles (ADHD-Friendly)

- Miller's Law: Max 3 sections (NOW, NEXT, ACHIEVED)
- Fitts' Law: Large touch targets (56-64px buttons)
- Micro-tasks with time estimates (5-20 min)
- Immediate gratification (achieved section with medals)
- Zero-friction onboarding (guest mode, no signup required)

## Conventions

- **Language:** English (code, comments, commits)
- **Python:** snake_case, Pydantic models, type hints
- **TypeScript/React:** camelCase variables, PascalCase components
- **Commits:** conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **Path Alias:** `@/` maps to `frontend/src/`
- **Prompts:** Markdown templates in `app/agent/prompts/`, loaded by `prompts.py`
- **LLM Config:** Structured output (temp=0.0) for planning, tools (temp=0.7) for conversation
- **Toasts:** Sonner (`import { toast } from "sonner"`)
- **Action types flow:** Backend tool returns `{"type": "action_name", "data": {...}}` → frontend `processAction` switch
- **Supabase client:** Global singleton in `app/core/supabase.py`, may be `None` if unconfigured
