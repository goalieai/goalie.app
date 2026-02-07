import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, Lock, Loader2, LogIn, Eye, EyeOff } from "lucide-react";

export default function LoginDialog() {
    const { signUp, signInWithPassword, isGuest } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [open, setOpen] = useState(false);
    const [mode, setMode] = useState<"signin" | "signup">("signin");
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        const { error } = mode === "signup"
            ? await signUp(email, password)
            : await signInWithPassword(email, password);

        setIsLoading(false);

        if (error) {
            setError(error.message);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        setOpen(newOpen);
        if (!newOpen) {
            setEmail("");
            setPassword("");
            setError(null);
            setShowPassword(false);
        }
    };

    const toggleMode = () => {
        setMode((m) => (m === "signin" ? "signup" : "signin"));
        setError(null);
    };

    if (!isGuest) return null;

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                    <LogIn className="w-4 h-4" />
                    Sign In
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="text-2xl">
                        {mode === "signin" ? "Welcome back" : "Create your account"}
                    </DialogTitle>
                    <DialogDescription>
                        {mode === "signin"
                            ? "Sign in to sync your goals and tasks across devices."
                            : "Sign up to save your progress and access it anywhere."}
                    </DialogDescription>
                </DialogHeader>

                {/* Email/Password form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="pl-10"
                                required
                                disabled={isLoading}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder={mode === "signup" ? "Create a password (min 6 chars)" : "Your password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="pl-10 pr-10"
                                required
                                minLength={6}
                                disabled={isLoading}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                tabIndex={-1}
                            >
                                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    {error && (
                        <p className="text-sm text-destructive">{error}</p>
                    )}

                    <Button type="submit" className="w-full" disabled={isLoading || !email || !password}>
                        {isLoading ? (
                            <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                {mode === "signup" ? "Creating account..." : "Signing in..."}
                            </>
                        ) : (
                            mode === "signup" ? "Create Account" : "Sign In"
                        )}
                    </Button>
                </form>

                {/* Mode toggle */}
                <p className="text-xs text-center text-muted-foreground">
                    {mode === "signin" ? "Don't have an account?" : "Already have an account?"}
                    <button
                        type="button"
                        onClick={toggleMode}
                        className="text-primary ml-1 hover:underline font-medium"
                    >
                        {mode === "signin" ? "Sign up" : "Sign in"}
                    </button>
                </p>
            </DialogContent>
        </Dialog>
    );
}
