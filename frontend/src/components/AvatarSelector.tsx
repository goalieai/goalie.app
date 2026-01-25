import { useState } from "react";
import { cn } from "@/lib/utils";

const avatars = [
  { id: "octopus", emoji: "🐙", label: "Octopus" },
  { id: "lion", emoji: "🦁", label: "Lion" },
  { id: "rocket", emoji: "🚀", label: "Rocket" },
  { id: "star", emoji: "⭐", label: "Star" },
  { id: "fire", emoji: "🔥", label: "Fire" },
  { id: "trophy", emoji: "🏆", label: "Trophy" },
];

interface AvatarSelectorProps {
  selectedAvatar?: string;
  onSelect?: (avatarId: string) => void;
  className?: string;
}

const AvatarSelector = ({ selectedAvatar = "octopus", onSelect, className }: AvatarSelectorProps) => {
  const [selected, setSelected] = useState(selectedAvatar);

  const handleSelect = (avatarId: string) => {
    setSelected(avatarId);
    onSelect?.(avatarId);
  };

  return (
    <div className={cn("", className)}>
      <p className="text-sm font-medium text-muted-foreground mb-3">Choose your Goalie</p>
      <div className="flex gap-2 flex-wrap">
        {avatars.map((avatar) => (
          <button
            key={avatar.id}
            onClick={() => handleSelect(avatar.id)}
            className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center text-2xl transition-all duration-200 hover:scale-110",
              selected === avatar.id
                ? "bg-primary ring-2 ring-primary ring-offset-2 ring-offset-background shadow-lg"
                : "bg-secondary hover:bg-secondary/80"
            )}
            title={avatar.label}
          >
            {avatar.emoji}
          </button>
        ))}
      </div>
    </div>
  );
};

export default AvatarSelector;
