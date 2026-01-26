// Auto-generated types matching Supabase schema
// Run migration first: backend/app/migrations/001_init_schema.sql

export interface Profile {
  id: string; // UUID, matches auth.users.id
  first_name: string | null;
  preferences: UserPreferences;
  updated_at: string; // ISO timestamp
}

export interface UserPreferences {
  timezone?: string;
  working_hours?: { start: string; end: string };
  anchors?: string[]; // Daily habit anchors for task scheduling
  theme?: "light" | "dark" | "system";
}

export interface Session {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  last_active: string;
}

export interface Goal {
  id: string;
  user_id: string;
  session_id: string | null;
  title: string;
  description: string | null;
  emoji: string;
  status: "active" | "achieved" | "archived";
  target_date: string | null; // ISO timestamp
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  user_id: string;
  goal_id: string | null;
  session_id: string | null;
  task_name: string;
  scheduled_text: string | null; // "Tomorrow morning", "After coffee"
  scheduled_at: string | null; // ISO timestamp for sorting
  estimated_minutes: number;
  energy_required: "high" | "medium" | "low";
  assigned_anchor: string | null;
  rationale: string | null;
  status: "pending" | "in_progress" | "completed";
  created_by: "user" | "agent";
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  user_id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "function";
  content: string | null;
  metadata: MessageMetadata;
  created_at: string;
}

export interface MessageMetadata {
  tokens?: { input: number; output: number };
  model?: string;
  tool_calls?: ToolCall[];
  duration_ms?: number;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

// ============================================
// Input types for creating/updating records
// ============================================

export interface ProfileUpdate {
  first_name?: string;
  preferences?: Partial<UserPreferences>;
}

export interface GoalCreate {
  title: string;
  description?: string;
  emoji?: string;
  target_date?: string;
  session_id?: string;
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  emoji?: string;
  status?: "active" | "achieved" | "archived";
  target_date?: string;
}

export interface TaskCreate {
  task_name: string;
  goal_id?: string;
  session_id?: string;
  scheduled_text?: string;
  scheduled_at?: string;
  estimated_minutes?: number;
  energy_required?: "high" | "medium" | "low";
  assigned_anchor?: string;
  rationale?: string;
}

export interface TaskUpdate {
  task_name?: string;
  scheduled_text?: string;
  scheduled_at?: string;
  estimated_minutes?: number;
  energy_required?: "high" | "medium" | "low";
  status?: "pending" | "in_progress" | "completed";
}

export interface SessionCreate {
  title?: string;
}

// ============================================
// API Response helpers
// ============================================

export interface PaginatedResponse<T> {
  data: T[];
  count: number;
  has_more: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}
