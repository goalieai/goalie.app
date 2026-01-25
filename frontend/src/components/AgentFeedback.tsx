import { Calendar, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Suggestion {
  id: string;
  message: string;
  type: "reschedule" | "break" | "motivation";
}

interface AgentFeedbackProps {
  suggestions: Suggestion[];
  onAccept: (id: string) => void;
  onDismiss: (id: string) => void;
}

const AgentFeedback = ({ suggestions, onAccept, onDismiss }: AgentFeedbackProps) => {
  if (suggestions.length === 0) return null;

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion, index) => (
        <div
          key={suggestion.id}
          className={cn(
            "rounded-xl border bg-card p-4 shadow-sm animate-slide-up",
            suggestion.type === "reschedule" && "border-l-4 border-l-warning",
            suggestion.type === "break" && "border-l-4 border-l-primary",
            suggestion.type === "motivation" && "border-l-4 border-l-success"
          )}
          style={{ animationDelay: `${index * 100}ms` }}
        >
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "rounded-full p-2 shrink-0",
                suggestion.type === "reschedule" && "bg-warning/10 text-warning",
                suggestion.type === "break" && "bg-primary/10 text-primary",
                suggestion.type === "motivation" && "bg-success/10 text-success"
              )}
            >
              <Calendar className="w-4 h-4" />
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground leading-relaxed">
                {suggestion.message}
              </p>
            </div>
          </div>

          <div className="flex gap-2 mt-3 ml-11">
            <Button
              size="sm"
              onClick={() => onAccept(suggestion.id)}
              className="h-8 px-4 rounded-lg bg-primary hover:bg-primary/90"
            >
              <Check className="w-3.5 h-3.5 mr-1.5" />
              Accept
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDismiss(suggestion.id)}
              className="h-8 px-4 rounded-lg text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5 mr-1.5" />
              Dismiss
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AgentFeedback;
