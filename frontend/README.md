# Goally Frontend

ADHD-friendly productivity dashboard for managing New Year's resolutions through micro-task management and AI coaching.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.2 | UI Framework |
| TypeScript | 5.9 | Type Safety |
| Vite | 7.2 | Build Tool |
| React Router | 7.13 | Routing |
| Tailwind CSS | 3.4 | Styling |
| Radix UI | Latest | Accessible Primitives |
| TanStack Query | 5.90 | Server State |
| Lucide React | 0.563 | Icons |
| Sonner | 2.0 | Toast Notifications |

## Project Structure

```
src/
├── pages/                    # Route-level components
│   ├── Index.tsx             # Main dashboard (307 lines)
│   └── NotFound.tsx          # 404 page
│
├── components/
│   ├── ui/                   # Radix-based primitives (43 components)
│   │   ├── button.tsx        # CVA-based button variants
│   │   ├── card.tsx          # Card + CardHeader/Content/Footer
│   │   ├── dialog.tsx        # Modal dialogs
│   │   ├── input.tsx         # Form inputs
│   │   ├── sonner.tsx        # Toast configuration
│   │   └── ...
│   │
│   ├── AgentChat.tsx         # Sidebar chat with AI coach
│   ├── AgentFeedback.tsx     # Contextual suggestions
│   ├── AvatarSelector.tsx    # Emoji avatar picker
│   ├── DashboardHeader.tsx   # Greeting + progress summary
│   ├── MedalTask.tsx         # Completed task with medal
│   ├── MotivationalQuote.tsx # Inspirational quotes
│   ├── ProgressSpiral.tsx    # SVG circular progress
│   ├── SectionHeader.tsx     # Section titles (NOW/NEXT/ACHIEVED)
│   └── TaskCard.tsx          # Task with Done/Re-plan actions
│
├── hooks/
│   ├── use-toast.ts          # Toast state management
│   └── use-mobile.tsx        # Mobile viewport detection (768px)
│
├── lib/
│   └── utils.ts              # cn() className utility
│
├── assets/
│   └── goalie-logo.jpeg      # Mascot logo
│
├── App.tsx                   # Root component + routing
├── App.css                   # Global styles
├── main.tsx                  # Entry point
└── index.css                 # Tailwind + CSS variables
```

## Commands

```bash
pnpm dev      # Start dev server (port 5173)
pnpm build    # TypeScript check + production build
pnpm lint     # Run ESLint
pnpm preview  # Preview production build locally
```

## Design System

### Color Palette

| Token | HSL Value | Usage |
|-------|-----------|-------|
| Primary | `25 95% 53%` | Orange - CTAs, energy |
| Secondary | `35 40% 94%` | Cream - backgrounds |
| Success | `140 50% 45%` | Green - completed |
| Replan | `38 90% 55%` | Amber - adaptive |

### Typography

- **Body:** Nunito (400-800)
- **Display:** Space Grotesk (400-700)

### Custom CSS Classes

```css
.section-now      /* Current focus section */
.section-next     /* Upcoming tasks section */
.section-achieved /* Completed tasks section */
.agent-bubble     /* AI chat message */
.user-bubble      /* User chat message */
.pulse-focus      /* Attention animation */
.animate-spiral   /* Progress animation */
```

## Component Patterns

### CVA (Class Variance Authority)

```typescript
const buttonVariants = cva(baseStyles, {
  variants: {
    variant: { default: "...", destructive: "...", outline: "..." },
    size: { default: "h-10", sm: "h-8", lg: "h-12" }
  },
  defaultVariants: { variant: "default", size: "default" }
})
```

### Path Alias

`@/` maps to `./src/` for clean imports:

```typescript
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
```

## Dashboard Sections

1. **YOUR GOALIE (NOW)** - Current focus task with prominent actions
2. **NEXT** - Upcoming micro-tasks in responsive grid
3. **ACHIEVED** - Completed tasks with medals for dopamine

## Key Interfaces

```typescript
interface Message {
  id: string
  content: string
  sender: "agent" | "user"
  timestamp: Date
}

interface Suggestion {
  id: string
  message: string
  type: "reschedule" | "break" | "motivation"
}

interface Task {
  id: string
  action: string
  time: string  // e.g., "9:00 AM - 10:30 AM"
}
```

## UX Principles

- **Miller's Law** - Max 3+1 visible sections
- **Fitts' Law** - Large touch targets (56-64px)
- **ADHD-Friendly** - Clear visual hierarchy, micro-tasks
- **Immediate Feedback** - Celebration animations on completion

## Environment Variables

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Backend Integration

Prepared for FastAPI connection:

1. Create `src/services/api.ts` for HTTP clients
2. Use TanStack Query for server state management
3. Handle errors with Sonner toast notifications
