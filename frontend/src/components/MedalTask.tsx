import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import goalieLogo from "@/assets/goalie-logo.jpeg";

interface MedalTaskProps {
  task: string;
  completed?: boolean;
  className?: string;
}

const MedalTask = ({ task, completed = true, className }: MedalTaskProps) => {
  return (
    <div
      className={cn(
        "flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl border-2 bg-card",
        completed ? "border-primary/30 bg-primary/5" : "border-border",
        className
      )}
    >
      {/* Logo */}
      <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl overflow-hidden shadow-md flex-shrink-0">
        <img src={goalieLogo} alt="Goalie" className="w-full h-full object-cover" />
      </div>
      
      {/* Checkbox and Task */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1">
        <Checkbox checked={completed} className="w-5 h-5 sm:w-6 sm:h-6 border-2 border-primary data-[state=checked]:bg-primary" />
        <span className={cn(
          "font-medium text-sm sm:text-base",
          completed ? "text-foreground" : "text-muted-foreground"
        )}>
          {task}
        </span>
      </div>
      
      {completed && (
        <span className="text-xs sm:text-sm text-primary font-semibold whitespace-nowrap">Complete ✓</span>
      )}
    </div>
  );
};

export default MedalTask;
