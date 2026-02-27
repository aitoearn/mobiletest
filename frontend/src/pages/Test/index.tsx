import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Space, Tag, Spin, message, Select, Drawer, Input, Card, List } from "antd";
import { ArrowLeftOutlined, ClearOutlined, ThunderboltOutlined, RobotOutlined, BarChartOutlined, PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { ScrcpyPlayer } from "@/components/ScrcpyPlayer";
import { MessageList, ChatInput } from "@/components/chat";
import { useChatStream } from "@/hooks/useChatStream";
import type { Device, Message } from "@/types";

const { Option } = Select;
const { TextArea } = Input;

interface Engine {
  id: string;
  name: string;
  model: string;
  prompt?: string;
}

interface AnalysisRule {
  id: string;
  content: string;
}

export default function Test() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState("");
  const [engines, setEngines] = useState<Engine[]>([]);
  const [selectedEngineId, setSelectedEngineId] = useState<string>("");
  
  // 后置分析侧边栏状态
  const [analysisDrawerOpen, setAnalysisDrawerOpen] = useState(false);
  const [analysisRules, setAnalysisRules] = useState<AnalysisRule[]>([]);
  const [newRule, setNewRule] = useState("");
  const [currentMessage, setCurrentMessage] = useState<Message | null>(null);
  const lastUserInputRef = useRef<string>("");

  const { messages, sending, sendMessage, abort, clear } = useChatStream({
    deviceId,
    engineId: selectedEngineId || undefined,
    onError: (error) => message.error(`错误: ${error}`),
  });
  // console.log("messages:", messages);

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

    // 获取引擎列表
    const fetchEngines = async () => {
      try {
        const response = await fetch("/api/v1/engines");
        const data = await response.json();
        if (data.code === 0 && data.data) {
          setEngines(data.data);
          // 如果有引擎，默认选择第一个
          if (data.data.length > 0) {
            setSelectedEngineId(data.data[0].id);
          }
        }
      } catch (error) {
        console.error("获取引擎列表失败:", error);
      }
    };

    fetchDevice();
    fetchEngines();
  }, [deviceId, navigate]);

  const handleSend = () => {
    if (!inputValue.trim()) return;
    lastUserInputRef.current = inputValue;
    sendMessage(inputValue);
    setInputValue("");
  };

  const handleClear = () => {
    clear();
    message.info("对话已清空");
  };

  // 保存指令到用例管理
  const handleSaveInstruction = async (msg: Message) => {
    const engine = engines.find(e => e.id === selectedEngineId);
    if (!engine) {
      message.error("未找到执行引擎信息");
      return;
    }

    console.log("Saving instruction:", inputValue);
    try {
      const res = await fetch("/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: lastUserInputRef.current.slice(0, 50) + (lastUserInputRef.current.length > 50 ? "..." : ""),
          description: msg.content,
          content: {
            steps: msg.steps?.map((step, idx) => ({
              step_number: idx + 1,
              action: step.toolName || "execute",
              target: step.content,
              params: step.toolArgs,
            })),
            engine_id: selectedEngineId,
            engine_name: engine.name,
            engine_model: engine.model,
            engine_prompt: engine.prompt,
          },
          tags: ["chat", engine.name],
        }),
      });

      if (res.ok) {
        message.success("指令已保存到用例管理");
      } else {
        message.error("保存失败");
      }
    } catch (error) {
      console.error("保存指令失败:", error);
      message.error("保存失败");
    }
  };

  // 打开后置分析侧边栏
  const handleAddAnalysis = (msg: Message) => {
    setCurrentMessage(msg);
    setAnalysisDrawerOpen(true);
  };

  // 添加分析规则
  const handleAddRule = () => {
    if (!newRule.trim()) return;
    setAnalysisRules([...analysisRules, { id: Date.now().toString(), content: newRule }]);
    setNewRule("");
  };

  // 删除分析规则
  const handleDeleteRule = (id: string) => {
    setAnalysisRules(analysisRules.filter(r => r.id !== id));
  };

  // 执行分析
  const handleExecuteAnalysis = async () => {
    if (analysisRules.length === 0) {
      message.warning("请先添加分析规则");
      return;
    }

    message.info("分析功能开发中...");
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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
                  <ThunderboltOutlined style={{ fontSize: 24, color: "white" }} />
                </div>
                <div>
                  <h2 className="text-xl font-bold mb-1">UI 智能驱动</h2>
                  <p className="text-sm text-gray-500">
                    请在右侧输入框描述操作，或直接输入具体指令:
                  </p>
                </div>
              </div>
              
              {/* 引擎选择器 */}
              <div className="flex items-center gap-2">
                <RobotOutlined className="text-gray-400" />
                <Select
                  placeholder="选择执行引擎"
                  value={selectedEngineId}
                  onChange={setSelectedEngineId}
                  style={{ width: 200 }}
                  className="rounded-lg"
                >
                  {engines.map((engine) => (
                    <Option key={engine.id} value={engine.id}>
                      <div className="flex items-center gap-2">
                        <span>{engine.name}</span>
                        <span className="text-xs text-gray-400">{engine.model}</span>
                      </div>
                    </Option>
                  ))}
                </Select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            <MessageList 
              messages={messages} 
              onSaveInstruction={handleSaveInstruction}
              onAddAnalysis={handleAddAnalysis}
            />
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

      {/* 后置分析侧边栏 */}
      <Drawer
        title="后置分析"
        placement="right"
        width={480}
        onClose={() => setAnalysisDrawerOpen(false)}
        open={analysisDrawerOpen}
      >
        <div className="space-y-6">
          {/* 结果分析助手 */}
          <Card title="结果分析助手" className="border-0 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <BarChartOutlined className="text-blue-500" />
              <span className="font-medium">基础断言助手</span>
              <Tag color="blue">v2</Tag>
            </div>
            <div className="text-sm text-gray-500 mb-2">
              模型: {engines.find(e => e.id === selectedEngineId)?.model || "-"}
            </div>
          </Card>

          {/* 分析规则 */}
          <Card 
            title={`分析规则 (${analysisRules.length}条)`} 
            className="border-0 shadow-sm"
          >
            <div className="space-y-3">
              {analysisRules.map((rule, index) => (
                <div key={rule.id} className="flex items-start gap-2">
                  <span className="text-gray-400 text-sm mt-1">{index + 1}.</span>
                  <div className="flex-1 bg-gray-50 rounded-lg p-2 text-sm">
                    {rule.content}
                  </div>
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteRule(rule.id)}
                  />
                </div>
              ))}
              
              <div className="flex gap-2">
                <TextArea
                  placeholder="输入分析规则，如：页面成功跳转到..."
                  value={newRule}
                  onChange={(e) => setNewRule(e.target.value)}
                  rows={2}
                  className="flex-1"
                />
              </div>
              <Button
                type="dashed"
                block
                icon={<PlusOutlined />}
                onClick={handleAddRule}
                disabled={!newRule.trim()}
              >
                添加规则
              </Button>
            </div>
          </Card>

          {/* 执行分析按钮 */}
          <Button
            type="primary"
            block
            size="large"
            icon={<BarChartOutlined />}
            onClick={handleExecuteAnalysis}
            disabled={analysisRules.length === 0}
          >
            执行分析
          </Button>
          
          {analysisRules.length === 0 && (
            <p className="text-xs text-gray-400 text-center">
              请先保存驱动指令后再保存分析规则
            </p>
          )}
        </div>
      </Drawer>
    </div>
  );
}
