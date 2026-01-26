import { useState } from "react";
import { useCreateTask } from "@/hooks/useTasks";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus } from "lucide-react";

export default function AddTaskForm() {
    const [open, setOpen] = useState(false);
    const [taskName, setTaskName] = useState("");
    const [minutes, setMinutes] = useState("15");
    const [energy, setEnergy] = useState<"high" | "medium" | "low">("medium");

    const createTask = useCreateTask();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        createTask.mutate(
            {
                task_name: taskName,
                estimated_minutes: parseInt(minutes),
                energy_required: energy,
            },
            {
                onSuccess: () => {
                    setOpen(false);
                    setTaskName("");
                    setMinutes("15");
                    setEnergy("medium");
                },
            }
        );
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button size="sm" className="gap-2">
                    <Plus className="w-4 h-4" /> Add Task
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add New Task</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="task">Task Name</Label>
                        <Input
                            id="task"
                            value={taskName}
                            onChange={(e) => setTaskName(e.target.value)}
                            placeholder="e.g., Review PRs"
                            required
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="minutes">Minutes</Label>
                            <Input
                                id="minutes"
                                type="number"
                                value={minutes}
                                onChange={(e) => setMinutes(e.target.value)}
                                min="1"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="energy">Energy</Label>
                            <Select value={energy} onValueChange={(v: any) => setEnergy(v)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="low">Low 🟢</SelectItem>
                                    <SelectItem value="medium">Medium 🟡</SelectItem>
                                    <SelectItem value="high">High 🔴</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" type="button" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={createTask.isPending}>
                            {createTask.isPending ? "Adding..." : "Add Task"}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    );
}
