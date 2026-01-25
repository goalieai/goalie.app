import { cn } from "@/lib/utils";

interface ProgressSpiralProps {
  completed: number;
  total: number;
  className?: string;
}

const ProgressSpiral = ({ completed, total, className }: ProgressSpiralProps) => {
  const percentage = total > 0 ? (completed / total) * 100 : 0;
  const circumference = 2 * Math.PI * 45; // radius = 45
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      <svg
        className="transform -rotate-90 w-32 h-32"
        viewBox="0 0 100 100"
      >
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-muted"
        />
        {/* Progress circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          className="text-primary transition-all duration-1000 ease-out"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: strokeDashoffset,
          }}
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-foreground">
          {completed}
        </span>
        <span className="text-sm text-muted-foreground">
          of {total}
        </span>
      </div>
    </div>
  );
};

export default ProgressSpiral;
