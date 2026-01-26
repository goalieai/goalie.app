import {
    Task,
    TaskCreate,
    TaskUpdate,
    Goal,
    GoalCreate,
    GoalUpdate,
} from "../types/database";

const TASKS_KEY = "goalie_tasks";
const GOALS_KEY = "goalie_goals";

// Helper to generate UUIDs
function generateId(): string {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Helper to get data
function getLocal<T>(key: string): T[] {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
}

// Helper to set data
function setLocal<T>(key: string, data: T[]) {
    localStorage.setItem(key, JSON.stringify(data));
}

export const storageApi = {
    // ===========================================================================
    // TASKS
    // ===========================================================================
    tasks: {
        getAll: async (): Promise<Task[]> => {
            // Simulate network delay
            await new Promise((resolve) => setTimeout(resolve, 100));
            return getLocal<Task>(TASKS_KEY).sort((a, b) =>
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
        },

        create: async (data: TaskCreate): Promise<Task> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const tasks = getLocal<Task>(TASKS_KEY);

            const newTask: Task = {
                id: generateId(),
                user_id: "guest",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                task_name: data.task_name,
                estimated_minutes: data.estimated_minutes || 15,
                energy_required: data.energy_required || "medium",
                assigned_anchor: data.assigned_anchor || null,
                rationale: data.rationale || null,
                status: "pending",
                created_by: "user",
                goal_id: data.goal_id || null,
                session_id: data.session_id || null,
                scheduled_text: data.scheduled_text || null,
                scheduled_at: data.scheduled_at || null,
            };

            tasks.push(newTask);
            setLocal(TASKS_KEY, tasks);
            return newTask;
        },

        update: async (id: string, data: TaskUpdate): Promise<Task> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const tasks = getLocal<Task>(TASKS_KEY);
            const index = tasks.findIndex((t) => t.id === id);

            if (index === -1) throw new Error("Task not found");

            const updatedTask = {
                ...tasks[index],
                ...data,
                updated_at: new Date().toISOString(),
            };

            tasks[index] = updatedTask;
            setLocal(TASKS_KEY, tasks);
            return updatedTask;
        },

        delete: async (id: string): Promise<void> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const tasks = getLocal<Task>(TASKS_KEY);
            const newTasks = tasks.filter((t) => t.id !== id);
            setLocal(TASKS_KEY, newTasks);
        },
    },

    // ===========================================================================
    // GOALS
    // ===========================================================================
    goals: {
        getAll: async (): Promise<Goal[]> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            return getLocal<Goal>(GOALS_KEY).sort((a, b) =>
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
        },

        create: async (data: GoalCreate): Promise<Goal> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const goals = getLocal<Goal>(GOALS_KEY);

            const newGoal: Goal = {
                id: generateId(),
                user_id: "guest",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                title: data.title,
                description: data.description || null,
                emoji: data.emoji || "🎯",
                status: "active",
                target_date: data.target_date || null,
                session_id: data.session_id || null,
            };

            goals.push(newGoal);
            setLocal(GOALS_KEY, goals);
            return newGoal;
        },

        update: async (id: string, data: GoalUpdate): Promise<Goal> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const goals = getLocal<Goal>(GOALS_KEY);
            const index = goals.findIndex((g) => g.id === id);

            if (index === -1) throw new Error("Goal not found");

            const updatedGoal = {
                ...goals[index],
                ...data,
                updated_at: new Date().toISOString(),
            };

            goals[index] = updatedGoal;
            setLocal(GOALS_KEY, goals);
            return updatedGoal;
        },

        delete: async (id: string): Promise<void> => {
            await new Promise((resolve) => setTimeout(resolve, 100));
            const goals = getLocal<Goal>(GOALS_KEY);
            const newGoals = goals.filter((g) => g.id !== id);
            setLocal(GOALS_KEY, newGoals);
        },
    },
};
