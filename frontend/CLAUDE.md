# Frontend Guide - Goally

## Overview

Goally's frontend is a **React 19** Single Page Application (SPA) built with **Vite** and **TypeScript**. It features a modern, accessible UI using **Radix UI** primitives and **Tailwind CSS**.

## Tech Stack

- **Core**: React 19 + TypeScript 5.9
- **Build**: Vite 7
- **Routing**: React Router DOM 7
- **Styling**: Tailwind CSS 3.4 + `tailwindcss-animate`
- **UI Components**: Radix UI (Headless accessible components)
- **State/Fetching**: TanStack React Query 5
- **Icons**: Lucide React
- **Notifications**: Sonner

## Project Structure

```
src/
├── pages/
│   ├── Index.tsx            # Main Dashboard (Split view: Tasks + Agent)
│   └── NotFound.tsx         # 404 Route
├── components/
│   ├── ui/                  # Reusable Design System (Button, Card, Input...)
│   ├── AgentChat.tsx        # AI Chat Interface
│   ├── TaskCard.tsx         # Micro-task display & management
│   ├── DashboardHeader.tsx  # User greeting & stats
│   ├── AddTaskForm.tsx      # Task creation modal
│   ├── AddGoalForm.tsx      # High-level goal creation
│   └── ...                  # Other domain components
├── services/
│   ├── api.ts               # Typed API client (Tasks, Goals, Agent)
│   └── storage.ts           # Local storage wrappers
├── hooks/
│   ├── use-toast.ts         # Toast notification hook
│   └── use-mobile.tsx       # Viewport detection
├── lib/
│   └── utils.ts             # Tailwind merging utility (cn)
├── types/
│   └── database.ts          # Shared types (mirrors backend schemas)
└── assets/                  # Static assets
```

## Workflows

### 1. Agent Interaction
- **Component**: `AgentChat.tsx`
- **Flow**: User types message -> `agentApi.sendMessage` -> Updates chat history -> Handles "Actions" (create/update tasks) returned by agent.

### 2. Task Management
- **Components**: `UpcomingTasks.tsx`, `TaskCard.tsx`
- **State**: React Query (`useQuery(['tasks'])`).
- **Updates**: Optimistic updates using mutation triggers (`taskApi`).

## Services & API (`src/services/api.ts`)

The `api` module provides typed functions for backend interaction:

```typescript
// Agent
agentApi.sendMessage(request: ChatRequest): Promise<ChatResponse>

// Resources
taskApi.getAll(userId): Promise<Task[]>
taskApi.create(data): Promise<Task>
goalApi.getAll(userId): Promise<Goal[]>
```

## Styling System

Tailwind is configured with a custom theme in `tailwind.config.ts`.

### Key Colors (HSL)
- **Primary (Coral)**: `hsl(8 75% 65%)` - Actions, Highlights
- **Secondary (Cyan)**: `hsl(195 85% 50%)` - Info, Calm
- **Success**: `hsl(155 65% 45%)` - Completion
- **Background**: `hsl(0 0% 100%)` / `hsl(222 47% 11%)` (Dark mode)

### Patterns
- **Glassmorphism**: `.glass-card` utility.
- **Micro-interactions**: `.animate-scale-in`, `.animate-fade-in`.

## Commands

```bash
# Development Server
npm run dev

# Build for Production
npm run build

# Preview Production Build
npm run preview

# Linting
npm run lint
```

## Environment Variables (.env)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Implementation URL for backend (default: `http://localhost:8000`) |

## Guidelines

- **Components**: Use `src/components/ui` for primitives. Build domain components in `src/components/`.
- **Async**: Use `useQuery` for fetching and `useMutation` for updates.
- **Types**: Define shared data models in `src/types/`.
- **Accessibility**: Use Radix UI primitives for complex interactive components (Dialogs, Popovers).
