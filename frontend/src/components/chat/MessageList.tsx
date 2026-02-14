import { useEffect, useRef, useState } from "react";
import { Avatar, Tag, Button, Collapse } from "antd";
import {
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ToolOutlined,
  RightOutlined,
  DownOutlined,
} from "@ant-design/icons";
import type { Message, ExecutionStep } from "@/types";

interface MessageListProps {
  messages: Message[];
}

const roleConfig = {
  user: {
    avatar: <UserOutlined />,
    bgColor: "#722ed1",
    bubbleClass: "bg-purple-600 text-white rounded-2xl rounded-br-sm",
    align: "justify-end",
  },
  assistant: {
    avatar: <RobotOutlined />,
    bgColor: "#52c41a",
    bubbleClass: "bg-gray-100 text-gray-800 rounded-2xl rounded-tl-sm",
    align: "justify-start",
  },
  system: {
    avatar: <ThunderboltOutlined />,
    bgColor: "#faad14",
    bubbleClass: "bg-gray-100 text-gray-600 rounded-lg",
    align: "justify-start",
  },
};

interface StepItemProps {
  step: ExecutionStep;
  index: number;
  messageId: string;
}

function StepItem({ step, index }: StepItemProps) {
  const [expanded, setExpanded] = useState(true);

  const getStepStyle = () => {
    switch (step.type) {
      case "tool_call":
        return {
          icon: <ToolOutlined className="text-blue-500" />,
          iconBg: "bg-blue-100",
          label: `步骤 ${index + 1}: ${step.content || "调用工具"}`,
          labelColor: "text-blue-600",
        };
      case "tool_result":
        return {
          icon: <CheckCircleOutlined className="text-green-500" />,
          iconBg: "bg-green-100",
          label: `步骤 ${index + 1}: 执行结果`,
          labelColor: "text-green-600",
        };
      case "thinking":
        return {
          icon: <LoadingOutlined spin className="text-orange-500" />,
          iconBg: "bg-orange-100",
          label: `步骤 ${index + 1}: 思考中...`,
          labelColor: "text-orange-600",
        };
      default:
        return {
          icon: <RightOutlined className="text-gray-500" />,
          iconBg: "bg-gray-100",
          label: `步骤 ${index + 1}: ${step.content}`,
          labelColor: "text-gray-600",
        };
    }
  };

  const style = getStepStyle();

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`flex h-6 w-6 items-center justify-center rounded-full ${style.iconBg}`}>
            {style.icon}
          </div>
          <span className={`text-sm font-medium ${style.labelColor}`}>
            {style.label}
          </span>
          {step.toolName && (
            <Tag color="blue" className="ml-2 text-xs">
              {step.toolName}
            </Tag>
          )}
        </div>
        {expanded ? (
          <DownOutlined className="text-gray-400 text-xs" />
        ) : (
          <RightOutlined className="text-gray-400 text-xs" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {step.type === "tool_call" && step.toolArgs && (
            <div className="bg-white rounded-lg p-3 text-sm border border-gray-100">
              <p className="text-xs text-gray-500 mb-1 font-medium">
                工具参数:
              </p>
              <pre className="text-xs text-gray-600 overflow-x-auto whitespace-pre-wrap">
                {typeof step.toolArgs === "string"
                  ? step.toolArgs
                  : JSON.stringify(step.toolArgs, null, 2)}
              </pre>
            </div>
          )}
          {step.type === "tool_result" && step.toolResult && (
            <div className="bg-white rounded-lg p-3 text-sm border border-gray-100">
              <p className="text-xs text-gray-500 mb-1 font-medium">
                执行结果:
              </p>
              <pre className="text-xs text-gray-600 overflow-x-auto whitespace-pre-wrap max-h-40 overflow-y-auto">
                {typeof step.toolResult === "string"
                  ? step.toolResult
                  : JSON.stringify(step.toolResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="space-y-4">
      {messages.map((msg) => {
        const config = roleConfig[msg.role];
        const isLastMessage = msg.id === messages[messages.length - 1]?.id;

        return (
          <div key={msg.id} className={`flex ${config.align}`}>
            {msg.role === "user" ? (
              <div className="max-w-[80%]">
                <div className={`${config.bubbleClass} px-4 py-2`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                <p className="text-xs text-gray-400 mt-1 text-right">
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>
            ) : (
              <div className="max-w-[85%] space-y-3">
                {msg.steps && msg.steps.length > 0 && (
                  <div className="space-y-2">
                    {msg.steps.map((step, idx) => (
                      <StepItem
                        key={step.id}
                        step={step}
                        index={idx}
                        messageId={msg.id}
                      />
                    ))}
                  </div>
                )}

                {msg.content && (
                  <div
                    className={`px-4 py-3 ${
                      msg.success === false
                        ? "bg-red-50 text-red-600 border border-red-200"
                        : "bg-gray-100 text-gray-800"
                    } rounded-2xl rounded-tl-sm`}
                  >
                    <div className="flex items-start gap-2">
                      {msg.success !== undefined && (
                        msg.success ? (
                          <CheckCircleOutlined className="text-green-500 mt-0.5" />
                        ) : (
                          <CloseCircleOutlined className="text-red-500 mt-0.5" />
                        )
                      )}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                )}

                {isLastMessage && msg.isStreaming && !msg.content && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 px-4 py-2 rounded-lg">
                    <LoadingOutlined spin />
                    <span>正在思考和执行...</span>
                  </div>
                )}

                <p className="text-xs text-gray-400">
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>
            )}
          </div>
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
