# Goally

AI-powered agent to help you achieve your New Year's resolutions through intelligent micro-task management and motivational coaching.

Built for the [Comet Resolution V2 Hackathon](https://www.encodeclub.com/programmes/comet-resolution-v2-hackathon) by Encode Club.

## Features

- **Smart Task Breakdown** - AI breaks down goals into manageable micro-tasks (5-20 min)
- **ADHD-Friendly Design** - Clear sections, large touch targets, immediate feedback
- **AI Coach Chat** - Real-time motivational support and guidance
- **Adaptive Scheduling** - Tasks assigned to your daily anchors (Morning Coffee, Lunch Break, etc.)
- **Progress Visualization** - Spiral progress tracker with completion metrics
- **Unified Agent** - Single intent-router manages planning, coaching, and casual conversation
- **Guest & Authenticated Modes** - Use without login, or sign in for persistence

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19 + TypeScript 5.9 + Vite 7 |
| **State & Routing** | TanStack Query 5 + React Router 7 |
| **Styling** | Tailwind CSS 3.4 + Radix UI + Lucide Icons |
| **Backend** | FastAPI + LangGraph + LangChain |
| **LLM** | Google Gemini (`gemini-3-flash-preview`) |
| **Database** | Supabase (PostgreSQL) |
| **Auth** | Supabase Auth (Magic Link) |
| **Observability** | Comet Opik |
| **Hosting** | Vercel (Frontend) + Google Cloud Run (Backend) |

## Getting Started

### Prerequisites

- Node.js 20+ / pnpm
- Python 3.11+
- Google Cloud account (for Gemini API)
- Supabase Project
- Comet account (for Opik - optional)

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev
```

Create `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

Frontend runs at `http://localhost:5173`

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_key
OPIK_API_KEY=your_opik_api_key  # optional
```

Run the server:
```bash
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

## Architecture

### Project Structure

```
goally/
├── frontend/                    # React 19 SPA
│   └── src/
│       ├── pages/               # Route components (Index, NotFound)
│       ├── components/
│       │   ├── ui/              # Radix-based primitives (Button, Card, etc.)
│       │   ├── AgentChat.tsx    # AI coach sidebar
│       │   ├── TaskCard.tsx     # Task display with Done/Re-plan actions
│       │   ├── ProgressSpiral.tsx
│       │   └── ...
│       ├── contexts/            # AuthContext (Supabase)
│       ├── hooks/               # useTasks, useGoals, useToast
│       └── services/            # API client (api.ts, storage.ts)
├── backend/                     # FastAPI + LangGraph
│   └── app/
│       ├── api/                 # REST endpoints (routes.py, schemas.py)
│       ├── agent/
│       │   ├── graph.py         # StateGraph (Orchestrator & Planning)
│       │   ├── nodes.py         # Node logic (intent, casual, coaching)
│       │   ├── memory.py        # HybridSessionStore
│       │   ├── prompts/         # Markdown prompt templates
│       │   └── tools/           # LangChain tools (create_task, etc.)
│       └── core/                # Config & Supabase client
└── .github/                     # CI/CD workflows
```

### Agent Workflow

```
User Message -> Intent Router -> [casual | coaching | planning_pipeline]
                                        |
                                        v
                              Response + Actions[]
```

**Intent Types:**
- `casual` - Greetings, small talk, general questions
- `planning` - Create new goals/plans (triggers full pipeline)
- `coaching` - Progress review, motivation, setback handling

### Planning Pipeline

```
Smart Refiner -> Task Splitter -> Context Matcher
     |                |                |
     v                v                v
 SMART Goal      3-7 Tasks      MicroTasks with Anchors
```

### Database Schema

**`goals`** - User goals with status tracking
**`tasks`** - Micro-tasks with time estimates, energy levels, and anchor assignments
**`profiles`** - User preferences and daily anchors
**`sessions`** / **`messages`** - Conversation persistence

## API Endpoints

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to agent (handles all intents) |

### Resources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/tasks` | List/create tasks |
| PUT/DELETE | `/api/tasks/{id}` | Update/delete task |
| GET/POST | `/api/goals` | List/create goals |
| PUT/DELETE | `/api/goals/{id}` | Update/delete goal |
| GET/PUT | `/api/profile/{id}` | Get/update user profile |

## Design System

**Colors (HSL):**
- **Primary (Orange)**: `hsl(25 95% 53%)` - Energy, motivation
- **Secondary (Cream)**: `hsl(35 40% 94%)` - Calm backgrounds
- **Success**: `hsl(140 50% 45%)` - Completed tasks

**UX Principles (ADHD-Friendly):**
- Miller's Law: Max 3+1 sections (NOW, NEXT, ACHIEVED)
- Fitts' Law: Large touch targets (56-64px buttons)
- Micro-tasks with time estimates
- Immediate gratification (achieved section with points)

## Deployment

### Frontend (Vercel)
Auto-deploys on push to `main`. Set environment variables in Vercel dashboard.

### Backend (Google Cloud Run)
Auto-deploys on push to `main`. Requires GCP Service Account and environment variables.

## Observability

This project uses [Comet Opik](https://www.comet.com/site/products/opik/) for LLM observability. All LangGraph operations are automatically traced, allowing you to debug agent reasoning and tool usage.

## License

MIT
