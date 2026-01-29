import { useState, useCallback, useRef } from "react";
import { ChatRequest, ChatResponse, Plan } from "@/services/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// =============================================================================
// Types
// =============================================================================

export type PipelineStep =
  | "intent"
  | "smart"
  | "tasks"
  | "schedule"
  | "response";

export interface StreamProgress {
  smart_goal?: { summary: string };
  raw_tasks?: string[];
}

export interface StreamEvent {
  type: "status" | "progress" | "complete" | "error";
  message?: string;
  data?: {
    step?: string;
    data?: unknown;
    // Complete event data
    session_id?: string;
    intent_detected?: string;
    response?: string;
    plan?: Plan;
    progress?: { completed: number; total: number; percentage: number };
    actions?: Array<{ type: string; data: Record<string, unknown> }>;
  };
}

export interface UseStreamingChatReturn {
  /** Current status message (e.g., "Refining SMART goal...") */
  status: string | null;
  /** Which pipeline step is currently active */
  currentStep: PipelineStep | null;
  /** Completed steps */
  completedSteps: PipelineStep[];
  /** Intermediate progress data (smart_goal, raw_tasks) */
  progress: StreamProgress;
  /** Final result when stream completes */
  result: ChatResponse | null;
  /** Error message if something went wrong */
  error: string | null;
  /** Whether we're currently streaming */
  isStreaming: boolean;
  /** Send a message and start streaming */
  sendMessage: (request: ChatRequest) => Promise<void>;
  /** Reset all state */
  reset: () => void;
}

// Map node names to pipeline steps
const NODE_TO_STEP: Record<string, PipelineStep> = {
  intent_router: "intent",
  smart_refiner: "smart",
  task_splitter: "tasks",
  context_matcher: "schedule",
  planning_response: "response",
  casual: "response",
  coaching: "response",
};

// =============================================================================
// SSE Line Buffer
// =============================================================================

/**
 * Handles buffering of SSE data that may arrive in chunks.
 * Proxies (Cloudflare, Vercel, nginx) can split events mid-line.
 *
 * Example problem without buffer:
 *   Chunk 1: 'data: {"type": "sta'
 *   Chunk 2: 'tus", "message": "..."}\n\n'
 *
 * JSON.parse would fail on chunk 1. This buffer accumulates
 * data until we have complete lines ending with \n\n.
 */
class SSEBuffer {
  private buffer = "";

  /**
   * Add a chunk to the buffer and extract complete events.
   * @returns Array of complete SSE data payloads (without "data: " prefix)
   */
  push(chunk: string): string[] {
    this.buffer += chunk;
    const events: string[] = [];

    // SSE events are separated by double newlines
    const parts = this.buffer.split("\n\n");

    // Keep the last part in buffer (may be incomplete)
    this.buffer = parts.pop() || "";

    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.startsWith("data: ")) {
        events.push(trimmed.slice(6)); // Remove "data: " prefix
      }
    }

    return events;
  }

  /**
   * Flush any remaining data in the buffer.
   */
  flush(): string[] {
    const events: string[] = [];
    const trimmed = this.buffer.trim();
    if (trimmed.startsWith("data: ")) {
      events.push(trimmed.slice(6));
    }
    this.buffer = "";
    return events;
  }

  clear(): void {
    this.buffer = "";
  }
}

// =============================================================================
// Hook
// =============================================================================

export function useStreamingChat(): UseStreamingChatReturn {
  const [status, setStatus] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<PipelineStep | null>(null);
  const [completedSteps, setCompletedSteps] = useState<PipelineStep[]>([]);
  const [progress, setProgress] = useState<StreamProgress>({});
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setStatus(null);
    setCurrentStep(null);
    setCompletedSteps([]);
    setProgress({});
    setResult(null);
    setError(null);
    setIsStreaming(false);

    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const processEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case "status":
        setStatus(event.message || null);
        break;

      case "progress":
        if (event.data?.step && event.data?.data) {
          const step = event.data.step;

          // Mark current step as completed when we get its progress data
          if (step === "smart_goal") {
            setCompletedSteps((prev) =>
              prev.includes("smart") ? prev : [...prev, "smart"]
            );
            setCurrentStep("tasks");
            setProgress((prev) => ({
              ...prev,
              smart_goal: event.data!.data as { summary: string },
            }));
          } else if (step === "raw_tasks") {
            setCompletedSteps((prev) =>
              prev.includes("tasks") ? prev : [...prev, "tasks"]
            );
            setCurrentStep("schedule");
            setProgress((prev) => ({
              ...prev,
              raw_tasks: event.data!.data as string[],
            }));
          }
        }
        break;

      case "complete":
        // Mark all remaining steps as completed
        setCompletedSteps(["intent", "smart", "tasks", "schedule", "response"]);
        setCurrentStep(null);
        setStatus(null);

        if (event.data) {
          setResult({
            session_id: event.data.session_id || "",
            intent_detected: (event.data.intent_detected as ChatResponse["intent_detected"]) || "unknown",
            response: event.data.response || "",
            plan: event.data.plan,
            progress: event.data.progress,
            actions: (event.data.actions || []) as ChatResponse["actions"],
          });
        }
        break;

      case "error":
        setError(event.message || "Unknown error occurred");
        break;
    }
  }, []);

  const sendMessage = useCallback(
    async (request: ChatRequest) => {
      // Reset state for new request
      reset();
      setIsStreaming(true);
      setCurrentStep("intent");
      setStatus("Processing your request...");

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();
      const buffer = new SSEBuffer();

      try {
        const response = await fetch(`${API_BASE}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body available");
        }

        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            // Process any remaining buffered data
            const remaining = buffer.flush();
            for (const eventData of remaining) {
              try {
                const event: StreamEvent = JSON.parse(eventData);
                processEvent(event);
              } catch (e) {
                console.warn("Failed to parse final SSE event:", eventData, e);
              }
            }
            break;
          }

          // Decode chunk and push to buffer
          const chunk = decoder.decode(value, { stream: true });
          const events = buffer.push(chunk);

          // Process complete events
          for (const eventData of events) {
            try {
              const event: StreamEvent = JSON.parse(eventData);
              processEvent(event);

              // Update current step based on status messages
              if (event.type === "status" && event.message) {
                // Infer step from status message
                for (const [node, step] of Object.entries(NODE_TO_STEP)) {
                  if (event.message.toLowerCase().includes(node.toLowerCase())) {
                    setCurrentStep(step);
                    break;
                  }
                }
                // Also check by message content
                if (event.message.includes("intención") || event.message.includes("intent")) {
                  setCompletedSteps((prev) =>
                    prev.includes("intent") ? prev : [...prev, "intent"]
                  );
                  setCurrentStep("smart");
                } else if (event.message.includes("SMART") || event.message.includes("Refinando")) {
                  setCurrentStep("smart");
                } else if (event.message.includes("micro-tareas") || event.message.includes("Dividiendo")) {
                  setCurrentStep("tasks");
                } else if (event.message.includes("agenda") || event.message.includes("Asignando")) {
                  setCurrentStep("schedule");
                } else if (event.message.includes("plan") || event.message.includes("Preparando")) {
                  setCurrentStep("response");
                }
              }
            } catch (e) {
              console.warn("Failed to parse SSE event:", eventData, e);
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          // Request was cancelled, don't treat as error
          return;
        }
        setError(err instanceof Error ? err.message : "Connection error");
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [reset, processEvent]
  );

  return {
    status,
    currentStep,
    completedSteps,
    progress,
    result,
    error,
    isStreaming,
    sendMessage,
    reset,
  };
}
