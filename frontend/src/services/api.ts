import {
  Task,
  TaskCreate,
  TaskUpdate,
  Goal,
  GoalCreate,
  GoalUpdate,
} from "../types/database";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// =============================================================================
// Types
// =============================================================================

export interface Action {
  type: "create_task" | "complete_task" | "create_goal" | "update_task";
  data: Record<string, unknown>;
}

export interface Progress {
  completed: number;
  total: number;
  percentage: number;
}

export interface MicroTask {
  task_name: string;
  estimated_minutes: number;
  energy_required: "high" | "medium" | "low";
  assigned_anchor: string;
  rationale: string;
}

export interface Plan {
  project_name: string;
  smart_goal_summary: string;
  deadline: string;
  tasks: MicroTask[];
}

export interface ChatResponse {
  session_id: string;
  intent_detected: "casual" | "planning" | "coaching" | "modify" | "unknown";
  response: string;
  plan?: Plan;
  progress?: Progress;
  actions: Action[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  user_profile?: {
    name: string;
    role?: string;
    anchors?: string[];
  };
}

// =============================================================================
// API Client
// =============================================================================

export const agentApi = {
  /**
   * Send a message to the AI agent.
   * Returns full response with actions for frontend processing.
   */
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    return res.json();
  },

  /**
   * Health check endpoint.
   */
  healthCheck: async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  },
};

// =============================================================================
// Task API
// =============================================================================

export const taskApi = {
  getAll: async (userId: string): Promise<Task[]> => {
    const res = await fetch(`${API_BASE}/api/tasks?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch tasks");
    return res.json();
  },

  create: async (data: TaskCreate & { user_id: string }): Promise<Task> => {
    // Extract user_id to query param, rest to body
    const { user_id, ...body } = data;
    const res = await fetch(`${API_BASE}/api/tasks?user_id=${user_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Failed to create task");
    return res.json();
  },

  update: async (
    taskId: string,
    data: TaskUpdate & { user_id: string },
  ): Promise<Task> => {
    const { user_id, ...body } = data;
    const res = await fetch(
      `${API_BASE}/api/tasks/${taskId}?user_id=${user_id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
    if (!res.ok) throw new Error("Failed to update task");
    return res.json();
  },

  delete: async (taskId: string, userId: string): Promise<void> => {
    const res = await fetch(
      `${API_BASE}/api/tasks/${taskId}?user_id=${userId}`,
      {
        method: "DELETE",
      },
    );
    if (!res.ok) throw new Error("Failed to delete task");
  },

  complete: async (taskId: string, userId: string): Promise<Task> => {
    // Convenience method, just calls update
    return taskApi.update(taskId, { user_id: userId, status: "completed" });
  },
};

// =============================================================================
// Goal API
// =============================================================================

export const goalApi = {
  getAll: async (userId: string): Promise<Goal[]> => {
    const res = await fetch(`${API_BASE}/api/goals?user_id=${userId}`);
    if (!res.ok) throw new Error("Failed to fetch goals");
    return res.json();
  },

  create: async (data: GoalCreate & { user_id: string }): Promise<Goal> => {
    const { user_id, ...body } = data;
    const res = await fetch(`${API_BASE}/api/goals?user_id=${user_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Failed to create goal");
    return res.json();
  },

  update: async (
    goalId: string,
    data: GoalUpdate & { user_id: string },
  ): Promise<Goal> => {
    const { user_id, ...body } = data;
    const res = await fetch(
      `${API_BASE}/api/goals/${goalId}?user_id=${user_id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
    if (!res.ok) throw new Error("Failed to update goal");
    return res.json();
  },

  delete: async (goalId: string, userId: string): Promise<void> => {
    const res = await fetch(
      `${API_BASE}/api/goals/${goalId}?user_id=${userId}`,
      {
        method: "DELETE",
      },
    );
    if (!res.ok) throw new Error("Failed to delete goal");
  },
};
