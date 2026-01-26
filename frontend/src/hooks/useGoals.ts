import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { goalApi } from "@/services/api";
import { storageApi } from "@/services/storage";
import { GoalCreate, GoalUpdate } from "@/types/database";

// TODO: Replace with real user ID from auth context
const USER_ID = "a7bed60b-dcb6-458c-b17b-f51b0c73fd7d";

// If no user ID, we treat as guest
const IS_GUEST = !USER_ID;

export function useGoals() {
    return useQuery({
        queryKey: ["goals", USER_ID || "guest"],
        queryFn: async () => {
            if (IS_GUEST) {
                return storageApi.goals.getAll();
            }
            return goalApi.getAll(USER_ID);
        },
    });
}

export function useCreateGoal() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: GoalCreate) => {
            if (IS_GUEST) {
                return storageApi.goals.create(data);
            }
            return goalApi.create({ ...data, user_id: USER_ID });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}

export function useUpdateGoal() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) => {
            if (IS_GUEST) {
                return storageApi.goals.update(id, data);
            }
            return goalApi.update(id, { ...data, user_id: USER_ID });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}

export function useDeleteGoal() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (goalId: string) => {
            if (IS_GUEST) {
                return storageApi.goals.delete(goalId);
            }
            return goalApi.delete(goalId, USER_ID);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["goals"] });
        },
    });
}
