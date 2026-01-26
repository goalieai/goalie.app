import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { getStore } from "@/services/store";
import { TaskCreate, TaskUpdate } from "@/types/database";

export function useTasks() {
    const { user, isGuest } = useAuth();
    const store = getStore(user?.id ?? null);

    return useQuery({
        queryKey: ["tasks", user?.id ?? "guest"],
        queryFn: () => store.tasks.getAll(),
        enabled: !isGuest || true, // Always enabled (guest uses localStorage)
    });
}

export function useCreateTask() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: TaskCreate) => store.tasks.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useUpdateTask() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) =>
            store.tasks.update(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useDeleteTask() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (taskId: string) => store.tasks.delete(taskId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useCompleteTask() {
    const { user } = useAuth();
    const store = getStore(user?.id ?? null);
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (taskId: string) => store.tasks.complete(taskId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}
