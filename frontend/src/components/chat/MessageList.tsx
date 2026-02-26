import { useEffect, useRef, useState } from "react";
import { Tag, Image, Button } from "antd";
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
  BulbOutlined,
  ApiOutlined,
  CameraOutlined,
  SaveOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import type { Message, ExecutionStep } from "@/types";

interface MessageListProps {
  messages: Message[];
  onSaveInstruction?: (message: Message) => void;
  onAddAnalysis?: (message: Message) => void;
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

// 新版本的步骤展示组件 - 参考图片样式
function StepItem({ step, index }: StepItemProps) {
  const [expanded, setExpanded] = useState(true);

  // 解析步骤数据
  const thinking = step.content || "";
  const action = step.toolName || "";
  const actionParams = step.toolArgs || {};
  const screenshot = step.screenshot || "";

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-3">
      {/* 步骤头部 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors border-b border-gray-100"
      >
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100">
            <CheckCircleOutlined className="text-green-500 text-sm" />
          </div>
          <span className="text-sm font-medium text-gray-700">
            Step {index + 1}
          </span>
          <span className="text-xs text-gray-400">
            {step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ""}
          </span>
        </div>
        {expanded ? (
          <DownOutlined className="text-gray-400 text-xs" />
        ) : (
          <RightOutlined className="text-gray-400 text-xs" />
        )}
      </button>

      {expanded && (
        <div className="p-4">
          <div className="flex gap-4">
            {/* 左侧内容区域 */}
            <div className="flex-1 space-y-3">
              {/* 思考过程 */}
              {thinking && (
                <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
                  <div className="flex items-center gap-2 mb-2">
                    <BulbOutlined className="text-amber-500" />
                    <span className="text-sm font-medium text-amber-700">思考过程</span>
                  </div>
                  <p className="text-sm text-amber-800 whitespace-pre-wrap">{thinking}</p>
                </div>
              )}

              {/* 执行动作 */}
              {action && (
                <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                  <div className="flex items-center gap-2 mb-2">
                    <ApiOutlined className="text-blue-500" />
                    <span className="text-sm font-medium text-blue-700">执行动作</span>
                  </div>
                  <div className="bg-white rounded-md p-2 border border-blue-200">
                    <code className="text-sm text-blue-800 font-mono">
                      {action}({Object.entries(actionParams).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
                    </code>
                  </div>
                </div>
              )}
            </div>

            {/* 右侧截图区域 */}
            {screenshot && (
              <div className="w-48 flex-shrink-0">
                <div className="flex items-center gap-2 mb-2">
                  <CameraOutlined className="text-gray-500" />
                  <span className="text-sm font-medium text-gray-600">屏幕快照</span>
                </div>
                <Image
                  src={screenshot.startsWith('data:') ? screenshot : `data:image/png;base64,${screenshot}`}
                  alt="截图"
                  className="rounded-lg border border-gray-200"
                  style={{ maxWidth: '100%', maxHeight: '200px' }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// 执行完成后的操作按钮组件
function CompletionActions({ message, onSave, onAnalyze }: { 
  message: Message; 
  onSave?: (msg: Message) => void;
  onAnalyze?: (msg: Message) => void;
}) {
  return (
    <div className="bg-blue-50 rounded-xl p-4 border border-blue-100 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <ThunderboltOutlined className="text-blue-500" />
        <span className="text-sm text-blue-600">探索模式：任务完成后可直接保存驱动指令</span>
      </div>
      <div className="flex gap-3">
        <Button
          type="primary"
          danger
          icon={<SaveOutlined />}
          onClick={() => onSave?.(message)}
          className="rounded-lg"
        >
          保存驱动指令
        </Button>
        <Button
          icon={<BarChartOutlined />}
          onClick={() => onAnalyze?.(message)}
          className="rounded-lg"
        >
          添加后置分析
        </Button>
      </div>
    </div>
  );
}

export function MessageList({ messages, onSaveInstruction, onAddAnalysis }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 判断消息是否已完成（有步骤且不在流式状态）
  const isMessageComplete = (msg: Message) => {
    return msg.steps && msg.steps.length > 0 && !msg.isStreaming;
  };

  return (
    <div className="space-y-4">
      {messages.map((msg) => {
        const config = roleConfig[msg.role];
        const isLastMessage = msg.id === messages[messages.length - 1]?.id;
        const showActions = isLastMessage && isMessageComplete(msg);

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
              <div className="max-w-[90%] w-full space-y-3">
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

                {/* 执行完成后的操作按钮 */}
                {showActions && (
                  <CompletionActions
                    message={msg}
                    onSave={onSaveInstruction}
                    onAnalyze={onAddAnalysis}
                  />
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
