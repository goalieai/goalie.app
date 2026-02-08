import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CalendarCheck, AlertCircle } from "lucide-react";

const GoogleConnected = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const success = searchParams.get("success") === "true";
  const error = searchParams.get("error");

  useEffect(() => {
    if (success) {
      toast.success("Google Calendar connected successfully!");
    } else {
      toast.error(error === "no_email" ? "Could not retrieve your Google email." : "Failed to connect Google Calendar.");
    }

    const timer = setTimeout(() => navigate("/"), 2000);
    return () => clearTimeout(timer);
  }, [success, error, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4 p-8">
        {success ? (
          <>
            <CalendarCheck className="w-16 h-16 text-primary mx-auto" />
            <h1 className="text-2xl font-bold text-foreground">Google Calendar Connected!</h1>
            <p className="text-muted-foreground">Redirecting you back to the dashboard...</p>
          </>
        ) : (
          <>
            <AlertCircle className="w-16 h-16 text-destructive mx-auto" />
            <h1 className="text-2xl font-bold text-foreground">Connection Failed</h1>
            <p className="text-muted-foreground">Redirecting you back to the dashboard...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default GoogleConnected;
