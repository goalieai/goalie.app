import { storageApi } from "./storage";
import { supabaseStore } from "./supabaseStore";
import {
    Task,
    TaskCreate,
    TaskUpdate,
    Goal,
    GoalCreate,
    GoalUpdate,
} from "@/types/database";

/**
 * Unified store interface for tasks and goals.
 * Abstracts the underlying storage (localStorage vs Supabase).
 */
export interface Store {
    tasks: {
        getAll(): Promise<Task[]>;
        create(data: TaskCreate): Promise<Task>;
        update(id: string, data: TaskUpdate): Promise<Task>;
        delete(id: string): Promise<void>;
        complete(id: string): Promise<Task>;
    };
    goals: {
        getAll(): Promise<Goal[]>;
        create(data: GoalCreate): Promise<Goal>;
        update(id: string, data: GoalUpdate): Promise<Goal>;
        delete(id: string): Promise<void>;
    };
}

/**
 * Creates a store bound to localStorage (guest mode).
 * No user ID needed - data is stored locally.
 */
export function createGuestStore(): Store {
    return {
        tasks: {
            getAll: () => storageApi.tasks.getAll(),
            create: (data) => storageApi.tasks.create(data),
            update: (id, data) => storageApi.tasks.update(id, data),
            delete: (id) => storageApi.tasks.delete(id),
            complete: (id) => storageApi.tasks.update(id, { status: "completed" }),
        },
        goals: {
            getAll: () => storageApi.goals.getAll(),
            create: (data) => storageApi.goals.create(data),
            update: (id, data) => storageApi.goals.update(id, data),
            delete: (id) => storageApi.goals.delete(id),
        },
    };
}

/**
 * Creates a store bound to Supabase for a specific user.
 * Requires a valid user ID from authentication.
 */
export function createUserStore(userId: string): Store {
    return {
        tasks: {
            getAll: () => supabaseStore.tasks.getAll(userId),
            create: (data) => supabaseStore.tasks.create(userId, data),
            update: (id, data) => supabaseStore.tasks.update(userId, id, data),
            delete: (id) => supabaseStore.tasks.delete(userId, id),
            complete: (id) => supabaseStore.tasks.complete(userId, id),
        },
        goals: {
            getAll: () => supabaseStore.goals.getAll(userId),
            create: (data) => supabaseStore.goals.create(userId, data),
            update: (id, data) => supabaseStore.goals.update(userId, id, data),
            delete: (id) => supabaseStore.goals.delete(userId, id),
        },
    };
}

/**
 * Factory function to get the appropriate store based on auth state.
 */
export function getStore(userId: string | null): Store {
    if (!userId) {
        return createGuestStore();
    }
    return createUserStore(userId);
}
