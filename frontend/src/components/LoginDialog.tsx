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
import { Mail, Loader2, CheckCircle } from "lucide-react";

export default function LoginDialog() {
    const { signInWithMagicLink, isGuest } = useAuth();
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSent, setIsSent] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [open, setOpen] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        const { error } = await signInWithMagicLink(email);

        setIsLoading(false);

        if (error) {
            setError(error.message);
        } else {
            setIsSent(true);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        setOpen(newOpen);
        if (!newOpen) {
            // Reset state when closing
            setEmail("");
            setIsSent(false);
            setError(null);
        }
    };

    if (!isGuest) return null;

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
                {/* {trigger || (
                    <Button variant="outline" size="sm" className="gap-2">
                        <LogIn className="w-4 h-4" />
                        Sign In
                    </Button>
                )} */}
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="text-2xl">Welcome to Goalie</DialogTitle>
                    <DialogDescription>
                        Sign in to sync your goals and tasks across devices.
                    </DialogDescription>
                </DialogHeader>

                {isSent ? (
                    <div className="flex flex-col items-center gap-4 py-6">
                        <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                            <CheckCircle className="w-6 h-6 text-green-600" />
                        </div>
                        <div className="text-center">
                            <p className="font-medium">Check your email</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                We sent a magic link to <strong>{email}</strong>
                            </p>
                        </div>
                        <Button
                            variant="ghost"
                            onClick={() => setIsSent(false)}
                            className="mt-2"
                        >
                            Use a different email
                        </Button>
                    </div>
                ) : (
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

                        {error && (
                            <p className="text-sm text-destructive">{error}</p>
                        )}

                        <Button
                            type="submit"
                            className="w-full"
                            disabled={isLoading || !email}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Sending...
                                </>
                            ) : (
                                "Send Magic Link"
                            )}
                        </Button>

                        <p className="text-xs text-center text-muted-foreground">
                            No password needed. We'll email you a secure link.
                        </p>
                    </form>
                )}
            </DialogContent>
        </Dialog>
    );
}
