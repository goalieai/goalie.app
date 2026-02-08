import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface GoogleAccount {
  id: string;
  email: string;
}

interface GoogleStatus {
  connected: boolean;
  accounts: GoogleAccount[];
}

export function useGoogleCalendar(userId: string | undefined) {
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery<GoogleStatus>({
    queryKey: ["google-calendar-status", userId],
    queryFn: async () => {
      // console.log("[GOOGLE DEBUG] Fetching status for user_id:", userId);
      const res = await fetch(`${API_BASE}/api/google/status?user_id=${userId}`);
      if (!res.ok) throw new Error("Failed to check Google Calendar status");
      return res.json();
    },
    enabled: !!userId,
  });

  const connect = useCallback(async () => {
    if (!userId) return;
    const res = await fetch(`${API_BASE}/api/google/auth-url?user_id=${userId}`);
    const { auth_url } = await res.json();
    window.location.href = auth_url;
  }, [userId]);

  const disconnectMutation = useMutation({
    mutationFn: async (googleEmail?: string) => {
      const params = new URLSearchParams({ user_id: userId! });
      if (googleEmail) params.set("google_email", googleEmail);
      const res = await fetch(`${API_BASE}/api/google/disconnect?${params}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to disconnect");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["google-calendar-status"] });
    },
  });

  return {
    isConnected: status?.connected ?? false,
    accounts: status?.accounts ?? [],
    isLoading,
    connect,
    disconnect: disconnectMutation.mutate,
    isDisconnecting: disconnectMutation.isPending,
  };
}
