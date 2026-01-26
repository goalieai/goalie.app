import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { taskApi } from "@/services/api";
import { storageApi } from "@/services/storage";
import { TaskCreate, TaskUpdate } from "@/types/database";

// TODO: Replace with real user ID from auth context
const USER_ID = "a7bed60b-dcb6-458c-b17b-f51b0c73fd7d";

// If no user ID, we treat as guest
const IS_GUEST = !USER_ID;

export function useTasks() {
    return useQuery({
        queryKey: ["tasks", USER_ID || "guest"],
        queryFn: async () => {
            if (IS_GUEST) {
                return storageApi.tasks.getAll();
            }
            return taskApi.getAll(USER_ID);
        },
    });
}

export function useCreateTask() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: TaskCreate) => {
            if (IS_GUEST) {
                return storageApi.tasks.create(data);
            }
            return taskApi.create({ ...data, user_id: USER_ID });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useUpdateTask() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) => {
            if (IS_GUEST) {
                return storageApi.tasks.update(id, data);
            }
            return taskApi.update(id, { ...data, user_id: USER_ID });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useDeleteTask() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (taskId: string) => {
            if (IS_GUEST) {
                return storageApi.tasks.delete(taskId);
            }
            return taskApi.delete(taskId, USER_ID);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}

export function useCompleteTask() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (taskId: string) => {
            if (IS_GUEST) {
                // For guest, complete is just an update
                return storageApi.tasks.update(taskId, { status: "completed" });
            }
            return taskApi.complete(taskId, USER_ID);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
        },
    });
}
