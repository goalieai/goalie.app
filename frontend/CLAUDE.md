# Goally Frontend

ADHD-friendly productivity app for managing New Year's resolutions through objective breakdown and micro-task management.

## Tech Stack

- **Framework:** React 19 + TypeScript 5.9
- **Build Tool:** Vite 7
- **Router:** React Router DOM 7
- **Styling:** Tailwind CSS 3.4 + tailwindcss-animate
- **Components:** Radix UI primitives
- **Icons:** Lucide React
- **Data Fetching:** TanStack React Query 5
- **Notifications:** Sonner + custom toast hook
- **Theme:** next-themes (dark mode support)

## Project Structure

```
src/
├── pages/              # Route-level components
│   ├── Index.tsx       # Main dashboard
│   └── NotFound.tsx    # 404 page
├── components/
│   ├── goalie/         # Domain-specific components
│   │   ├── AddObjectiveModal.tsx
│   │   ├── CurrentFocus.tsx
│   │   ├── DashboardHeader.tsx
│   │   ├── ObjectiveProgress.tsx
│   │   ├── ReplanCard.tsx
│   │   └── UpcomingTasks.tsx
│   └── ui/             # Reusable Radix-based UI components
├── hooks/              # Custom React hooks
│   ├── use-toast.ts    # Toast state management
│   └── use-mobile.tsx  # Mobile viewport detection
├── lib/
│   └── utils.ts        # cn() class name utility
├── types/
│   └── goalie.ts       # TypeScript interfaces
└── assets/             # Images and static files
```

## Commands

```bash
npm run dev      # Start dev server (port 5173)
npm run build    # TypeScript check + production build
npm run lint     # Run ESLint
npm run preview  # Preview production build
```

## Key Types

```typescript
interface MicroTask {
  id: string;
  title: string;
  estimatedMinutes: number;
  scheduledTime?: string;
  status: 'pending' | 'in-progress' | 'completed' | 'replanning';
  suggestedNewTime?: string;
}

interface Objective {
  id: string;
  title: string;
  emoji: string;
  progress: number;
  microTasks: MicroTask[];
  dueDate?: string;
}
```

## Styling System

### Design Tokens (index.css)

- **Primary (Coral):** `hsl(8 75% 65%)` - CTAs, active states
- **Secondary (Cyan):** `hsl(195 85% 50%)` - Calm, verified
- **Success:** `hsl(155 65% 45%)` - Completed tasks
- **Replan:** `hsl(38 90% 55%)` - Adaptive state

### Fonts

- **Body:** Nunito (400-800)
- **Display:** Space Grotesk (400-700)

### Custom Utilities

- `.gradient-coral`, `.gradient-cyan`, `.gradient-success`
- `.glass-card` - Glassmorphism effect
- `.animate-pulse-soft`, `.animate-slide-up`, `.animate-bounce-soft`

## Component Patterns

### UI Components (CVA pattern)

```typescript
const buttonVariants = cva(baseStyles, {
  variants: { variant: {...}, size: {...} }
})
```

### Path Alias

`@/` maps to `./src/` in imports.

## Conventions

- **Components:** PascalCase (`AddObjectiveModal.tsx`)
- **Hooks:** camelCase with `use` prefix (`useToast`)
- **Types:** PascalCase interfaces
- **Handlers:** camelCase (`handleCompleteTask`)

## Environment Variables

```
VITE_API_BASE_URL=http://localhost:8000
```

## Backend Integration

The frontend is prepared for FastAPI backend connection:

1. Create `src/services/` for API clients
2. Use TanStack React Query for server state
3. Extend `types/goalie.ts` with backend response types
4. Use Sonner toast for error handling
