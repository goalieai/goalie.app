import { useGoogleCalendar } from "@/hooks/useGoogleCalendar";
import { Button } from "@/components/ui/button";
import { CalendarCheck, CalendarPlus, Loader2 } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface GoogleConnectButtonProps {
  userId: string | undefined;
}

const GoogleConnectButton = ({ userId }: GoogleConnectButtonProps) => {
  const { isConnected, accounts, isLoading, connect, disconnect, isDisconnecting } = useGoogleCalendar(userId);

  // console.log("[GOOGLE DEBUG] GoogleConnectButton render:", { userId, isConnected, accounts, isLoading, isDisconnecting });

  if (!userId || isLoading) return null;

  if (isConnected) {
    const email = accounts[0]?.email;
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => disconnect(email)}
            disabled={isDisconnecting}
            className="text-muted-foreground gap-1.5 text-xs"
          >
            {isDisconnecting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CalendarCheck className="w-3.5 h-3.5 text-green-600" />
            )}
            <span className="hidden sm:inline">{email || "Calendar"}</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Click to disconnect Google Calendar</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          onClick={connect}
          className="text-muted-foreground gap-1.5 text-xs"
        >
          <CalendarPlus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Connect Calendar</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent>Connect Google Calendar to sync tasks</TooltipContent>
    </Tooltip>
  );
};

export default GoogleConnectButton;
