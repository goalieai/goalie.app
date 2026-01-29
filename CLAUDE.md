# Goally

AI agent to help users achieve their New Year's resolutions through micro-task management and motivational coaching.

**Hackathon:** Comet Resolution V2 - Encode Club

## Stack

| Component            | Technology                         |
| -------------------- | ---------------------------------- |
| **Frontend**         | React 19 + TypeScript 5.9 + Vite 7 |
| **Styling**          | Tailwind CSS 3.4 + Radix UI        |
| **Backend**          | FastAPI + LangGraph + Gemini       |
| **Observability**    | Comet Opik                         |
| **Frontend Hosting** | Vercel                             |
| **Backend Hosting**  | Heroku                             |
| **CI/CD**            | GitHub Actions                     |

## Project Structure

```
goally/
├── app/                # FastAPI + LangGraph agent (Heroku backend)
│   ├── api/            # REST endpoints
│   ├── agent/          # LangGraph workflow
│   │   ├── graph.py    # Orchestrator + Planning graphs
│   │   ├── nodes.py    # Node implementations
│   │   ├── schema.py   # Pydantic models
│   │   ├── memory.py   # Session management
│   │   ├── prompts/    # Markdown prompt templates
│   │   └── tools/      # LangChain tools
│   └── core/           # Configuration
├── frontend/           # React 19 SPA (Vercel)
│   ├── src/
│   │   ├── pages/      # Route-level components (Index, NotFound)
│   │   ├── components/ # UI components
│   │   │   ├── ui/     # Radix-based primitives
│   │   │   ├── AgentChat.tsx
│   │   │   ├── TaskCard.tsx
│   │   │   └── ...
│   │   ├── hooks/      # Custom hooks
│   │   ├── lib/        # Utilities
│   │   └── services/   # API client
│   └── ...
├── docs/               # Architecture documentation
├── Procfile            # Heroku process definition
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version for Heroku
└── .github/            # CI/CD workflows
```

## Quick Start

### Backend

```bash
# From project root
pip install -r requirements.txt
uvicorn app.main:app --reload  # Runs at http://localhost:8000
```

### Frontend

```bash
cd frontend
pnpm install    # or npm install
pnpm dev        # Runs at http://localhost:5173
```

## Environment Variables

### Backend (`.env` at root)

```
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPIK_API_KEY=your_opik_api_key
```

### Frontend (`frontend/.env`)

```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Frontend Architecture

### Key Components

- **TaskCard** - Individual task with Done/Re-plan actions
- **AgentChat** - Sidebar chat with AI coach
- **AgentFeedback** - Contextual suggestions (breaks, reschedule, motivation)
- **ProgressSpiral** - SVG circular progress visualization
- **DashboardHeader** - Dynamic greeting + progress summary

### Design System

- **Primary Color:** Orange (hsl 25 95% 53%) - Energy, motivation
- **Secondary Color:** Cream (hsl 35 40% 94%) - Calm, rest
- **Success:** Green (hsl 140 50% 45%) - Completed tasks
- **Fonts:** Nunito (body), Space Grotesk (display)

### UX Principles (ADHD-Friendly)

- Miller's Law: Max 3+1 sections (NOW, NEXT, ACHIEVED)
- Fitts' Law: Large touch targets (56-64px buttons)
- Micro-tasks with time estimates
- Immediate gratification (achieved section)

## Conventions

- **Language:** English (code, comments, commits)
- **Python:** snake_case
- **TypeScript/React:** camelCase, PascalCase components
- **Commits:** conventional commits (feat:, fix:, docs:, etc.)
- **Path Alias:** `@/` maps to `./src/`
