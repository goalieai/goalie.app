import { supabase } from "@/lib/supabase";
import {
    Task,
    TaskCreate,
    TaskUpdate,
    Goal,
    GoalCreate,
    GoalUpdate,
} from "@/types/database";

// Helper to ensure supabase is available
function getSupabase() {
    if (!supabase) {
        throw new Error("Supabase client not initialized");
    }
    return supabase;
}

export const supabaseStore = {
    // ===========================================================================
    // TASKS
    // ===========================================================================
    tasks: {
        getAll: async (userId: string): Promise<Task[]> => {
            const client = getSupabase();
            const { data, error } = await client
                .from("tasks")
                .select("*")
                .eq("user_id", userId)
                .order("created_at", { ascending: false });

            if (error) throw error;
            return data as Task[];
        },

        create: async (userId: string, data: TaskCreate): Promise<Task> => {
            const client = getSupabase();
            const { data: task, error } = await client
                .from("tasks")
                .insert({
                    user_id: userId,
                    task_name: data.task_name,
                    estimated_minutes: data.estimated_minutes ?? 15,
                    energy_required: data.energy_required ?? "medium",
                    assigned_anchor: data.assigned_anchor ?? null,
                    rationale: data.rationale ?? null,
                    status: "pending",
                    created_by: "user",
                    goal_id: data.goal_id ?? null,
                    session_id: data.session_id ?? null,
                    scheduled_text: data.scheduled_text ?? null,
                    scheduled_at: data.scheduled_at ?? null,
                })
                .select()
                .single();

            if (error) throw error;
            return task as Task;
        },

        update: async (userId: string, id: string, data: TaskUpdate): Promise<Task> => {
            const client = getSupabase();
            const { data: task, error } = await client
                .from("tasks")
                .update(data)
                .eq("id", id)
                .eq("user_id", userId) // RLS safety
                .select()
                .single();

            if (error) throw error;
            return task as Task;
        },

        delete: async (userId: string, id: string): Promise<void> => {
            const client = getSupabase();
            const { error } = await client
                .from("tasks")
                .delete()
                .eq("id", id)
                .eq("user_id", userId); // RLS safety

            if (error) throw error;
        },

        complete: async (userId: string, id: string): Promise<Task> => {
            return supabaseStore.tasks.update(userId, id, { status: "completed" });
        },
    },

    // ===========================================================================
    // GOALS
    // ===========================================================================
    goals: {
        getAll: async (userId: string): Promise<Goal[]> => {
            const client = getSupabase();
            const { data, error } = await client
                .from("goals")
                .select("*")
                .eq("user_id", userId)
                .order("created_at", { ascending: false });

            if (error) throw error;
            return data as Goal[];
        },

        create: async (userId: string, data: GoalCreate): Promise<Goal> => {
            const client = getSupabase();
            const { data: goal, error } = await client
                .from("goals")
                .insert({
                    user_id: userId,
                    title: data.title,
                    description: data.description ?? null,
                    emoji: data.emoji ?? "🎯",
                    status: "active",
                    target_date: data.target_date ?? null,
                    session_id: data.session_id ?? null,
                })
                .select()
                .single();

            if (error) throw error;
            return goal as Goal;
        },

        update: async (userId: string, id: string, data: GoalUpdate): Promise<Goal> => {
            const client = getSupabase();
            const { data: goal, error } = await client
                .from("goals")
                .update(data)
                .eq("id", id)
                .eq("user_id", userId) // RLS safety
                .select()
                .single();

            if (error) throw error;
            return goal as Goal;
        },

        delete: async (userId: string, id: string): Promise<void> => {
            const client = getSupabase();
            const { error } = await client
                .from("goals")
                .delete()
                .eq("id", id)
                .eq("user_id", userId); // RLS safety

            if (error) throw error;
        },
    },
};
