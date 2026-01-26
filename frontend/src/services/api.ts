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
