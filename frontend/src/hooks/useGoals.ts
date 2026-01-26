import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { getStore } from "@/services/store";
import { GoalCreate, GoalUpdate } from "@/types/database";

export function useGoals() {
    const { user, isGuest } = useAuth();
    const store = getStore(user?.id ?? null);

    return useQuery({
        queryKey: ["goals", user?.id ?? "guest"],
        queryFn: () => store.goals.getAll(),
        enabled: !isGuest || true, // Always enabled (guest uses localStorage)
    });
}

export function useCreateGoal() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: GoalCreate) => store.goals.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}

export function useUpdateGoal() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
            store.goals.update(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}

export function useDeleteGoal() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (goalId: string) => store.goals.delete(goalId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}
