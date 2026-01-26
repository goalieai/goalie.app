import { useState, useCallback, useRef } from "react";
import { Clock, Trophy, MessageCircle, X, Medal } from "lucide-react";
import { agentApi, Action } from "@/services/api";
import DashboardHeader from "@/components/DashboardHeader";
import TaskCard from "@/components/TaskCard";
import SectionHeader from "@/components/SectionHeader";
import AgentFeedback from "@/components/AgentFeedback";
import AgentChat from "@/components/AgentChat";
import MedalTask from "@/components/MedalTask";
import MotivationalQuote from "@/components/MotivationalQuote";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import goalieLogo from "@/assets/goalie-logo.jpeg";

// Initial goals data
const initialGoals = [
  { id: "g1", goal: "Learn Spanish", emoji: "🇪🇸" },
  { id: "g2", goal: "Go to the gym", emoji: "💪" },
  { id: "g3", goal: "Read 20 pages daily", emoji: "📚" },
];

// Sample data
const initialTasks = {
  now: { id: "1", action: "Write project proposal draft", time: "9:00 AM - 10:30 AM" },
  next: [
    { id: "2", action: "Review team feedback", time: "11:00 AM" },
    { id: "3", action: "Prepare presentation slides", time: "2:00 PM" },
  ],
  achieved: [
    { id: "4", action: "Morning meditation", time: "7:30 AM" },
    { id: "5", action: "Check emails", time: "8:00 AM" },
  ],
};

const initialSuggestions = [
  {
    id: "s1",
    message: "You've been working for 45 minutes. Would you like to take a 5-minute break?",
    type: "break" as const,
  },
  {
    id: "s2",
    message: "I noticed 'Review team feedback' might take longer than planned. Should I move it to 11:30 AM?",
    type: "reschedule" as const,
  },
];

interface Message {
  id: string;
  content: string;
  sender: "agent" | "user";
  timestamp: Date;
}

const initialMessages: Message[] = [
  {
    id: "m1",
    content: "Hey! 👋 I see you're about to start your project proposal. Remember, you've got this! Just focus on getting your ideas down first.",
    sender: "agent",
    timestamp: new Date(),
  },
];

const Index = () => {
  const [tasks, setTasks] = useState(initialTasks);
  const [goals, setGoals] = useState(initialGoals);
  const [suggestions, setSuggestions] = useState(initialSuggestions);
  const [messages, setMessages] = useState(initialMessages);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  // Session management for conversation continuity
  const sessionIdRef = useRef<string | null>(null);

  const currentDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const completedCount = tasks.achieved.length;
  const totalCount = 1 + tasks.next.length + tasks.achieved.length;

  const handleCompleteNow = useCallback(() => {
    if (tasks.now) {
      setTasks((prev) => ({
        ...prev,
        achieved: [
          { ...prev.now!, time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) },
          ...prev.achieved,
        ],
        now: prev.next[0] || null,
        next: prev.next.slice(1),
      }));

      // Agent celebrates
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
  }, [tasks]);

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

  const handleAcceptSuggestion = useCallback((id: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const handleDismissSuggestion = useCallback((id: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  // Process actions returned by the AI agent
  const processAction = useCallback((action: Action) => {
    const { type, data } = action;

    switch (type) {
      case "create_task": {
        const newTask = {
          id: `task-${Date.now()}`,
          action: (data.action as string) || (data.task_name as string) || "New task",
          time: (data.time as string) || (data.scheduled_time as string) || "Anytime",
        };
        setTasks((prev) => ({
          ...prev,
          next: [...prev.next, newTask],
        }));
        break;
      }

      case "complete_task": {
        const taskId = data.task_id as string;
        const taskName = data.task_name as string;
        setTasks((prev) => {
          // Find task by ID or name
          const findTask = (t: { id: string; action: string }) =>
            t.id === taskId || t.action.toLowerCase().includes((taskName || "").toLowerCase());

          // Check if it's the current task
          if (prev.now && findTask(prev.now)) {
            return {
              ...prev,
              achieved: [
                { ...prev.now, time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) },
                ...prev.achieved,
              ],
              now: prev.next[0] || null,
              next: prev.next.slice(1),
            };
          }

          // Check in next tasks
          const taskIndex = prev.next.findIndex(findTask);
          if (taskIndex !== -1) {
            const completedTask = prev.next[taskIndex];
            return {
              ...prev,
              achieved: [
                { ...completedTask, time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) },
                ...prev.achieved,
              ],
              next: prev.next.filter((_, i) => i !== taskIndex),
            };
          }

          return prev;
        });
        break;
      }

      case "create_goal": {
        const newGoal = {
          id: `goal-${Date.now()}`,
          goal: (data.goal as string) || "New goal",
          emoji: (data.emoji as string) || "🎯",
        };
        setGoals((prev) => [...prev, newGoal]);
        break;
      }

      case "update_task": {
        // Future: handle task updates
        console.log("update_task action:", data);
        break;
      }
    }
  }, []);

  const handleSendMessage = useCallback(async (content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        content,
        sender: "user" as const,
        timestamp: new Date(),
      },
    ]);

    setIsTyping(true);

    try {
      const response = await agentApi.sendMessage({
        message: content,
        session_id: sessionIdRef.current || undefined,
        user_profile: { name: "Alex" },
      });

      // Store session ID for conversation continuity
      sessionIdRef.current = response.session_id;

      // Add agent response to chat
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-${Date.now()}`,
          content: response.response,
          sender: "agent" as const,
          timestamp: new Date(),
        },
      ]);

      // Process any actions from the agent
      if (response.actions && response.actions.length > 0) {
        response.actions.forEach(processAction);
      }

    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: `agent-${Date.now()}`,
          content: "Sorry, I'm having trouble connecting. Please try again.",
          sender: "agent" as const,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  }, [processAction]);

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        {/* Main Content */}
        <main className="flex-1 p-6 lg:p-8 max-w-6xl mx-auto">
          <DashboardHeader
            userName="Alex"
            completedTasks={completedCount}
            totalTasks={totalCount}
            currentDate={currentDate}
          />

          {/* Three Section Layout - Miller's Law */}
          <div className="grid gap-6 lg:gap-8">
            {/* NOW Section - Your Goalie Goals */}
            <section className="section-now rounded-2xl border-2 p-4 sm:p-6 lg:p-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-4">YOUR GOALIE</h2>
              
              {/* User Goals List */}
              <div className="mb-6 space-y-2">
                {goals.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 text-foreground">
                    <span className="text-lg">{item.emoji}</span>
                    <span className="text-base sm:text-lg font-medium">{item.goal}</span>
                  </div>
                ))}
              </div>

              {tasks.now && (
                <TaskCard
                  action={tasks.now.action}
                  time={tasks.now.time}
                  isCurrentFocus
                  onComplete={handleCompleteNow}
                  onReplan={handleReplanNow}
                />
              )}
            </section>

            {/* NEXT Section - Preparation */}
            <section className="section-next rounded-2xl border-2 p-4 sm:p-6 lg:p-8">
              <SectionHeader
                icon={Clock}
                title="Next"
                subtitle="Coming up"
                variant="next"
              />
              <MedalTask task="Morning Meditation" completed className="mb-4" />
              <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
                {tasks.next.map((task) => (
                  <TaskCard
                    key={task.id}
                    action={task.action}
                    time={task.time}
                    onComplete={() => {}}
                    onReplan={() => {}}
                  />
                ))}
              </div>
            </section>

            {/* ACHIEVED Section - Dopamine */}
            <section className="section-achieved rounded-2xl border-2 p-4 sm:p-6 lg:p-8 bg-gradient-to-br from-primary/10 via-warning/10 to-primary/5">
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
                    onComplete={() => {}}
                    onReplan={() => {}}
                  />
                ))}
              </div>
            </section>
          </div>

          {/* Agent Feedback - Calendar Suggestions */}
          {suggestions.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-4 text-foreground">
                Goalie's Suggestions
              </h3>
              <AgentFeedback
                suggestions={suggestions}
                onAccept={handleAcceptSuggestion}
                onDismiss={handleDismissSuggestion}
              />
            </div>
          )}

          {/* Motivational Quote */}
          <MotivationalQuote quote="I FEELING GOOD" author="Elon Musk" />
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
              isTyping={isTyping}
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
