import { useEffect, useRef } from "react";
import { Avatar, Tag } from "antd";
import {
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import type { Message } from "@/types";

interface MessageListProps {
  messages: Message[];
}

const roleConfig = {
  user: {
    avatar: <UserOutlined />,
    bgColor: "#1890ff",
    bubbleColor: "bg-blue-500 text-white",
    align: "flex-row-reverse",
  },
  assistant: {
    avatar: <RobotOutlined />,
    bgColor: "#52c41a",
    bubbleColor: "bg-green-50 text-gray-800 border border-green-200",
    align: "",
  },
  system: {
    avatar: <ThunderboltOutlined />,
    bgColor: "#faad14",
    bubbleColor: "bg-gray-100 text-gray-600",
    align: "",
  },
};

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
          <div
            key={msg.id}
            className={`flex gap-3 ${config.align}`}
          >
            <Avatar
              icon={config.avatar}
              style={{ backgroundColor: config.bgColor }}
            />

            <div className={`flex-1 ${msg.role === "user" ? "text-right" : ""}`}>
              <div className={`inline-block max-w-[80%] p-3 rounded-lg ${config.bubbleColor}`}>
                {msg.content}
                {isLastMessage && msg.isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-green-500 animate-pulse" />
                )}
              </div>

              {msg.steps && msg.steps.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.steps.map((step) => (
                    <div
                      key={step.id}
                      className="flex items-start gap-2 text-xs text-gray-500 bg-gray-50 p-2 rounded"
                    >
                      {step.type === "thinking" && <LoadingOutlined spin />}
                      {step.type === "tool_call" && (
                        <Tag color="blue" className="m-0 text-xs">
                          工具
                        </Tag>
                      )}
                      {step.type === "tool_result" && (
                        <Tag color="green" className="m-0 text-xs">
                          结果
                        </Tag>
                      )}
                      <span>{step.content}</span>
                      {step.toolName && (
                        <span className="text-blue-500">
                          ({step.toolName})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="text-xs text-gray-400 mt-1">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
