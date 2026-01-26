import { useState } from "react";
import { useCreateGoal } from "@/hooks/useGoals";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus } from "lucide-react";

export default function AddGoalForm() {
    const [open, setOpen] = useState(false);
    const [title, setTitle] = useState("");
    const [emoji, setEmoji] = useState("🎯");

    const createGoal = useCreateGoal();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createGoal.mutate(
            {
                title,
                emoji,
            },
            {
                onSuccess: () => {
                    setOpen(false);
                    setTitle("");
                    setEmoji("🎯");
                },
            }
        );
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2 h-auto py-1 px-2">
                    <Plus className="w-4 h-4" /> Add Goal
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Set New Goal</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="flex gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="emoji">Emoji</Label>
                            <Input
                                id="emoji"
                                value={emoji}
                                onChange={(e) => setEmoji(e.target.value)}
                                className="w-16 text-center text-2xl"
                                maxLength={2}
                            />
                        </div>
                        <div className="space-y-2 flex-1">
                            <Label htmlFor="title">Goal Title</Label>
                            <Input
                                id="title"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="e.g., Run 5k"
                                required
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" type="button" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={createGoal.isPending}>
                            {createGoal.isPending ? "Saving..." : "Save Goal"}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
