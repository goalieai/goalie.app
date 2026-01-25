import { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  content: string;
  sender: "agent" | "user";
  timestamp: Date;
}

interface AgentChatProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isTyping?: boolean;
}

const AgentChat = ({ messages, onSendMessage, isTyping = false }: AgentChatProps) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-agent rounded-2xl border">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b">
        <div className="relative">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-success rounded-full border-2 border-agent" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Goalie</h3>
          <p className="text-xs text-muted-foreground">Your goal companion</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-scroll">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={cn(
              "flex animate-fade-in",
              message.sender === "user" ? "justify-end" : "justify-start"
            )}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
                message.sender === "agent"
                  ? "agent-bubble text-foreground rounded-bl-md"
                  : "bg-primary text-primary-foreground rounded-br-md"
              )}
            >
              <p className="leading-relaxed">{message.content}</p>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="agent-bubble rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Talk to Goalie..."
            className="flex-1 rounded-xl border bg-card px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim()}
            className="h-12 w-12 rounded-xl bg-primary hover:bg-primary/90 transition-all disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default AgentChat;
