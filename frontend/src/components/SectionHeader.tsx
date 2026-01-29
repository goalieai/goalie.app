import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  variant: "now" | "next" | "achieved";
}

const SectionHeader = ({ icon: Icon, title, subtitle, variant }: SectionHeaderProps) => {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div
        className={cn(
          "rounded-xl p-2.5",
          variant === "now" && "bg-primary/10 text-primary",
          variant === "next" && "bg-accent text-accent-foreground",
          variant === "achieved" && "bg-achieved text-achieved-border"
        )}
      >
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </div>
  );
};

export default SectionHeader;
