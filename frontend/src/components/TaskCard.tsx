import { Check, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  action: string;
  time: string;
  isCurrentFocus?: boolean;
  onComplete: () => void;
  onReplan: () => void;
  completed?: boolean;
}

const TaskCard = ({
  action,
  time,
  isCurrentFocus = false,
  onComplete,
  onReplan,
  completed = false,
}: TaskCardProps) => {
  return (
    <div
      className={cn(
        "group relative rounded-2xl border-2 p-6 transition-all duration-300",
        isCurrentFocus
          ? "bg-card border-primary/30 shadow-lg pulse-focus"
          : "bg-card border-border hover:border-primary/20 hover:shadow-md",
        completed && "opacity-60"
      )}
    >
      {/* Time badge */}
      <div className="mb-4">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium",
            isCurrentFocus
              ? "bg-primary/10 text-primary"
              : "bg-muted text-muted-foreground"
          )}
        >
          {time}
        </span>
      </div>

      {/* Action verb - large and clear */}
      <h3
        className={cn(
          "text-2xl font-semibold leading-tight mb-6",
          completed && "line-through text-muted-foreground"
        )}
      >
        {action}
      </h3>

      {/* Large action buttons - Fitts' Law */}
      {!completed && (
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <Button
            onClick={onComplete}
            size="lg"
            className="flex-1 h-12 sm:h-14 text-base sm:text-lg font-semibold rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground shadow-md hover:shadow-lg transition-all"
          >
            <Check className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Done
          </Button>
          <Button
            onClick={onReplan}
            size="lg"
            variant="outline"
            className="flex-1 h-12 sm:h-14 text-base sm:text-lg font-semibold rounded-xl border-2 hover:bg-secondary transition-all"
          >
            <RefreshCw className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
            Re-plan
          </Button>
        </div>
      )}

      {completed && (
        <div className="flex items-center justify-center py-3 text-success font-medium">
          <Check className="w-5 h-5 mr-2" />
          Completed!
        </div>
      )}
    </div>
  );
};

export default TaskCard;
