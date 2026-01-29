import { Check, Loader2, Brain, Target, ListTodo, Calendar, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { PipelineStep, StreamProgress } from "@/hooks/useStreamingChat";

interface PipelineProgressProps {
  currentStep: PipelineStep | null;
  completedSteps: PipelineStep[];
  progress: StreamProgress;
  status: string | null;
  /** Compact mode for narrow containers */
  compact?: boolean;
}

interface StepConfig {
  id: PipelineStep;
  label: string;
  shortLabel: string;
  icon: React.ElementType;
}

const STEPS: StepConfig[] = [
  { id: "intent", label: "Understanding", shortLabel: "Intent", icon: Brain },
  { id: "smart", label: "SMART Goal", shortLabel: "SMART", icon: Target },
  { id: "tasks", label: "Micro-tasks", shortLabel: "Tasks", icon: ListTodo },
  { id: "schedule", label: "Scheduling", shortLabel: "Schedule", icon: Calendar },
  { id: "response", label: "Your Plan", shortLabel: "Plan", icon: MessageSquare },
];

export function PipelineProgress({
  currentStep,
  completedSteps,
  progress,
  status,
  compact = true,
}: PipelineProgressProps) {
  const getStepState = (stepId: PipelineStep): "pending" | "active" | "completed" => {
    if (completedSteps.includes(stepId)) return "completed";
    if (currentStep === stepId) return "active";
    return "pending";
  };

  return (
    <div className="w-full space-y-3">
      {/* Step indicators - scrollable on narrow containers */}
      <div className="overflow-x-auto scrollbar-hide -mx-1 px-1">
        <div className={cn(
          "flex items-center",
          compact ? "gap-1 min-w-max" : "justify-between px-2"
        )}>
          {STEPS.map((step, index) => {
            const state = getStepState(step.id);
            const Icon = step.icon;

            return (
              <div key={step.id} className="flex items-center">
                {/* Step circle */}
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={cn(
                      "rounded-full flex items-center justify-center transition-all duration-300",
                      compact ? "w-8 h-8" : "w-10 h-10",
                      state === "completed" && "bg-success text-white",
                      state === "active" && "bg-primary text-white ring-2 ring-primary/20",
                      state === "pending" && "bg-muted text-muted-foreground"
                    )}
                  >
                    {state === "completed" ? (
                      <Check className={cn(compact ? "w-4 h-4" : "w-5 h-5")} />
                    ) : state === "active" ? (
                      <Loader2 className={cn(compact ? "w-4 h-4" : "w-5 h-5", "animate-spin")} />
                    ) : (
                      <Icon className={cn(compact ? "w-4 h-4" : "w-5 h-5")} />
                    )}
                  </div>
                  <span
                    className={cn(
                      "font-medium transition-colors text-center whitespace-nowrap",
                      compact ? "text-[10px]" : "text-xs",
                      state === "completed" && "text-success",
                      state === "active" && "text-primary",
                      state === "pending" && "text-muted-foreground"
                    )}
                  >
                    {compact ? step.shortLabel : step.label}
                  </span>
                </div>

                {/* Connector line */}
                {index < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "h-0.5 transition-colors duration-300",
                      compact ? "w-4 mx-0.5" : "w-8 mx-1",
                      completedSteps.includes(STEPS[index + 1].id) ||
                        currentStep === STEPS[index + 1].id
                        ? "bg-primary"
                        : "bg-muted"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Status message */}
      {status && (
        <div className="text-center text-sm text-muted-foreground animate-pulse">
          {status}
        </div>
      )}

      {/* Progress cards */}
      <div className="space-y-3">
        {/* SMART Goal card */}
        {progress.smart_goal && (
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 animate-fade-in">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Target className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-xs font-medium text-primary uppercase tracking-wide mb-1">
                  Your SMART Goal
                </p>
                <p className="text-sm text-foreground leading-relaxed">
                  {progress.smart_goal.summary}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Raw tasks preview */}
        {progress.raw_tasks && progress.raw_tasks.length > 0 && (
          <div className="bg-secondary/30 border border-secondary rounded-xl p-4 animate-fade-in">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                <ListTodo className="w-4 h-4 text-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  Breaking it down into {progress.raw_tasks.length} tasks
                </p>
                <ul className="space-y-1.5">
                  {progress.raw_tasks.slice(0, 4).map((task, i) => (
                    <li
                      key={i}
                      className="text-sm text-foreground truncate flex items-center gap-2"
                    >
                      <span className="w-5 h-5 rounded-full bg-background border text-xs flex items-center justify-center flex-shrink-0">
                        {i + 1}
                      </span>
                      <span className="truncate">{task}</span>
                    </li>
                  ))}
                  {progress.raw_tasks.length > 4 && (
                    <li className="text-xs text-muted-foreground pl-7">
                      +{progress.raw_tasks.length - 4} more tasks...
                    </li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PipelineProgress;
