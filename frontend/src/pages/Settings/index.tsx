import { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Space,
  Divider,
  Tooltip,
  Select,
  Spin,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  GlobalOutlined,
  ApiOutlined,
  LinkOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloudSyncOutlined,
} from "@ant-design/icons";

const { Option } = Select;

interface LLMConfig {
  baseUrl: string;
  apiKey: string;
  selectedModels: string[];
  defaultMaxSteps: number;
  layeredMaxTurns: number;
  // 为每个供应商保存独立的 API Key 和模型
  providerApiKeys: Record<string, string>;
  providerModels: Record<string, string[]>;
}

interface ModelInfo {
  id: string;
  name: string;
  description?: string;
}

const PROVIDER_PRESETS = [
  {
    name: "bigmodel",
    displayName: "智谱 BigModel",
    description: "智谱 AI GLM 系列模型",
    icon: "🤖",
    color: "#3b82f6",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    apiKeyUrl: "https://open.bigmodel.cn/api-keys",
  },
  {
    name: "qwen",
    displayName: "阿里通义千问",
    description: "阿里云 DashScope API 服务",
    icon: "☁️",
    color: "#ff6a00",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    apiKeyUrl: "https://dashscope.console.aliyun.com/apiKey",
  },
  {
    name: "modelscope",
    displayName: "阿里云魔搭社区",
    description: "阿里云魔搭社区模型服务",
    icon: "🔬",
    color: "#8b5cf6",
    baseUrl: "https://api-inference.modelscope.cn/v1",
    apiKeyUrl: "https://modelscope.cn/my/myaccesstoken",
  },
  {
    name: "custom",
    displayName: "自建服务",
    description: "vLLM / Ollama 等自建服务",
    icon: "🔧",
    color: "#6b7280",
    baseUrl: "http://localhost:11434/v1",
    apiKeyUrl: null,
  },
];

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch("/api/v1/settings/llm");
      if (res.ok) {
        const data = await res.json();
        
        // 找到匹配的供应商
        const preset = PROVIDER_PRESETS.find(
          (p) => p.baseUrl === data.baseUrl
        );
        
        if (preset) {
          setSelectedPreset(preset.name);
          
          // 加载该供应商对应的 API Key 和模型
          const providerApiKeys = data.providerApiKeys || {};
          const providerModels = data.providerModels || {};
          const savedApiKey = providerApiKeys[preset.name] || data.apiKey || "";
          const savedModels = providerModels[preset.name] || data.selectedModels || [];
          
          form.setFieldsValue({
            ...data,
            apiKey: savedApiKey,
            selectedModels: savedModels,
          });
          
          // 如果有已保存的模型，设置到可用模型列表
          if (savedModels.length > 0) {
            setAvailableModels(
              savedModels.map((m: string) => ({ id: m, name: m, description: "多模态" }))
            );
          }
        } else {
          form.setFieldsValue(data);
        }
      }
    } catch (error) {
      console.error("Failed to load config:", error);
    }
  };

  const handleSave = async (values: LLMConfig) => {
    setLoading(true);
    try {
      // 从表单获取当前已保存的 providerApiKeys 和 providerModels（包含其他供应商的数据）
      const currentProviderApiKeys = form.getFieldValue("providerApiKeys") || {};
      const currentProviderModels = form.getFieldValue("providerModels") || {};
      
      // 保存当前供应商的 API Key 和模型
      if (selectedPreset) {
        if (values.apiKey) {
          currentProviderApiKeys[selectedPreset] = values.apiKey;
        }
        if (values.selectedModels) {
          currentProviderModels[selectedPreset] = values.selectedModels;
        }
      }
      
      const saveData = {
        ...values,
        providerApiKeys: currentProviderApiKeys,
        providerModels: currentProviderModels,
      };
      
      const res = await fetch("/api/v1/settings/llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saveData),
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

  const applyPreset = (preset: typeof PROVIDER_PRESETS[0]) => {
    const currentProvider = selectedPreset;
    const currentApiKey = form.getFieldValue("apiKey") || "";
    const currentModels = form.getFieldValue("selectedModels") || [];
    
    // 保存当前供应商的 API Key 和模型
    const providerApiKeys = form.getFieldValue("providerApiKeys") || {};
    const providerModels = form.getFieldValue("providerModels") || {};
    
    if (currentProvider) {
      if (currentApiKey) {
        providerApiKeys[currentProvider] = currentApiKey;
      }
      if (currentModels.length > 0) {
        providerModels[currentProvider] = currentModels;
      }
    }
    
    setSelectedPreset(preset.name);
    
    // 切换供应商时，加载该供应商保存的 API Key 和模型
    const savedApiKey = providerApiKeys[preset.name] || "";
    const savedModels = providerModels[preset.name] || [];
    
    form.setFieldsValue({
      baseUrl: preset.baseUrl,
      apiKey: savedApiKey,
      selectedModels: savedModels,
      providerApiKeys: providerApiKeys,
      providerModels: providerModels,
    });
    
    // 如果有已保存的模型，设置到可用模型列表
    if (savedModels.length > 0) {
      setAvailableModels(
        savedModels.map((m: string) => ({ id: m, name: m, description: "多模态" }))
      );
    } else {
      setAvailableModels([]);
    }
  };

  const fetchModels = async () => {
    const baseUrl = form.getFieldValue("baseUrl");
    const apiKey = form.getFieldValue("apiKey");
    
    if (!baseUrl) {
      message.error("请先填写 Base URL");
      return;
    }

    setFetchingModels(true);
    try {
      const res = await fetch("/api/v1/settings/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseUrl, apiKey }),
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.code === 0 && data.data) {
          setAvailableModels(data.data);
          message.success(`获取到 ${data.data.length} 个模型`);
        } else {
          message.error(data.message || "获取模型列表失败");
        }
      } else {
        message.error("获取模型列表失败");
      }
    } catch (error) {
      message.error("获取模型列表失败: " + error);
    } finally {
      setFetchingModels(false);
    }
  };

  const renderPresetCard = (
    preset: typeof PROVIDER_PRESETS[0],
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
              <p className="text-gray-500 text-sm">配置 LLM API 以获取模型列表</p>
            </div>
          </div>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            baseUrl: "",
            apiKey: "",
            selectedModels: [],
            defaultMaxSteps: 100,
            layeredMaxTurns: 50,
            providerApiKeys: {},
            providerModels: {},
          }}
        >
          <div className="max-w-3xl">
            <Card className="shadow-sm border-0 rounded-xl mb-6">
              <div className="flex items-center gap-2 mb-4">
                <CloudSyncOutlined className="text-blue-500" />
                <span className="font-semibold text-gray-900">模型提供商</span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    选择提供商
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {PROVIDER_PRESETS.map((preset) =>
                      renderPresetCard(
                        preset,
                        selectedPreset === preset.name,
                        () => applyPreset(preset)
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
                  name="baseUrl"
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
                  name="apiKey"
                >
                  <Input.Password
                    placeholder="sk-..."
                    className="rounded-lg"
                    iconRender={(visible) =>
                      visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
                    }
                    visibilityToggle={{
                      visible: showApiKey,
                      onVisibleChange: setShowApiKey,
                    }}
                  />
                </Form.Item>

                <div className="flex justify-end">
                  <Button
                    icon={<CloudSyncOutlined />}
                    onClick={fetchModels}
                    loading={fetchingModels}
                    className="rounded-lg"
                  >
                    获取模型列表
                  </Button>
                </div>

                <Form.Item
                  label={
                    <span className="flex items-center gap-1 text-gray-700">
                      <ApiOutlined className="text-gray-400" />
                      选择多模态模型（可多选）
                    </span>
                  }
                  name="selectedModels"
                >
                  <Select
                    mode="multiple"
                    placeholder={fetchingModels ? "获取中..." : availableModels.length === 0 ? "请先点击获取模型列表" : "选择模型"}
                    loading={fetchingModels}
                    className="rounded-lg"
                    disabled={availableModels.length === 0}
                  >
                    {availableModels.map((model) => (
                      <Option key={model.id} value={model.id}>
                        <div className="flex flex-col">
                          <span>{model.name}</span>
                          {model.description && (
                            <span className="text-xs text-gray-400">{model.description}</span>
                          )}
                        </div>
                      </Option>
                    ))}
                  </Select>
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

            <div className="flex justify-between items-center">
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
          </div>
        </Form>
      </div>
    </div>
  );
}
