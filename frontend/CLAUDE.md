# Frontend Guide - Goally

## Overview

Goally's frontend is a **React 19** Single Page Application (SPA) built with **Vite** and **TypeScript**. It features a modern, accessible UI using **Radix UI** primitives and **Tailwind CSS**, with Supabase for authentication.

## Tech Stack

- **Core**: React 19 + TypeScript 5.9
- **Build**: Vite 7
- **Routing**: React Router DOM 7
- **Styling**: Tailwind CSS 3.4 + `tailwindcss-animate`
- **UI Components**: Radix UI (Headless accessible components)
- **State/Fetching**: TanStack React Query 5
- **Authentication**: Supabase Auth
- **Icons**: Lucide React
- **Notifications**: Sonner

## Project Structure

```
src/
├── pages/
│   ├── Index.tsx            # Main Dashboard (Goals + Tasks + Agent Chat)
│   └── NotFound.tsx         # 404 Route
├── components/
│   ├── ui/                  # Reusable Design System (Button, Card, Input...)
│   ├── AgentChat.tsx        # AI Chat Interface (sidebar)
│   ├── TaskCard.tsx         # Micro-task display & management
│   ├── DashboardHeader.tsx  # User greeting, login button
│   ├── LoginDialog.tsx      # Auth modal (Supabase)
│   ├── AddTaskForm.tsx      # Manual task creation
│   ├── AddGoalForm.tsx      # Manual goal creation
│   ├── SectionHeader.tsx    # Section titles with icons
│   ├── ProgressSpiral.tsx   # SVG circular progress
│   └── ...
├── contexts/
│   └── AuthContext.tsx      # Supabase auth state provider
├── hooks/
│   ├── useTasks.ts          # React Query hooks for tasks
│   ├── useGoals.ts          # React Query hooks for goals
│   ├── use-toast.ts         # Toast notifications
│   └── use-mobile.tsx       # Viewport detection
├── services/
│   ├── api.ts               # Typed API client (Agent, Tasks, Goals)
│   └── supabase.ts          # Supabase client instance
├── lib/
│   └── utils.ts             # Tailwind merging utility (cn)
├── types/
│   └── database.ts          # Shared types (mirrors backend)
└── assets/                  # Static assets (logo, images)
```

## Authentication Flow

**Provider:** Supabase Auth (Magic Link / OAuth)

```
AuthContext.tsx
    |
    v
useAuth() -> { user, session, isGuest, signIn, signOut }
    |
    v
Index.tsx -> Conditional rendering based on auth state
```

- **Guest users**: Can use agent chat (in-memory, no persistence)
- **Authenticated users**: Full persistence to Supabase

## Data Flow

### 1. Agent Interaction (`Index.tsx` + `AgentChat.tsx`)

```
User types message
    |
    v
agentApi.sendMessage({ message, session_id, user_id, user_profile })
    |
    v
Backend returns: { response, actions[], intent_detected }
    |
    v
processAction() -> Creates tasks/goals via API
    |
    v
React Query invalidation -> UI updates
```

### 2. Action Processing

The agent returns `actions[]` which the frontend processes:

```typescript
interface Action {
  type: "create_task" | "create_goal" | "complete_task" | "update_task";
  data: Record<string, unknown>;
}

// Processing in Index.tsx
switch (action.type) {
  case "create_task":
    await taskApi.create({ ...data, user_id });
    queryClient.invalidateQueries(["tasks"]);
    break;
  case "create_goal":
    await goalApi.create({ title: data.title, user_id });
    queryClient.invalidateQueries(["goals"]);
    break;
}
```

### 3. Task Management

**Hooks:** `useTasks.ts`
- `useTasks()` - Fetch all tasks for user
- `useCompleteTask()` - Mutation to mark task complete

**State mapping:**
```typescript
tasks = {
  now: firstPendingTask,      // Current focus
  next: remainingPending[],   // Coming up
  achieved: completedTasks[]  // Done today
}
```

## Services & API (`src/services/api.ts`)

```typescript
// Agent
agentApi.sendMessage(request: ChatRequest): Promise<ChatResponse>

// Tasks
taskApi.getAll(userId): Promise<Task[]>
taskApi.create(data): Promise<Task>
taskApi.complete(taskId, userId): Promise<Task>

// Goals
goalApi.getAll(userId): Promise<Goal[]>
goalApi.create(data): Promise<Goal>
```

## Styling System

### Theme (`tailwind.config.ts`)

**Key Colors (HSL):**
- **Primary (Orange)**: `hsl(25 95% 53%)` - Energy, motivation, CTAs
- **Secondary (Cream)**: `hsl(35 40% 94%)` - Calm backgrounds
- **Success**: `hsl(140 50% 45%)` - Completed tasks
- **Warning**: `hsl(45 95% 55%)` - Attention
- **Achieved**: `hsl(45 50% 95%)` - Achievement section bg

**Section Classes:**
- `.section-now` - Orange tinted background
- `.section-next` - Cream background
- `.section-achieved` - Golden/warm background

### Dashboard Layout (Miller's Law)

Three sections optimized for ADHD:
1. **YOUR GOALIE** - Current goals + NOW task
2. **NEXT** - Upcoming tasks (max 4-5)
3. **ACHIEVED** - Completed tasks (dopamine reward)

## Commands

```bash
# Development
pnpm dev          # or npm run dev

# Build
pnpm build        # Production build

# Preview
pnpm preview      # Preview production build

# Lint
pnpm lint
```

## Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | Yes | Backend URL (default: `http://localhost:8000`) |
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |

## Code Conventions

- **Components**: PascalCase, one component per file
- **Hooks**: `use` prefix, in `hooks/` directory
- **API calls**: Through `services/api.ts`, never direct fetch
- **State**: React Query for server state, useState for UI state
- **Styling**: Tailwind classes, use `cn()` for conditional classes
- **Types**: Define in `types/` or co-locate with components

## UX Principles (ADHD-Friendly)

- **Miller's Law**: Max 3+1 sections visible
- **Fitts' Law**: Large touch targets (56-64px buttons)
- **Micro-tasks**: 5-20 minute estimates
- **Immediate feedback**: Animations on completion
- **Gamification**: Points, medals in achieved section

## Future Enhancements (Planned)

- [ ] Google Calendar sync for scheduling
- [ ] User confirmation dialog before agent creates items
- [ ] Offline support with service worker
- [ ] Push notifications for task reminders
