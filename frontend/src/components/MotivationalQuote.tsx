import { cn } from "@/lib/utils";

interface MotivationalQuoteProps {
  quote: string;
  author?: string;
  className?: string;
}

const MotivationalQuote = ({ quote, author, className }: MotivationalQuoteProps) => {
  return (
    <div className={cn("text-center py-6 sm:py-8", className)}>
      <p className="text-xl sm:text-2xl font-bold text-primary">
        "{quote}"
      </p>
      {author && (
        <p className="text-sm sm:text-base text-muted-foreground mt-2">— {author}</p>
      )}
    </div>
  );
};

export default MotivationalQuote;
