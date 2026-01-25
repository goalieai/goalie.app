# Goally

AI-powered agent to help you achieve your New Year's resolutions through intelligent micro-task management and motivational coaching.

Built for the [Comet Resolution V2 Hackathon](https://www.encodeclub.com/programmes/comet-resolution-v2-hackathon) by Encode Club.

## Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19 + TypeScript 5.9 + Vite 7 |
| Styling | Tailwind CSS 3.4 + Radix UI |
| Backend | FastAPI + LangGraph + LangChain |
| LLM | Google Gemini |
| Observability | Comet Opik |
| Frontend Hosting | Vercel |
| Backend Hosting | Google Cloud Run |
| CI/CD | GitHub Actions |

## Features

- **Smart Task Breakdown** - AI breaks down goals into manageable micro-tasks
- **ADHD-Friendly Design** - Clear sections, large buttons, immediate feedback
- **AI Coach Chat** - Real-time motivational support and guidance
- **Adaptive Scheduling** - Re-plan tasks based on your progress
- **Progress Visualization** - Spiral progress tracker with completion metrics

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- Google Cloud account (for Gemini API)
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
│   │   │   └── NotFound.tsx     # 404 page
│   │   ├── components/
│   │   │   ├── ui/              # Radix-based UI primitives
│   │   │   ├── AgentChat.tsx    # AI coach sidebar
│   │   │   ├── AgentFeedback.tsx# Contextual suggestions
│   │   │   ├── TaskCard.tsx     # Task with actions
│   │   │   ├── ProgressSpiral.tsx # Circular progress
│   │   │   ├── DashboardHeader.tsx
│   │   │   └── ...
│   │   ├── hooks/               # Custom React hooks
│   │   ├── lib/                 # Utilities
│   │   └── assets/              # Images
│   └── ...
├── backend/                     # FastAPI + LangGraph
│   └── app/
│       ├── api/                 # REST endpoints
│       ├── agent/               # LangGraph workflow
│       └── core/                # Configuration
└── .github/workflows/           # CI/CD pipelines
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to agent |
| GET | `/api/health` | Health check |

## Deployment

### Frontend (Vercel)

The frontend auto-deploys to Vercel on push to `main`. Configure these secrets in GitHub:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

### Backend (Google Cloud Run)

The backend auto-deploys to Cloud Run on push to `main`. Configure these secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `GOOGLE_API_KEY`
- `OPIK_API_KEY`

## Observability

This project uses [Comet Opik](https://www.comet.com/site/products/opik/) for LLM observability. All LangGraph operations are automatically traced.

View traces at: https://www.comet.com/opik

## Design Philosophy

Goally is designed with ADHD-friendly principles:

- **Miller's Law** - Maximum 3+1 sections (NOW, NEXT, ACHIEVED)
- **Fitts' Law** - Large touch targets (56-64px buttons)
- **Immediate Feedback** - Visual celebration on task completion
- **Micro-tasks** - Small, achievable chunks with time estimates

## License

MIT
