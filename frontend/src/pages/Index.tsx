import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { Clock, MessageCircle, X, Medal } from "lucide-react";
import { Action } from "@/services/api";
import { getStore } from "@/services/store";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useTasks, useCompleteTask } from "@/hooks/useTasks";
import { useGoals } from "@/hooks/useGoals";
import { useStreamingChat } from "@/hooks/useStreamingChat";
import DashboardHeader from "@/components/DashboardHeader";
import TaskCard from "@/components/TaskCard";
import SectionHeader from "@/components/SectionHeader";
import ProgressSpiral from "@/components/ProgressSpiral";
import AgentChat from "@/components/AgentChat";
import AddTaskForm from "@/components/AddTaskForm";
import AddGoalForm from "@/components/AddGoalForm";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import goalieLogo from "@/assets/goalie-logo.jpeg";

// Empty state for tasks
const emptyTasks = {
  now: null,
  next: [],
  achieved: [],
};

interface Message {
  id: string;
  content: string;
  sender: "agent" | "user";
  timestamp: Date;
}

const Index = () => {
  // Auth
  const { user, isGuest } = useAuth();

  // Queries
  const { data: tasksData } = useTasks();
  const { data: goalsData, isLoading: isLoadingGoals } = useGoals();
  const completeTask = useCompleteTask();
  const queryClient = useQueryClient();

  // Local state for UI only
  const [messages, setMessages] = useState<Message[]>([]);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Streaming chat hook
  const streaming = useStreamingChat();

  // Session management for conversation continuity
  const sessionIdRef = useRef<string | null>(null);

  // Derived state for Tasks
  const tasks = useMemo(() => {
    if (!tasksData) return emptyTasks;

    // Map tasks to UI format
    const achieved = tasksData
      .filter((t) => t.status === "completed")
      .map((t) => ({
        id: t.id,
        action: t.task_name,
        time: t.scheduled_text || new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }));

    const pending = tasksData.filter((t) => t.status !== "completed");

    // Simple logic: First pending task is 'now', rest are 'next'
    // Future: Use 'scheduled_at' to sort
    const nowTask = pending.length > 0 ? pending[0] : null;

    const now = nowTask ? {
      id: nowTask.id,
      action: nowTask.task_name,
      time: nowTask.scheduled_text || "Now"
    } : null;

    const next = pending.length > 1 ? pending.slice(1).map((t) => ({
      id: t.id,
      action: t.task_name,
      time: t.scheduled_text || "Later"
    })) : [];

    return { now, next, achieved };
  }, [tasksData]);

  // Derived state for Goals
  const goals = useMemo(() => {
    return goalsData || [];
  }, [goalsData]);

  const currentDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const completedCount = tasks.achieved.length;
  const totalCount = (tasks.now ? 1 : 0) + tasks.next.length + tasks.achieved.length;

  const handleCompleteNow = useCallback(() => {
    if (tasks.now) {
      completeTask.mutate(tasks.now.id);

      // Agent celebrates (optimistic UI update via React Query invalidation in background)
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `m${Date.now()}`,
            content: "🎉 Amazing work! You completed your task. Take a moment to appreciate that win!",
            sender: "agent" as const,
            timestamp: new Date(),
          },
        ]);
      }, 500);
    }
  }, [tasks.now, completeTask]);

  const handleReplanNow = useCallback(() => {
    setMessages((prev) => [
      ...prev,
      {
        id: `m${Date.now()}`,
        content: "No problem! Let's figure out a better time for this task. What's getting in the way?",
        sender: "agent" as const,
        timestamp: new Date(),
      },
    ]);
    setIsChatOpen(true);
  }, []);

  // Process actions returned by the AI agent
  // Uses the unified store (localStorage for guests, Supabase for authenticated)
  const processAction = useCallback(async (action: Action) => {
    const { type, data } = action;
    const userId = user?.id ?? null;
    const store = getStore(userId);

    try {
      switch (type) {
        case "create_task": {
          console.log("[Action] Creating task:", data, "userId:", userId ?? "guest");
          await store.tasks.create({
            task_name: (data.task_name || data.action) as string,
            estimated_minutes: (data.estimated_minutes as number) || 15,
            energy_required: (data.energy_required as "high" | "medium" | "low") || "medium",
            scheduled_text: data.assigned_anchor as string,
            assigned_anchor: data.assigned_anchor as string,
            rationale: data.rationale as string,
          });
          queryClient.invalidateQueries({ queryKey: ["tasks"] });
          break;
        }

        case "complete_task": {
          const taskId = data.task_id as string;
          if (taskId) {
            await store.tasks.complete(taskId);
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
          }
          break;
        }

        case "create_goal": {
          console.log("[Action] Creating goal:", data, "userId:", userId ?? "guest");
          await store.goals.create({
            title: (data.title || data.goal) as string,
            emoji: (data.emoji as string) || "🎯",
          });
          queryClient.invalidateQueries({ queryKey: ["goals"] });
          break;
        }

        case "update_task": {
          queryClient.invalidateQueries({ queryKey: ["tasks"] });
          break;
        }

        case "refresh_ui": {
          // Refresh all queries to sync UI with storage
          console.log("[Action] Refreshing UI");
          queryClient.invalidateQueries({ queryKey: ["tasks"] });
          queryClient.invalidateQueries({ queryKey: ["goals"] });
          break;
        }
      }
    } catch (error) {
      console.error("[Action] Failed to process action:", type, error);
    }
  }, [queryClient, user?.id]);

  // Handle streaming result when it arrives
  useEffect(() => {
    if (streaming.result) {
      // Store session ID for conversation continuity
      sessionIdRef.current = streaming.result.session_id;

      // Add agent response to chat
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-${Date.now()}`,
          content: streaming.result!.response,
          sender: "agent" as const,
          timestamp: new Date(),
        },
      ]);

      // Process any actions from the agent
      if (streaming.result.actions && streaming.result.actions.length > 0) {
        console.log("[Agent] Processing actions:", streaming.result.actions.length);
        Promise.all(streaming.result.actions.map(processAction));
      }
    }
  }, [streaming.result, processAction]);

  // Handle streaming errors
  useEffect(() => {
    if (streaming.error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-${Date.now()}`,
          content: "Sorry, I'm having trouble connecting. Please try again.",
          sender: "agent" as const,
          timestamp: new Date(),
        },
      ]);
    }
  }, [streaming.error]);

  const handleSendMessage = useCallback(async (content: string) => {
    // Add user message to chat
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        content,
        sender: "user" as const,
        timestamp: new Date(),
      },
    ]);

    // Send via streaming endpoint
    await streaming.sendMessage({
      message: content,
      session_id: sessionIdRef.current || undefined,
      user_id: user?.id,
      user_profile: {
        name: isGuest ? "Guest" : user?.email?.split("@")[0] || "there",
      },
    });
  }, [streaming, isGuest, user]);

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        {/* Main Content */}
        <main className="flex-1 p-6 lg:p-8 max-w-6xl mx-auto">
          <DashboardHeader currentDate={currentDate} />

          {/* Three Section Layout - Miller's Law */}
          <div className="grid gap-6 lg:gap-8">
            {/* NOW Section - Your Goalie Goals */}
            <section className="section-now rounded-2xl border-2 p-4 sm:p-6 lg:p-8">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-2xl sm:text-3xl font-bold text-primary">YOUR GOALIE</h2>
                <ProgressSpiral
                  completed={completedCount}
                  total={totalCount}
                  className="w-14 h-14 sm:w-20 sm:h-20"
                />
              </div>

              {/* User Goals List */}
              <div className="mb-6 space-y-2">
                {isLoadingGoals ? (
                  <div className="text-muted-foreground">Loading goals...</div>
                ) : (
                  goals.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 text-foreground">
                      <span className="text-lg">{item.emoji}</span>
                      <span className="text-base sm:text-lg font-medium">{item.title}</span>
                    </div>
                  ))
                )}
                {/* Fallback for empty state if not loading */}
                {!isLoadingGoals && goals.length === 0 && (
                  <p className="text-muted-foreground italic">No goals yet. Add one!</p>
                )}
                <div className="pt-2">
                  <AddGoalForm />
                </div>
              </div>

              {tasks.now ? (
                <TaskCard
                  action={tasks.now.action}
                  time={tasks.now.time}
                  isCurrentFocus
                  onComplete={handleCompleteNow}
                  onReplan={handleReplanNow}
                />
              ) : (
                <div className="p-4 bg-muted/20 rounded-lg text-center text-muted-foreground">
                  No task scheduled for now. Take a break!
                </div>
              )}
            </section>

            {/* NEXT Section - Preparation */}
            <section className="section-next rounded-2xl border-2 p-4 sm:p-6 lg:p-8">
              <div className="flex justify-between items-center mb-4">
                <SectionHeader
                  icon={Clock}
                  title="Next"
                  subtitle="Coming up"
                  variant="next"
                />
                <AddTaskForm />
              </div>
              <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
                {tasks.next.map((task) => (
                  <TaskCard
                    key={task.id}
                    action={task.action}
                    time={task.time}
                    onComplete={() => completeTask.mutate(task.id)}
                    onReplan={() => { }}
                  />
                ))}
              </div>
            </section>

            {/* ACHIEVED Section - Gamified Dopamine Rush */}
            <section className="rounded-2xl border-2 border-primary/50 p-4 sm:p-6 lg:p-8 bg-gradient-to-br from-primary/40 via-warning/30 to-primary/20 shadow-lg">
              {/* Logo + Medal Header */}
              <div className="flex items-center gap-4 mb-6">
                <div className="relative">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl overflow-hidden shadow-lg ring-4 ring-primary/30 animate-fade-in">
                    <img src={goalieLogo} alt="Goalie" className="w-full h-full object-cover" />
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-gradient-to-br from-medal-from to-medal-to rounded-full flex items-center justify-center shadow-lg">
                    <Medal className="w-4 h-4 text-primary-foreground" />
                  </div>
                </div>
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-primary">Achieved 🎉</h2>
                  <p className="text-sm sm:text-base text-muted-foreground font-medium">{completedCount} tasks completed today!</p>
                </div>
              </div>

              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                {tasks.achieved.map((task) => (
                  <TaskCard
                    key={task.id}
                    action={task.action}
                    time={task.time}
                    completed
                    onComplete={() => { }}
                    onReplan={() => { }}
                  />
                ))}
              </div>
            </section>
          </div>

        </main>

        {/* Agent Chat Sidebar - Trading Chat */}
        <aside
          className={cn(
            "fixed right-0 top-0 h-full w-full sm:w-96 bg-background border-l shadow-xl transform transition-transform duration-300 ease-out z-50",
            isChatOpen ? "translate-x-0" : "translate-x-full"
          )}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsChatOpen(false)}
            className="absolute top-4 left-4 z-10 rounded-full"
          >
            <X className="w-5 h-5" />
          </Button>
          <div className="h-full pt-16 pb-4 px-4">
            <AgentChat
              messages={messages}
              onSendMessage={handleSendMessage}
              streamingState={{
                isStreaming: streaming.isStreaming,
                status: streaming.status,
                currentStep: streaming.currentStep,
                completedSteps: streaming.completedSteps,
                progress: streaming.progress,
              }}
            />
          </div>
        </aside>

        {/* Chat Toggle Button */}
        <Button
          onClick={() => setIsChatOpen(true)}
          className={cn(
            "fixed bottom-6 right-6 h-14 w-14 rounded-full bg-primary shadow-lg hover:bg-primary/90 hover:scale-105 transition-all z-40",
            isChatOpen && "hidden"
          )}
        >
          <MessageCircle className="w-6 h-6" />
        </Button>
      </div>
    </div>
  );
};

export default Index;
