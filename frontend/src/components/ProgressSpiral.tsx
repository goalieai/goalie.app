import { cn } from "@/lib/utils";

interface ProgressSpiralProps {
  completed: number;
  total: number;
  label?: string;
  className?: string;
}

const ProgressSpiral = ({ completed, total, label = "Tasks", className }: ProgressSpiralProps) => {
  const percentage = total > 0 ? (completed / total) * 100 : 0;
  const circumference = 2 * Math.PI * 42; // radius = 42 (smaller for text space)
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  // Show different content when no tasks
  const isEmpty = total === 0;

  return (
    <div className={cn("relative flex flex-col items-center", className)}>
      <svg
        className="w-full h-full"
        viewBox="0 0 100 100"
      >
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="42"
          stroke="currentColor"
          strokeWidth="6"
          fill="none"
          className="text-muted"
        />
        {/* Progress circle */}
        <circle
          cx="50"
          cy="50"
          r="42"
          stroke="currentColor"
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          className="text-primary transition-all duration-1000 ease-out"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: isEmpty ? circumference : strokeDashoffset,
          }}
        />
        {/* Center text */}
        {isEmpty ? (
          <text
            x="50"
            y="50"
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-muted-foreground"
            style={{ fontSize: '12px' }}
          >
            No tasks
          </text>
        ) : (
          <>
            <text
              x="50"
              y="44"
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-foreground font-bold"
              style={{ fontSize: '22px' }}
            >
              {completed}/{total}
            </text>
            <text
              x="50"
              y="60"
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-muted-foreground"
              style={{ fontSize: '10px' }}
            >
              {label}
            </text>
          </>
        )}
      </svg>
    </div>
  );
};

export default ProgressSpiral;
