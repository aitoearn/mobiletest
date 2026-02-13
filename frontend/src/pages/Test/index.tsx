import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Input,
  Button,
  Space,
  Tag,
  Avatar,
  Spin,
  message,
} from "antd";
import {
  SendOutlined,
  ThunderboltOutlined,
  ArrowLeftOutlined,
  UserOutlined,
  RobotOutlined,
  HistoryOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import { ScrcpyPlayer } from "@/components/ScrcpyPlayer";

const { TextArea } = Input;

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

interface Device {
  device_id: string;
  model: string;
  brand: string;
  status: string;
}

export default function Test() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 获取设备信息
  useEffect(() => {
    const fetchDevice = async () => {
      try {
        const response = await fetch("/api/v1/devices/scan");
        const data = await response.json();
        const foundDevice = data.devices?.find(
          (d: Device) => d.device_id === deviceId
        );
        if (foundDevice) {
          setDevice(foundDevice);
          // 添加欢迎消息
          setMessages([
            {
              id: "welcome",
              role: "system",
              content: `已连接设备: ${foundDevice.model || foundDevice.device_id}`,
              timestamp: new Date(),
            },
            {
              id: "intro",
              role: "assistant",
              content:
                "你好！我是 UI Genie 智能驱动助手。请在右侧输入框描述你想执行的操作，或直接输入具体指令。",
              timestamp: new Date(),
            },
          ]);
        } else {
          message.error("设备不存在");
          navigate("/devices");
        }
      } catch (error) {
        message.error("获取设备信息失败");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchDevice();
  }, [deviceId, navigate]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setSending(true);

    try {
      // TODO: 调用后端 API
      const response = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: inputValue,
          device_id: deviceId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.message || "操作已执行",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error("请求失败");
      }
    } catch (error) {
      message.error("发送失败，请重试");
      console.error(error);
    } finally {
      setSending(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: "cleared",
        role: "system",
        content: "对话已清空",
        timestamp: new Date(),
      },
    ]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/devices")}
          >
            返回
          </Button>
          <div className="flex items-center gap-2">
            <Tag color="green" className="mb-0">
              在线
            </Tag>
            <span className="font-medium">
              {device?.model || device?.device_id}
            </span>
          </div>
        </Space>
        <Space>
          <Button icon={<HistoryOutlined />}>执行历史</Button>
          <Button icon={<ClearOutlined />} onClick={handleClear}>
            清空对话
          </Button>
        </Space>
      </div>

      {/* 主内容区 - 左右分栏 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：设备屏幕 */}
        <div className="w-1/3 bg-gray-100 flex items-center justify-center p-6">
          <div
            className="shadow-lg rounded-lg overflow-hidden"
            style={{
              width: "300px",
              aspectRatio: "9/19.5",
            }}
          >
            {deviceId && (
              <ScrcpyPlayer
                deviceId={deviceId}
                enableControl={true}
                onTapSuccess={() => console.log("Tap success")}
                onTapError={(error) => message.error(`点击失败: ${error}`)}
                onSwipeSuccess={() => console.log("Swipe success")}
                onSwipeError={(error) => message.error(`滑动失败: ${error}`)}
              />
            )}
          </div>
        </div>

        {/* 右侧：对话区域 */}
        <div className="flex-1 flex flex-col bg-white">
          {/* 标题 */}
          <div className="px-6 py-4 border-b">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
                <ThunderboltOutlined style={{ fontSize: 24, color: "white" }} />
              </div>
              <div>
                <h2 className="text-xl font-bold mb-1">UI Genie 智能驱动</h2>
                <p className="text-sm text-gray-500">
                  请在右侧输入框描述操作，或直接输入具体指令
                </p>
              </div>
            </div>
          </div>

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <div className="space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "flex-row-reverse" : ""
                  }`}
                >
                  {/* 头像 */}
                  <Avatar
                    icon={
                      msg.role === "user" ? (
                        <UserOutlined />
                      ) : msg.role === "assistant" ? (
                        <RobotOutlined />
                      ) : (
                        <ThunderboltOutlined />
                      )
                    }
                    style={{
                      backgroundColor:
                        msg.role === "user"
                          ? "#1890ff"
                          : msg.role === "assistant"
                          ? "#52c41a"
                          : "#faad14",
                    }}
                  />

                  {/* 消息内容 */}
                  <div
                    className={`flex-1 ${
                      msg.role === "user" ? "text-right" : ""
                    }`}
                  >
                    <div
                      className={`inline-block max-w-[80%] p-3 rounded-lg ${
                        msg.role === "user"
                          ? "bg-blue-500 text-white"
                          : msg.role === "system"
                          ? "bg-gray-100 text-gray-600"
                          : "bg-green-50 text-gray-800 border border-green-200"
                      }`}
                    >
                      {msg.content}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {msg.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* 输入框 */}
          <div className="border-t p-4 bg-gray-50">
            <div className="max-w-4xl mx-auto">
              <div className="bg-white rounded-lg border shadow-sm p-2">
                <TextArea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="输入指令 / 使用自然语言描述操作（支持步骤描述）..."
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  bordered={false}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <div className="flex justify-between items-center mt-2">
                  <Space size="small">
                    <Tag color="blue" className="m-0">
                      自然语言
                    </Tag>
                    <Tag color="green" className="m-0">
                      多步骤
                    </Tag>
                  </Space>
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={sending}
                    disabled={!inputValue.trim()}
                  >
                    发送
                  </Button>
                </div>
              </div>
              <div className="text-xs text-gray-400 mt-2 text-center">
                按 Enter 发送，Shift+Enter 换行
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
