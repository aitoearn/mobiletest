import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Space, Tag, Spin, message } from "antd";
import { ArrowLeftOutlined, HistoryOutlined, ClearOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { ScrcpyPlayer } from "@/components/ScrcpyPlayer";
import { MessageList, ChatInput } from "@/components/chat";
import { useChatStream } from "@/hooks/useChatStream";
import type { Device } from "@/types";

export default function Test() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState("");

  const { messages, sending, sendMessage, abort, clear } = useChatStream({
    deviceId,
    onError: (error) => message.error(`错误: ${error}`),
  });

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

  const handleSend = () => {
    if (!inputValue.trim()) return;
    sendMessage(inputValue);
    setInputValue("");
  };

  const handleClear = () => {
    clear();
    message.info("对话已清空");
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

      <div className="flex-1 flex overflow-hidden">
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

        <div className="flex-1 flex flex-col bg-white">
          <div className="px-6 py-4 border-b">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
                <ThunderboltOutlined style={{ fontSize: 24, color: "white" }} />
              </div>
              <div>
                <h2 className="text-xl font-bold mb-1">UI Genie 智能驱动</h2>
                <p className="text-sm text-gray-500">
                  请在右侧输入框描述操作，或直接输入具体指令:
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            <MessageList messages={messages} />
          </div>

          <div className="border-t p-4 bg-gray-50">
            <div className="max-w-4xl mx-auto">
              <ChatInput
                value={inputValue}
                onChange={setInputValue}
                onSend={handleSend}
                onAbort={abort}
                sending={sending}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
