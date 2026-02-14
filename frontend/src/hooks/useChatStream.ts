import { useState, useRef, useCallback } from "react";
import type { Message, ExecutionStep, SSEEvent } from "@/types";

interface UseChatStreamOptions {
  deviceId?: string;
  sessionId?: string;
  onMessage?: (content: string) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface UseChatStreamReturn {
  messages: Message[];
  sending: boolean;
  streamingContent: string;
  sendMessage: (content: string) => Promise<void>;
  abort: () => void;
  clear: () => void;
}

export function useChatStream(options: UseChatStreamOptions = {}): UseChatStreamReturn {
  const { deviceId, sessionId, onMessage, onComplete, onError } = options;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || sending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setSending(true);
    setStreamingContent("");

    const agentMessageId = (Date.now() + 1).toString();
    const agentMessage: Message = {
      id: agentMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      steps: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, agentMessage]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content }],
          device_id: deviceId,
          session_id: sessionId,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      const steps: ExecutionStep[] = [];
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data: SSEEvent = JSON.parse(line.slice(6));
              
              if (data.type === "start") {
                // Stream started
              } else if (data.type === "message") {
                const msgContent = data.content || "";
                fullContent += msgContent;
                setStreamingContent(fullContent);
                onMessage?.(msgContent);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === agentMessageId
                      ? { ...msg, content: fullContent }
                      : msg
                  )
                );
              } else if (data.type === "tool_call") {
                const toolName = data.tool_name || data.data?.tool_name || "";
                const toolArgs = data.tool_args || data.data?.tool_args || {};
                
                const step: ExecutionStep = {
                  id: `step-${Date.now()}-${Math.random()}`,
                  type: "tool_call",
                  content: _getToolCallDescription(toolName, toolArgs),
                  toolName,
                  toolArgs,
                  timestamp: new Date(),
                };
                steps.push(step);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === agentMessageId
                      ? { ...msg, steps: [...steps] }
                      : msg
                  )
                );
              } else if (data.type === "tool_result") {
                const toolName = data.tool_name || data.data?.tool_name || "";
                const result = data.result || data.data?.result || "";
                
                const step: ExecutionStep = {
                  id: `step-${Date.now()}-${Math.random()}`,
                  type: "tool_result",
                  content: `${toolName} 执行结果`,
                  toolName,
                  toolResult: result,
                  timestamp: new Date(),
                };
                steps.push(step);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === agentMessageId
                      ? { ...msg, steps: [...steps] }
                      : msg
                  )
                );
              } else if (data.type === "done") {
                const finalContent = data.content || fullContent || "执行完成";
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === agentMessageId
                      ? { 
                          ...msg, 
                          content: finalContent, 
                          isStreaming: false,
                          success: true,
                          steps: [...steps]
                        }
                      : msg
                  )
                );
                onComplete?.();
              } else if (data.type === "error") {
                const errorMsg = data.data?.error || data.data?.message || "未知错误";
                setStreamingContent(`错误: ${errorMsg}`);
                onError?.(errorMsg);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === agentMessageId
                      ? { 
                          ...msg, 
                          content: `错误: ${errorMsg}`, 
                          isStreaming: false,
                          success: false,
                          steps: [...steps]
                        }
                      : msg
                  )
                );
              }
            } catch {
              // Skip parsing errors
            }
          }
        }
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === agentMessageId && msg.isStreaming
            ? { 
                ...msg, 
                content: fullContent || "执行完成", 
                isStreaming: false,
                success: true,
                steps: [...steps]
              }
            : msg
        )
      );
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }

      console.error("Chat error:", err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === agentMessageId
            ? { 
                ...msg, 
                content: "请求失败", 
                isStreaming: false,
                success: false
              }
            : msg
        )
      );
    } finally {
      setSending(false);
      abortControllerRef.current = null;
    }
  }, [deviceId, sessionId, sending, onMessage, onComplete, onError]);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setSending(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isStreaming
            ? { 
                ...msg, 
                content: msg.content || "任务已中断", 
                isStreaming: false,
                success: false
              }
            : msg
        )
      );
    }
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    setStreamingContent("");
  }, []);

  return {
    messages,
    sending,
    streamingContent,
    sendMessage,
    abort,
    clear,
  };
}

function _getToolCallDescription(toolName: string, args: Record<string, unknown>): string {
  switch (toolName) {
    case "device_control":
      const action = args?.action || args?.params?.action || "";
      switch (action) {
        case "launch_app":
          return `启动应用: ${args?.params?.package || ""}`;
        case "click":
          return `点击屏幕`;
        case "swipe":
          return `滑动: ${args?.params?.direction || ""}`;
        case "input":
          return `输入文本: ${args?.params?.text || ""}`;
        default:
          return `设备控制: ${action}`;
      }
    case "list_devices":
      return "获取设备列表";
    default:
      return `调用工具: ${toolName}`;
  }
}
