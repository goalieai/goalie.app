const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ChatResponse {
  response: string;
}

export const agentApi = {
  sendMessage: async (message: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    const data: ChatResponse = await res.json();
    return data.response;
  },

  healthCheck: async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  },
};
