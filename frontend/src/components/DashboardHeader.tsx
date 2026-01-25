import ProgressSpiral from "./ProgressSpiral";
import goalieLogoImg from "@/assets/goalie-logo.jpeg";

interface DashboardHeaderProps {
  userName: string;
  completedTasks: number;
  totalTasks: number;
  currentDate: string;
}

const DashboardHeader = ({
  userName,
  completedTasks,
  totalTasks,
  currentDate,
}: DashboardHeaderProps) => {
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  return (
    <header className="flex items-center justify-between mb-8">
      <div className="flex items-center gap-4">
        <img 
          src={goalieLogoImg} 
          alt="Goalie Logo" 
          className="w-14 h-14 rounded-2xl shadow-lg object-cover"
        />
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {getGreeting()}, {userName}
          </h1>
          <p className="text-muted-foreground">{currentDate}</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right mr-2">
          <p className="text-sm font-medium text-foreground">Today's Progress</p>
          <p className="text-xs text-muted-foreground">Keep it up!</p>
        </div>
        <ProgressSpiral
          completed={completedTasks}
          total={totalTasks}
          className="w-20 h-20"
        />
      </div>
    </header>
  );
};

export default DashboardHeader;
