# Frontend Guide - Goally

## Overview

Goally's frontend is a **React 19** Single Page Application (SPA) built with **Vite 7** and **TypeScript 5.9**. It features an ADHD-friendly task dashboard with real-time AI agent integration via SSE streaming, Supabase authentication with guest fallback, Google Calendar integration, and a unified storage abstraction layer.

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Core** | React 19.2 + TypeScript 5.9 |
| **Build** | Vite 7.2 |
| **Routing** | React Router DOM 7.13 |
| **Styling** | Tailwind CSS 3.4 + `tailwindcss-animate` |
| **UI Primitives** | Radix UI (49 headless components) |
| **Data Fetching** | TanStack React Query 5.90 |
| **Auth/DB** | Supabase JS 2.91 (optional — guest mode if unconfigured) |
| **Icons** | Lucide React 0.563 |
| **Markdown** | react-markdown 10.1 |
| **Charts** | Recharts 3.7 |
| **Notifications** | Sonner 2.0 |
| **Forms** | react-hook-form 7.71 |
| **Testing** | Vitest 4.0 |

## Project Structure

```
src/
├── pages/
│   ├── Index.tsx               # Main dashboard (NOW / NEXT / ACHIEVED + Agent Chat sidebar)
│   ├── GoogleConnected.tsx     # OAuth callback landing page (success/error → redirect)
│   └── NotFound.tsx            # 404 catch-all
├── components/
│   ├── ui/                     # 49 Radix-based primitives (button, card, dialog, sheet, etc.)
│   ├── AgentChat.tsx           # AI chat sidebar (SSE streaming, pipeline progress, plan preview)
│   ├── AgentFeedback.tsx       # Contextual suggestion cards (reschedule, break, motivation)
│   ├── TaskCard.tsx            # Task with Done/Re-plan actions, time badge, focus animation
│   ├── PlanPreview.tsx         # Staged plan display with Confirm/Modify buttons (HITL)
│   ├── PipelineProgress.tsx    # Visual step indicator (Intent → Smart → Tasks → Schedule → Plan)
│   ├── ProgressSpiral.tsx      # SVG circular progress ring
│   ├── DashboardHeader.tsx     # Time-based greeting + auth button + Google Calendar button
│   ├── GoogleConnectButton.tsx # Connect/disconnect Google Calendar (shows email when connected)
│   ├── AddTaskForm.tsx         # Dialog: create task (name, minutes, energy)
│   ├── AddGoalForm.tsx         # Dialog: create goal (emoji + title)
│   ├── LoginDialog.tsx         # Magic link auth (Supabase OTP)
│   ├── SectionHeader.tsx       # Section title with icon + variant coloring
│   ├── MedalTask.tsx           # Completed task with logo + checkbox badge
│   ├── MotivationalQuote.tsx   # Quote display (primary text + attribution)
│   ├── NavLink.tsx             # React Router NavLink wrapper with active/pending classes
│   └── AvatarSelector.tsx      # Emoji avatar picker (6 options grid)
├── contexts/
│   └── AuthContext.tsx         # Supabase auth + guest mode + data migration
├── hooks/
│   ├── useStreamingChat.ts     # SSE streaming, HITL staging, Socratic clarification, pipeline state
│   ├── useGoogleCalendar.ts    # Google Calendar connection status, connect, disconnect
│   ├── useTasks.ts             # TanStack Query CRUD: useTasks, useCreateTask, useUpdateTask, useDeleteTask, useCompleteTask
│   ├── useGoals.ts             # TanStack Query CRUD: useGoals, useCreateGoal, useUpdateGoal, useDeleteGoal
│   ├── use-mobile.tsx          # useIsMobile() — true if viewport < 768px
│   └── use-toast.ts            # Toast state management (limit 1)
├── services/
│   ├── api.ts                  # REST client (agentApi, taskApi, goalApi) + types
│   ├── store.ts                # Unified store factory: getStore(userId) → guest or Supabase
│   ├── storage.ts              # Guest store: localStorage (goalie_tasks, goalie_goals)
│   └── supabaseStore.ts        # Auth store: Supabase client with RLS
├── lib/
│   ├── utils.ts                # cn() — clsx + tailwind-merge
│   └── supabase.ts             # Supabase client singleton (null if unconfigured)
├── types/
│   └── database.ts             # All entity interfaces (Task, Goal, Profile, Session, Message)
├── test/
│   ├── setup.ts                # Vitest setup
│   └── example.test.ts
├── App.tsx                     # Router + QueryClientProvider + AuthProvider + TooltipProvider + Toaster
├── main.tsx                    # ReactDOM.createRoot entry
└── index.css                   # Tailwind directives + CSS custom properties + animations
```

## Architecture

### Dashboard Layout (Index.tsx)

Three sections following Miller's Law (ADHD-friendly):

```
┌──────────────────────────────────────┬──────────────────┐
│  DashboardHeader (greeting + auth    │                  │
│    + Google Calendar button)         │                  │
├──────────────────────────────────────┤   AgentChat      │
│  YOUR GOALIE (NOW section)           │   (sidebar,      │
│  - Goal emoji + title                │    fixed right,   │
│  - Current task (Done / Re-plan)     │    toggleable)   │
│  - ProgressSpiral                    │                  │
├──────────────────────────────────────┤  Features:       │
│  NEXT section                        │  - SSE streaming │
│  - Task grid (2-col responsive)      │  - Pipeline viz  │
│  - Add Task button                   │  - Plan preview  │
├──────────────────────────────────────┤  - HITL confirm  │
│  ACHIEVED section                    │  - Clarification │
│  - Medal tasks (3-col grid)          │                  │
│  - Motivational header              │                  │
└──────────────────────────────────────┴──────────────────┘
                                    [Chat Toggle FAB]
```

**Task state derivation:**
```typescript
const tasks = useMemo(() => ({
  now: Task | null,        // First pending task
  next: Task[],            // Remaining pending
  achieved: Task[]         // Completed tasks
}), [tasksData])
```

### Data Flow

#### 1. SSE Streaming Chat (primary path)

```
User types message
  │
  ▼
useStreamingChat.sendMessage()
  │
  ▼  POST /api/chat/stream
SSEBuffer handles chunked responses
  │
  ├─ "status" events → pipeline step updates (PipelineProgress)
  ├─ "progress" events → smart_goal preview, raw_tasks list
  ├─ "clarification" events → Socratic Gatekeeper question
  └─ "complete" event
       │
       ├─ staging_plan present → PlanPreview (HITL: Confirm/Modify)
       ├─ actions[] present → processAction() → store mutations → query invalidation
       └─ response text → chat message bubble
```

#### 2. HITL Plan Confirmation

```
Agent generates plan
  │
  ▼
staging_plan set in useStreamingChat → PlanPreview rendered
  │
  ├─ User clicks "Save Plan" → handleConfirmPlan()
  │     └─ Creates tasks/goals in store + sends "confirm" message to agent
  │
  └─ User clicks "Modify" → handleModifyPlan()
        └─ Opens chat with "What would you like to change?" prompt
```

#### 3. Action Processing (Index.tsx → processAction)

```typescript
switch (action.type) {
  case "create_task"  → store.tasks.create(data) → invalidate ["tasks"]
  case "complete_task" → store.tasks.complete(id) → invalidate ["tasks"]
  case "create_goal"  → store.goals.create(data) → invalidate ["goals"]
  case "update_task"  → store.tasks.update(id, data) → invalidate ["tasks"]
  case "refresh_ui"   → invalidate all queries
}
```

### Google Calendar Integration

**Frontend components:**
- `GoogleConnectButton` — In DashboardHeader, shows connected email or "Connect Calendar" button
- `GoogleConnected` page — OAuth callback landing at `/google-connected`, auto-redirects to `/` after 2s
- `useGoogleCalendar(userId)` hook — TanStack Query for status, connect/disconnect

**Flow:**
1. User clicks "Connect Calendar" → `useGoogleCalendar.connect()` → fetches auth URL from backend → redirects to Google consent
2. Google redirects to `/api/google/callback` → backend stores tokens → redirects to `/google-connected?success=true`
3. `GoogleConnected` page shows success toast → redirects to dashboard
4. `GoogleConnectButton` now shows connected email with green checkmark

**Backend interaction:**
- `GET /api/google/status?user_id=X` — Check connection status (polled by TanStack Query)
- `GET /api/google/auth-url?user_id=X` — Get OAuth consent URL
- `POST /api/google/disconnect?user_id=X` — Remove tokens

### Storage Abstraction

```
getStore(userId)
  │
  ├─ userId is null → createGuestStore()
  │     └─ localStorage (goalie_tasks, goalie_goals)
  │     └─ crypto.randomUUID() for IDs (fallback: timestamp-based)
  │     └─ 100ms simulated delay
  │
  └─ userId present → createUserStore(userId)
        └─ Supabase client with RLS (eq("user_id", userId))
        └─ Real async operations

Both implement identical Store interface:
  store.tasks.getAll() / create() / update() / delete() / complete()
  store.goals.getAll() / create() / update() / delete()
```

### Authentication

**Provider:** Supabase Auth (Magic Link OTP)

```
AuthContext provides:
  user: User | null
  isGuest: boolean (true when user is null)
  isLoading: boolean
  signInWithMagicLink(email) → sends OTP email
  signOut()
  migrateGuestData() → moves localStorage → Supabase on first login
```

**Guest migration flow:**
1. Guest uses app → tasks/goals in localStorage
2. User signs in via magic link
3. `migrateGuestData()` reads localStorage keys
4. Inserts goals first, then tasks (with new user_id)
5. Clears localStorage keys

**Supabase optional:** If `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` are missing, the app runs in guest-only mode. `supabase` client exports as `null`, `isSupabaseConfigured` is `false`.

## Hooks Reference

### useStreamingChat()

The core hook managing SSE communication with the agent backend.

**Returns:**
```typescript
{
  // Pipeline state
  status: string | null              // Current step description
  currentStep: PipelineStep | null   // "intent" | "smart" | "tasks" | "schedule" | "response"
  completedSteps: PipelineStep[]
  progress: StreamProgress           // { smart_goal?: { summary }, raw_tasks?: string[] }

  // Result
  result: ChatResponse | null
  error: string | null
  isStreaming: boolean

  // HITL
  stagingPlan: Plan | null
  awaitingConfirmation: boolean
  clearStagingPlan: () => void

  // Socratic Gatekeeper
  clarification: ClarificationState | null  // { question, context, attempts }
  awaitingClarification: boolean

  // Actions
  sendMessage: (request: ChatRequest) => Promise<void>
  reset: () => void
}
```

**SSEBuffer:** Custom class that handles chunked SSE data from proxies (Vercel/Heroku may split mid-line). Looks for `data: ` prefix and `\n\n` delimiters.

**Node-to-step mapping:**
```typescript
intent_router → "intent"
smart_refiner → "smart"
task_splitter → "tasks"
context_matcher → "schedule"
planning_response / casual / coaching → "response"
```

### useGoogleCalendar(userId)

Google Calendar connection management.

**Returns:**
```typescript
{
  isConnected: boolean              // Whether user has Google tokens stored
  accounts: GoogleAccount[]         // { id, email }[]
  isLoading: boolean
  connect: () => Promise<void>      // Redirects to Google OAuth consent
  disconnect: (email?) => void      // Removes stored tokens
  isDisconnecting: boolean
}
```

**Query key:** `["google-calendar-status", userId]` — enabled only when userId is defined.

### useTasks() / useGoals()

TanStack Query hooks wrapping the unified store.

```typescript
// Query keys
["tasks", user?.id ?? "guest"]
["goals", user?.id ?? "guest"]

// All mutations auto-invalidate their query on success
useTasks()         → UseQueryResult<Task[]>
useCreateTask()    → UseMutationResult<Task, Error, TaskCreate>
useUpdateTask()    → UseMutationResult<Task, Error, { id, data }>
useDeleteTask()    → UseMutationResult<void, Error, string>
useCompleteTask()  → UseMutationResult<Task, Error, string>

useGoals()         → UseQueryResult<Goal[]>
useCreateGoal()    → UseMutationResult<Goal, Error, GoalCreate>
useUpdateGoal()    → UseMutationResult<Goal, Error, { id, data }>
useDeleteGoal()    → UseMutationResult<void, Error, string>
```

## Types (database.ts)

### Core Entities

```typescript
interface Task {
  id: string
  user_id: string
  goal_id: string | null
  session_id: string | null
  task_name: string
  scheduled_text: string | null     // "Tomorrow morning", "After coffee"
  scheduled_at: string | null       // ISO timestamp
  estimated_minutes: number
  energy_required: "high" | "medium" | "low"
  assigned_anchor: string | null
  rationale: string | null
  status: "pending" | "in_progress" | "completed"
  created_by: "user" | "agent"
  created_at: string
  updated_at: string
}

interface Goal {
  id: string
  user_id: string
  session_id: string | null
  title: string
  description: string | null
  emoji: string
  status: "active" | "achieved" | "archived"
  target_date: string | null
  created_at: string
  updated_at: string
}

interface Profile {
  id: string
  first_name: string | null
  preferences: UserPreferences  // { timezone?, working_hours?, anchors?, theme? }
  updated_at: string
}

interface Message {
  id: string
  user_id: string
  session_id: string
  role: "user" | "assistant" | "system" | "function"
  content: string | null
  metadata: MessageMetadata  // { tokens?, model?, tool_calls?, duration_ms? }
  created_at: string
}
```

### API Types (api.ts)

```typescript
interface Action {
  type: "create_task" | "complete_task" | "create_goal" | "update_task" | "refresh_ui"
  data: Record<string, unknown>
}

interface Plan {
  project_name: string
  smart_goal_summary: string
  deadline: string
  tasks: MicroTask[]  // { task_name, estimated_minutes, energy_required, assigned_anchor, rationale }
}

interface ChatResponse {
  session_id: string
  intent_detected: "casual" | "planning" | "planning_continuation" | "coaching" | "modify" | "confirm" | "unknown"
  response: string
  plan?: Plan
  progress?: Progress
  actions: Action[]
  staging_plan?: Plan
  awaiting_confirmation?: boolean
  awaiting_clarification?: boolean
  pending_context?: Record<string, unknown>
}

interface ChatRequest {
  message: string
  session_id?: string
  user_id?: string
  user_profile?: { name: string; role?: string; anchors?: string[] }
}
```

## Components Reference

### AgentChat

Props: `messages`, `onSendMessage`, `isTyping?`, `streamingState?`, `onConfirmPlan?`, `onModifyPlan?`, `isConfirmingPlan?`

- Renders message bubbles with markdown (ReactMarkdown)
- Special styling: "Goal:" lines get highlight box, anchor emojis get secondary bg
- Shows PipelineProgress during streaming
- Shows PlanPreview when staging plan exists (HITL)
- Clarification indicator (pulsing help icon) for Socratic Gatekeeper
- Auto-scrolls to bottom on new messages

### TaskCard

Props: `action`, `time`, `isCurrentFocus?`, `onComplete`, `onReplan`, `completed?`

- Current focus: border-primary/30, shadow-lg, pulse animation
- Completed: opacity-60, line-through, checkmark badge
- Fitts' Law buttons: h-12 sm:h-14 (56-64px)

### PlanPreview

Props: `plan: Plan`, `onConfirm`, `onModify`, `isLoading?`

- Anchor emoji mapping: Morning Coffee → sunrise, After Lunch → sun, End of Day → moon
- Task list with energy level colors and time estimates
- Max-h-64 scrollable task list
- Save Plan (primary) + Modify (outline) buttons

### PipelineProgress

Props: `currentStep`, `completedSteps`, `progress`, `status`, `compact?`

- 5 steps: Intent → Smart Goal → Tasks → Schedule → Response
- States: completed (green check), active (spinning loader), pending (muted icon)
- Shows SMART goal summary card and raw tasks list as they arrive

### GoogleConnectButton

Props: `userId: string | undefined`

- Shows nothing when no userId or loading
- Connected: green CalendarCheck icon + email, click to disconnect
- Disconnected: CalendarPlus icon + "Connect Calendar", click to start OAuth

### LoginDialog

- Magic link flow: email input → loading → "Check your email" confirmation
- Auto-closes when authenticated

## Styling System

### Colors (HSL custom properties in index.css)

| Token | Light | Purpose |
|-------|-------|---------|
| `--primary` | `25 95% 53%` | Orange — energy, motivation, CTAs |
| `--secondary` | `35 40% 94%` | Cream — calm backgrounds |
| `--success` | `140 50% 45%` | Green — completed tasks |
| `--destructive` | `0 70% 55%` | Red-orange — errors, delete |
| `--warning` | `45 95% 55%` | Golden amber — attention |
| `--now-bg` | `25 60% 96%` | Orange tint — NOW section |
| `--next-bg` | `35 50% 96%` | Warm tint — NEXT section |
| `--achieved-bg` | `45 50% 95%` | Gold tint — ACHIEVED section |
| `--agent-bg` | `30 35% 97%` | Agent chat background |

Dark mode inverts via `.dark` class. Border radius base: `1rem`.

### Fonts

- **Body:** Nunito (Google Fonts)
- **Display:** Space Grotesk

### Custom Animations (index.css + tailwind.config.ts)

- `spiral-progress` — ProgressSpiral ring fill
- `gentle-pulse` / `pulse-focus` — Current task attention
- `slide-up` — AgentFeedback suggestions
- `celebrate` — Task completion
- `fade-in` — General entrance (0.4s + translateY)
- `scale-in` — Pop entrance (0.3s)
- `swipe-left/right` — Exit animations

### Section Classes

- `.section-now` — Orange tinted bg
- `.section-next` — Cream bg
- `.section-achieved` — Golden/warm bg
- `.agent-bubble` / `.user-bubble` — Chat message styling
- `.scrollbar-hide` — Hide scrollbar
- `.chat-scroll` — Custom scrollbar for chat

## Commands

```bash
pnpm dev          # Development server (localhost:5173)
pnpm build        # Type-check + production build
pnpm preview      # Preview production build
pnpm lint         # ESLint
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Backend API URL |
| `VITE_SUPABASE_URL` | No | — | Supabase project URL (guest-only if missing) |
| `VITE_SUPABASE_ANON_KEY` | No | — | Supabase public anon key (guest-only if missing) |

## Conventions

- **Components:** PascalCase, one per file, in `components/`
- **Hooks:** `use` prefix, in `hooks/`
- **API calls:** Through `services/api.ts` or unified store, never direct fetch
- **Server state:** TanStack Query (query keys include userId for cache isolation)
- **UI state:** useState / useRef in components
- **Auth state:** React Context (`useAuth()`)
- **Styling:** Tailwind classes, `cn()` for conditional merging
- **Toasts:** Sonner (`import { toast } from "sonner"`)
- **Types:** Shared types in `types/database.ts`, API types co-located in `services/api.ts`
- **Path alias:** `@/` maps to `./src/`

## UX Principles (ADHD-Friendly)

- **Miller's Law:** Max 3 sections (NOW, NEXT, ACHIEVED)
- **Fitts' Law:** Large touch targets (56-64px buttons)
- **Micro-tasks:** 5-20 minute time estimates
- **Immediate feedback:** Animations on completion, medal badges
- **Zero friction:** Guest mode requires no signup
- **Gamification:** Medal tasks, progress spiral, celebration animations
