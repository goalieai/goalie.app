# Goally

AI-powered agent to help you achieve your New Year's resolutions through intelligent micro-task management and motivational coaching.

Built for the [Comet Resolution V2 Hackathon](https://www.encodeclub.com/programmes/comet-resolution-v2-hackathon) by Encode Club.

## Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React 19 + TypeScript 5.9 + Vite 7 |
| **State & Routing** | TanStack Query 5 + React Router 7 |
| **Styling** | Tailwind CSS 3.4 + Radix UI |
| **Backend** | FastAPI + LangGraph + LangChain |
| **Database** | Supabase (PostgreSQL) |
| **LLM** | Google Gemini (gemini-2.5-flash) |
| **Observability** | Comet Opik |
| **Hosting** | Vercel (Frontend) + Google Cloud Run (Backend) |

## Features

- **Smart Task Breakdown** - AI breaks down goals into manageable micro-tasks
- **ADHD-Friendly Design** - Clear sections, large buttons, immediate feedback
- **AI Coach Chat** - Real-time motivational support and guidance
- **Adaptive Scheduling** - Re-plan tasks based on your progress
- **Progress Visualization** - Spiral progress tracker with completion metrics
- **Unified Agent** - Single intent-router manages planning, coaching, and casual conversation

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- Google Cloud account (for Gemini API)
- Supabase Project
- Comet account (for Opik)

### Frontend Setup

```bash
cd frontend
pnpm install    # or npm install
pnpm dev
```

Frontend runs at `http://localhost:5173`

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
GOOGLE_API_KEY=your_gemini_api_key
OPIK_API_KEY=your_opik_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_key
```

Run the server:

```bash
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

## Project Structure

```
goally/
├── frontend/                    # React 19 SPA
│   ├── src/
│   │   ├── pages/               # Route components
│   │   │   ├── Index.tsx        # Main dashboard
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── ui/              # Radix-based UI primitives
│   │   │   ├── AgentChat.tsx    # AI coach sidebar
│   │   │   ├── TaskCard.tsx     # Task with actions
│   │   │   └── ...
│   │   ├── hooks/               # React Query hooks (useTasks, useGoals)
│   │   └── services/            # API client
│   └── ...
├── backend/                     # FastAPI + LangGraph
│   └── app/
│       ├── api/                 # REST endpoints
│       ├── agent/               # LangGraph workflow (Orchestrator)
│       ├── core/                # Configuration & Supabase
│       └── ...
└── ...
```

## API Endpoints

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to agent (handles planning & coaching) |
| POST | `/api/plan` | Run planning pipeline directly |

### Resources (CRUD)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List user tasks |
| POST | `/api/tasks` | Create task |
| GET | `/api/goals` | List user goals |
| POST | `/api/goals` | Create goal |
| GET | `/api/profile/{id}` | Get user profile |

## Deployment

### Frontend (Vercel)

The frontend auto-deploys to Vercel on push to `main`. Configure `VITE_API_BASE_URL` if needed.

### Backend (Google Cloud Run)

The backend auto-deploys to Cloud Run on push to `main`. Requires GCP Service Account and all environment variables configured.

## Observability

This project uses [Comet Opik](https://www.comet.com/site/products/opik/) for LLM observability. All LangGraph operations are automatically traced, allowing you to debug agent reasoning and tool usage.

## License

MIT
