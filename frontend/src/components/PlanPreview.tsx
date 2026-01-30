import { Check, Edit3, Clock, Zap, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Plan, MicroTask } from "@/services/api";

interface PlanPreviewProps {
  plan: Plan;
  onConfirm: () => void;
  onModify: () => void;
  isLoading?: boolean;
}

// Anchor emoji mapping
const ANCHOR_EMOJI: Record<string, string> = {
  "Morning Coffee": "🌅",
  "Morning": "🌅",
  "Before Work": "🌅",
  "After Lunch": "☀️",
  "Lunch Break": "☀️",
  "Midday": "☀️",
  "End of Day": "🌙",
  "After Dinner": "🌙",
  "Evening": "🌙",
};

// Energy level colors
const ENERGY_COLOR: Record<string, string> = {
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-green-500",
};

function TaskItem({ task }: { task: MicroTask }) {
  const emoji = ANCHOR_EMOJI[task.assigned_anchor] || "📋";
  const energyColor = ENERGY_COLOR[task.energy_required] || "text-muted-foreground";

  return (
    <div className="bg-background/50 rounded-lg p-3 border border-border/50">
      <div className="flex items-start gap-3">
        <span className="text-lg flex-shrink-0">{emoji}</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-foreground truncate">{task.task_name}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {task.estimated_minutes} min
            </span>
            <span className={cn("flex items-center gap-1", energyColor)}>
              <Zap className="w-3 h-3" />
              {task.energy_required}
            </span>
            <span className="truncate">{task.assigned_anchor}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PlanPreview({ plan, onConfirm, onModify, isLoading = false }: PlanPreviewProps) {
  return (
    <div className="bg-primary/5 border border-primary/20 rounded-xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="bg-primary/10 px-4 py-3 border-b border-primary/20">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">{plan.project_name}</h3>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{plan.smart_goal_summary}</p>
        {plan.deadline && (
          <p className="text-xs text-primary mt-1">Deadline: {plan.deadline}</p>
        )}
      </div>

      {/* Tasks List */}
      <div className="p-4 space-y-2 max-h-64 overflow-y-auto">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          {plan.tasks.length} Tasks
        </p>
        {plan.tasks.map((task, index) => (
          <TaskItem key={index} task={task} />
        ))}
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-t border-primary/20 bg-background/50 flex gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={onModify}
          disabled={isLoading}
          className="flex-1"
        >
          <Edit3 className="w-4 h-4 mr-2" />
          Modify
        </Button>
        <Button
          size="sm"
          onClick={onConfirm}
          disabled={isLoading}
          className="flex-1 bg-primary hover:bg-primary/90"
        >
          <Check className="w-4 h-4 mr-2" />
          {isLoading ? "Saving..." : "Save Plan"}
        </Button>
      </div>
    </div>
  );
}

export default PlanPreview;
