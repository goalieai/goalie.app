import {
    createContext,
    useContext,
    useEffect,
    useState,
    useCallback,
    ReactNode,
} from "react";
import { User, AuthError } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { storageApi } from "@/services/storage";

interface AuthContextType {
    user: User | null;
    isGuest: boolean;
    isLoading: boolean;
    signUp: (email: string, password: string) => Promise<{ error: AuthError | null }>;
    signInWithPassword: (email: string, password: string) => Promise<{ error: AuthError | null }>;
    signOut: () => Promise<void>;
    migrateGuestData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const GUEST_DATA_KEYS = ["goalie_tasks", "goalie_goals"];

function hasGuestData(): boolean {
    return GUEST_DATA_KEYS.some((key) => {
        const data = localStorage.getItem(key);
        if (!data) return false;
        try {
            const parsed = JSON.parse(data);
            return Array.isArray(parsed) && parsed.length > 0;
        } catch {
            return false;
        }
    });
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Initialize auth state
    useEffect(() => {
        if (!supabase) {
            // No Supabase configured, stay in guest mode
            setIsLoading(false);
            return;
        }

        // Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null);
            setIsLoading(false);
        });

        // Listen for auth changes
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => subscription.unsubscribe();
    }, []);

    const signUp = useCallback(async (email: string, password: string) => {
        if (!supabase) {
            return { error: { message: "Supabase not configured" } as AuthError };
        }
        const { error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                emailRedirectTo: window.location.origin,
            },
        });
        return { error };
    }, []);

    const signInWithPassword = useCallback(async (email: string, password: string) => {
        if (!supabase) {
            return { error: { message: "Supabase not configured" } as AuthError };
        }
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        return { error };
    }, []);

    const signOut = useCallback(async () => {
        if (!supabase) return;
        await supabase.auth.signOut();
        setUser(null);
    }, []);

    // Migrate localStorage data to Supabase after login
    const migrateGuestData = useCallback(async () => {
        if (!supabase || !user) return;
        if (!hasGuestData()) return;

        try {
            // Get guest data
            const guestTasks = await storageApi.tasks.getAll();
            const guestGoals = await storageApi.goals.getAll();

            // Insert goals first (tasks may reference them)
            for (const goal of guestGoals) {
                const { id, user_id, created_at, updated_at, ...goalData } = goal;
                await supabase.from("goals").insert({
                    ...goalData,
                    user_id: user.id,
                });
            }

            // Insert tasks
            for (const task of guestTasks) {
                const { id, user_id, created_at, updated_at, goal_id, ...taskData } = task;
                await supabase.from("tasks").insert({
                    ...taskData,
                    user_id: user.id,
                    goal_id: null, // Don't migrate goal references (IDs changed)
                });
            }

            // Clear guest data after successful migration
            GUEST_DATA_KEYS.forEach((key) => localStorage.removeItem(key));

            console.log("Guest data migrated successfully");
        } catch (error) {
            console.error("Failed to migrate guest data:", error);
            throw error;
        }
    }, [user]);

    // Auto-migrate guest data when a user signs in
    useEffect(() => {
        if (user && hasGuestData()) {
            migrateGuestData();
        }
    }, [user, migrateGuestData]);

    const value: AuthContextType = {
        user,
        isGuest: !user,
        isLoading,
        signUp,
        signInWithPassword,
        signOut,
        migrateGuestData,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
