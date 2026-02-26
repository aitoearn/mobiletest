export interface ExecutionStep {
  id: string;
  type: "thinking" | "tool_call" | "tool_result" | "assistant";
  content: string;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
  toolResult?: string;
  screenshot?: string; // 截图数据
  timestamp: Date;
  isExpanded?: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  steps?: ExecutionStep[];
  isStreaming?: boolean;
  success?: boolean;
}

export interface Device {
  device_id: string;
  model: string;
  brand: string;
  status: string;
}

export interface ChatAPIRequest {
  messages: Array<{ role: string; content: string }>;
  device_id?: string;
  session_id?: string;
}

export interface SSEEvent {
  type: "start" | "thinking" | "message" | "tool_call" | "tool_result" | "done" | "error" | "node" | "step";
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  result?: string;
  step?: number;
  thinking?: string;
  action?: Record<string, unknown>;
  success?: boolean;
  finished?: boolean;
  message?: string;
  screenshot?: string; // 截图数据
  data?: {
    node?: string;
    tool_name?: string;
    tool_args?: Record<string, unknown>;
    result?: string;
    error?: string;
    message?: string;
    content?: string;
    screenshot?: string; // 截图数据
  };
}
