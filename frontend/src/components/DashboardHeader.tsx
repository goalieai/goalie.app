import { useAuth } from "@/contexts/AuthContext";
import LoginDialog from "./LoginDialog";
import GoogleConnectButton from "./GoogleConnectButton";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import goalieLogoImg from "@/assets/goalie-logo.jpeg";

interface DashboardHeaderProps {
    currentDate: string;
}

const DashboardHeader = ({ currentDate }: DashboardHeaderProps) => {
    const { user, isGuest, signOut } = useAuth();

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 17) return "Good afternoon";
        return "Good evening";
    };

    // Get display name from user email or show "Guest"
    const displayName = isGuest
        ? "Guest"
        : user?.email?.split("@")[0] || "there";

    return (
        <header className="flex items-center justify-between mb-6 sm:mb-8">
            {/* Left: Logo + greeting */}
            <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                <img
                    src={goalieLogoImg}
                    alt="Goalie Logo"
                    className="w-10 h-10 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl shadow-lg object-cover flex-shrink-0"
                />
                <div className="min-w-0">
                    <h1 className="text-base sm:text-2xl font-bold text-foreground truncate">
                        {getGreeting()}, {displayName}
                    </h1>
                    <p className="text-xs sm:text-sm text-muted-foreground">{currentDate}</p>
                </div>
            </div>

            {/* Right: Auth Button */}
            {isGuest ? (
                <LoginDialog />
            ) : (
                <div className="flex items-center gap-1">
                    <GoogleConnectButton userId={user?.id} />
                    {/* Mobile: icon only */}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => signOut()}
                        className="text-muted-foreground sm:hidden h-8 w-8"
                        title="Sign Out"
                    >
                        <LogOut className="w-4 h-4" />
                    </Button>
                    {/* Desktop: icon + text */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => signOut()}
                        className="hidden sm:flex gap-2 text-muted-foreground"
                    >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                    </Button>
                </div>
            )}
        </header>
    );
};

export default DashboardHeader;
