import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import PipelineProgress from "@/components/PipelineProgress";
import PlanPreview from "@/components/PlanPreview";
import { PipelineStep, StreamProgress, ClarificationState } from "@/hooks/useStreamingChat";
import { Plan } from "@/services/api";

interface Message {
  id: string;
  content: string;
  sender: "agent" | "user";
  timestamp: Date;
}

interface StreamingState {
  isStreaming: boolean;
  status: string | null;
  currentStep: PipelineStep | null;
  completedSteps: PipelineStep[];
  progress: StreamProgress;
  // HITL: Staging plan state
  stagingPlan?: Plan | null;
  awaitingConfirmation?: boolean;
  // Socratic Gatekeeper: Clarification state
  clarification?: ClarificationState | null;
  awaitingClarification?: boolean;
}

interface AgentChatProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isTyping?: boolean;
  streamingState?: StreamingState;
  /** Called when user confirms a staged plan */
  onConfirmPlan?: () => void;
  /** Called when user wants to modify a staged plan */
  onModifyPlan?: () => void;
  /** Whether plan confirmation is in progress */
  isConfirmingPlan?: boolean;
}

const AgentChat = ({
  messages,
  onSendMessage,
  isTyping = false,
  streamingState,
  onConfirmPlan,
  onModifyPlan,
  isConfirmingPlan = false,
}: AgentChatProps) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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
      if (inputRef.current) {
        inputRef.current.style.height = "auto";
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-grow textarea
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
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
              {message.sender === "agent" ? (
                <div className="leading-relaxed space-y-3">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => {
                        const text = String(children);
                        // Style "Goal:" lines as a highlight box
                        if (text.startsWith("Goal:")) {
                          return (
                            <div className="bg-primary/10 border-l-4 border-primary px-3 py-2 rounded-r-lg my-3">
                              <p className="font-semibold text-foreground">{children}</p>
                            </div>
                          );
                        }
                        // Style "Your Plan:" or "Your Action Plan:" as section headers
                        if (text.match(/^Your (Action )?Plan:/)) {
                          return (
                            <p className="font-semibold text-foreground mt-4 mb-2 border-b border-border/50 pb-1">
                              {children}
                            </p>
                          );
                        }
                        // Style emoji time-of-day lines (🌅, ☀️, 🌙)
                        if (text.match(/^[🌅☀️🌙]/)) {
                          return (
                            <div className="bg-secondary/30 rounded-lg px-3 py-2 my-2">
                              <p className="font-medium">{children}</p>
                            </div>
                          );
                        }
                        return <p className="my-2 first:mt-0 last:mb-0">{children}</p>;
                      },
                      strong: ({ children }) => (
                        <strong className="font-semibold text-foreground">{children}</strong>
                      ),
                      ul: ({ children }) => (
                        <ul className="my-2 ml-4 space-y-1.5 list-disc">{children}</ul>
                      ),
                      li: ({ children }) => (
                        <li className="leading-relaxed pl-1">{children}</li>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="leading-relaxed">{message.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* Streaming pipeline progress */}
        {streamingState?.isStreaming && (
          <div className="flex justify-start animate-fade-in">
            <div className="agent-bubble rounded-2xl rounded-bl-md px-4 py-4 w-full max-w-[95%]">
              <PipelineProgress
                currentStep={streamingState.currentStep}
                completedSteps={streamingState.completedSteps}
                progress={streamingState.progress}
                status={streamingState.status}
              />
            </div>
          </div>
        )}

        {/* HITL: Plan Preview with confirmation buttons */}
        {streamingState?.awaitingConfirmation && streamingState?.stagingPlan && (
          <div className="flex justify-start animate-fade-in">
            <div className="w-full max-w-[95%]">
              <PlanPreview
                plan={streamingState.stagingPlan}
                onConfirm={onConfirmPlan || (() => {})}
                onModify={onModifyPlan || (() => {})}
                isLoading={isConfirmingPlan}
              />
            </div>
          </div>
        )}

        {/* Socratic Gatekeeper: Clarification indicator */}
        {streamingState?.awaitingClarification && (
          <div className="flex justify-start animate-fade-in">
            <div className="agent-bubble rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-primary animate-pulse" />
              <span className="text-sm text-muted-foreground">
                Waiting for your answer...
              </span>
            </div>
          </div>
        )}

        {/* Fallback typing indicator (non-streaming) */}
        {isTyping && !streamingState?.isStreaming && (
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
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Talk to Goalie..."
            rows={1}
            className="flex-1 rounded-xl border bg-card px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all resize-none max-h-32 overflow-y-auto"
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
