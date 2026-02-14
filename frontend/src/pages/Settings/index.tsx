import { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  Tabs,
  message,
  Space,
  Divider,
  Tooltip,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  GlobalOutlined,
  ApiOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  LinkOutlined,
  SettingOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";

interface LLMConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
  agentType: string;
  defaultMaxSteps: number;
  layeredMaxTurns: number;
  visionBaseUrl: string;
  visionModelName: string;
  visionApiKey: string;
  decisionBaseUrl: string;
  decisionModelName: string;
  decisionApiKey: string;
}

const VISION_PRESETS = [
  {
    name: "bigmodel",
    displayName: "智谱 BigModel",
    description: "智谱 AI GLM 系列模型",
    icon: "🤖",
    color: "#3b82f6",
    config: {
      baseUrl: "https://open.bigmodel.cn/api/paas/v4",
      modelName: "glm-4-plus",
    },
    apiKeyUrl: "https://open.bigmodel.cn/api-keys",
  },
  {
    name: "modelscope",
    displayName: "ModelScope",
    description: "阿里云魔搭社区模型服务",
    icon: "🔬",
    color: "#8b5cf6",
    config: {
      baseUrl: "https://api-inference.modelscope.cn/v1",
      modelName: "Qwen/Qwen2.5-72B-Instruct",
    },
    apiKeyUrl: "https://modelscope.cn/my/myaccesstoken",
  },
  {
    name: "qwen",
    displayName: "阿里通义千问",
    description: "阿里云 DashScope API 服务",
    icon: "☁️",
    color: "#ff6a00",
    config: {
      baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      modelName: "qwen-max",
    },
    apiKeyUrl: "https://dashscope.console.aliyun.com/apiKey",
  },
  {
    name: "custom",
    displayName: "自建服务",
    description: "vLLM / Ollama 等自建服务",
    icon: "🔧",
    color: "#6b7280",
    config: {
      baseUrl: "http://localhost:11434/v1",
      modelName: "local-model",
    },
  },
];

const DECISION_PRESETS = [...VISION_PRESETS];

const AGENT_TYPES = [
  {
    name: "glm-async",
    displayName: "GLM Agent",
    description: "基于 GLM 模型优化，成熟稳定，适合大多数任务",
    icon: <RobotOutlined />,
    color: "#1890ff",
  },
  {
    name: "mai",
    displayName: "MAI Agent",
    description: "阿里通义团队开发，支持多张历史截图上下文",
    icon: <ThunderboltOutlined />,
    color: "#722ed1",
  },
];

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("vision");
  const [showVisionApiKey, setShowVisionApiKey] = useState(false);
  const [showDecisionApiKey, setShowDecisionApiKey] = useState(false);
  const [selectedVisionPreset, setSelectedVisionPreset] = useState("");
  const [selectedDecisionPreset, setSelectedDecisionPreset] = useState("");

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch("/api/v1/settings/llm");
      if (res.ok) {
        const data = await res.json();
        form.setFieldsValue(data);
        
        const visionPreset = VISION_PRESETS.find(
          (p) => p.config.baseUrl === data.visionBaseUrl
        );
        if (visionPreset) {
          setSelectedVisionPreset(visionPreset.name);
        }
        
        const decisionPreset = DECISION_PRESETS.find(
          (p) => p.config.baseUrl === data.decisionBaseUrl
        );
        if (decisionPreset) {
          setSelectedDecisionPreset(decisionPreset.name);
        }
      }
    } catch (error) {
      console.error("Failed to load config:", error);
    }
  };

  const handleSave = async (values: LLMConfig) => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/settings/llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (res.ok) {
        message.success("配置保存成功");
      } else {
        message.error("保存失败");
      }
    } catch (error) {
      message.error("保存失败: " + error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/settings/llm/test", {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        message.success("连接测试成功");
      } else {
        message.error("连接测试失败: " + data.message);
      }
    } catch (error) {
      message.error("测试失败: " + error);
    } finally {
      setLoading(false);
    }
  };

  const applyVisionPreset = (preset: typeof VISION_PRESETS[0]) => {
    setSelectedVisionPreset(preset.name);
    form.setFieldsValue({
      visionBaseUrl: preset.config.baseUrl,
      visionModelName: preset.config.modelName,
    });
  };

  const applyDecisionPreset = (preset: typeof DECISION_PRESETS[0]) => {
    setSelectedDecisionPreset(preset.name);
    form.setFieldsValue({
      decisionBaseUrl: preset.config.baseUrl,
      decisionModelName: preset.config.modelName,
    });
  };

  const renderPresetCard = (
    preset: typeof VISION_PRESETS[0],
    isSelected: boolean,
    onClick: () => void
  ) => (
    <div
      key={preset.name}
      onClick={onClick}
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200
        border-2 group
        ${isSelected
          ? "border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-50 shadow-md"
          : "border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm"
        }
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
            style={{ backgroundColor: `${preset.color}15` }}
          >
            {preset.icon}
          </div>
          <div>
            <div className="font-semibold text-gray-900">{preset.displayName}</div>
            <div className="text-sm text-gray-500">{preset.description}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isSelected && (
            <CheckCircleOutlined className="text-blue-500 text-lg" />
          )}
          {preset.apiKeyUrl && (
            <Tooltip title="获取 API Key">
              <a
                href={preset.apiKeyUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors opacity-0 group-hover:opacity-100"
              >
                <LinkOutlined className="text-gray-400 hover:text-blue-500" />
              </a>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="px-8 py-6">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <SettingOutlined className="text-white text-lg" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>
              <p className="text-gray-500 text-sm">配置您的 API 设置以开始使用</p>
            </div>
          </div>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            provider: "openai",
            model: "gpt-4o",
            apiKey: "",
            baseUrl: "",
            agentType: "glm-async",
            defaultMaxSteps: 100,
            layeredMaxTurns: 50,
            visionBaseUrl: "",
            visionModelName: "",
            visionApiKey: "",
            decisionBaseUrl: "",
            decisionModelName: "",
            decisionApiKey: "",
          }}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="shadow-sm border-0 rounded-xl">
              <div className="flex items-center gap-2 mb-4">
                <EyeOutlined className="text-blue-500" />
                <span className="font-semibold text-gray-900">视觉模型</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择预设配置
                  </label>
                  <div className="grid grid-cols-1 gap-2">
                    {VISION_PRESETS.map((preset) =>
                      renderPresetCard(
                        preset,
                        selectedVisionPreset === preset.name,
                        () => applyVisionPreset(preset)
                      )
                    )}
                  </div>
                </div>

                <Divider className="my-4" />

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <GlobalOutlined className="text-gray-400" />
                      Base URL <span className="text-red-500">*</span>
                    </span>
                  }
                  name="visionBaseUrl"
                  rules={[
                    { required: true, message: "请输入 Base URL" },
                    { 
                      pattern: /^https?:\/\/.+/,
                      message: "URL 必须以 http:// 或 https:// 开头"
                    }
                  ]}
                >
                  <Input placeholder="https://api.openai.com/v1" className="rounded-lg" />
                </Form.Item>

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <ApiOutlined className="text-gray-400" />
                      API Key
                    </span>
                  }
                  name="visionApiKey"
                >
                  <Input.Password
                    placeholder="Leave empty if not required"
                    className="rounded-lg"
                    iconRender={(visible) =>
                      visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
                    }
                    visibilityToggle={{
                      visible: showVisionApiKey,
                      onVisibleChange: setShowVisionApiKey,
                    }}
                  />
                </Form.Item>

                <Form.Item
                  label={<span className="text-gray-700">模型名称</span>}
                  name="visionModelName"
                  rules={[{ required: true, message: "请输入模型名称" }]}
                >
                  <Input placeholder="gpt-4o" className="rounded-lg" />
                </Form.Item>

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <RobotOutlined className="text-gray-400" />
                      Agent 类型
                    </span>
                  }
                  name="agentType"
                >
                  <div className="grid grid-cols-2 gap-2">
                    {AGENT_TYPES.map((agent) => {
                      const isSelected = form.getFieldValue("agentType") === agent.name;
                      return (
                        <div
                          key={agent.name}
                          onClick={() => form.setFieldValue("agentType", agent.name)}
                          className={`
                            p-3 rounded-xl cursor-pointer transition-all border-2
                            ${isSelected
                              ? "border-blue-500 bg-blue-50"
                              : "border-gray-200 hover:border-blue-300 bg-white"
                            }
                          `}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span style={{ color: isSelected ? agent.color : "#9ca3af" }}>
                              {agent.icon}
                            </span>
                            <span className={`font-medium text-sm ${isSelected ? "text-gray-900" : "text-gray-600"}`}>
                              {agent.displayName}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 line-clamp-2">
                            {agent.description}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </Form.Item>

                <div className="grid grid-cols-2 gap-4">
                  <Form.Item label={<span className="text-gray-700">最大执行步数</span>} name="defaultMaxSteps">
                    <Input type="number" min={1} max={1000} className="rounded-lg" />
                  </Form.Item>
                  <Form.Item label={<span className="text-gray-700">分层代理轮次</span>} name="layeredMaxTurns">
                    <Input type="number" min={1} className="rounded-lg" />
                  </Form.Item>
                </div>
              </div>
            </Card>

            <Card className="shadow-sm border-0 rounded-xl">
              <div className="flex items-center gap-2 mb-4">
                <ThunderboltOutlined className="text-indigo-500" />
                <span className="font-semibold text-gray-900">决策模型</span>
              </div>

              <div className="space-y-4">
                <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-3">
                  <div className="flex items-start gap-2">
                    <InfoCircleOutlined className="text-indigo-500 mt-0.5" />
                    <div className="text-sm text-indigo-900">
                      决策模型用于分层代理的规划阶段。如果不配置，将使用视觉模型作为决策模型。
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择预设配置
                  </label>
                  <div className="grid grid-cols-1 gap-2">
                    {DECISION_PRESETS.map((preset) =>
                      renderPresetCard(
                        preset,
                        selectedDecisionPreset === preset.name,
                        () => applyDecisionPreset(preset)
                      )
                    )}
                  </div>
                </div>

                <Divider className="my-4" />

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <GlobalOutlined className="text-gray-400" />
                      Base URL
                    </span>
                  }
                  name="decisionBaseUrl"
                  rules={[
                    { 
                      pattern: /^https?:\/\/.+|^$/,
                      message: "URL 必须以 http:// 或 https:// 开头"
                    }
                  ]}
                >
                  <Input placeholder="https://api.openai.com/v1" className="rounded-lg" />
                </Form.Item>

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <ApiOutlined className="text-gray-400" />
                      API Key
                    </span>
                  }
                  name="decisionApiKey"
                >
                  <Input.Password
                    placeholder="sk-..."
                    className="rounded-lg"
                    iconRender={(visible) =>
                      visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
                    }
                    visibilityToggle={{
                      visible: showDecisionApiKey,
                      onVisibleChange: setShowDecisionApiKey,
                    }}
                  />
                </Form.Item>

                <Form.Item
                  label={<span className="text-gray-700">模型名称</span>}
                  name="decisionModelName"
                >
                  <Input placeholder="gpt-4o" className="rounded-lg" />
                </Form.Item>
              </div>
            </Card>
          </div>

          <div className="mt-6 flex justify-between items-center">
            <Button
              onClick={() => {
                fetchConfig();
                message.info("已重置为保存的配置");
              }}
              className="rounded-lg"
            >
              取消
            </Button>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleTest}
                loading={loading}
                className="rounded-lg"
              >
                测试连接
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={loading}
                className="rounded-lg"
              >
                保存配置
              </Button>
            </Space>
          </div>
        </Form>
      </div>
    </div>
  );
}
