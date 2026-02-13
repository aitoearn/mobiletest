import { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Divider,
  message,
  Tag,
} from "antd";
import { SaveOutlined, ReloadOutlined } from "@ant-design/icons";

interface LLMConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
}

const providerOptions = [
  { value: "openai", label: "OpenAI", color: "green" },
  { value: "anthropic", label: "Anthropic Claude", color: "blue" },
  { value: "qwen", label: "阿里 Qwen", color: "orange" },
  { value: "local", label: "本地模型", color: "purple" },
];

const modelOptions: Record<string, { value: string; label: string }[]> = {
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
    { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
  ],
  anthropic: [
    { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
    { value: "claude-3-5-sonnet-20240620", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-opus-20240229", label: "Claude 3 Opus" },
  ],
  qwen: [
    { value: "qwen-max", label: "Qwen Max" },
    { value: "qwen-plus", label: "Qwen Plus" },
    { value: "qwen-turbo", label: "Qwen Turbo" },
  ],
  local: [
    { value: "local-model", label: "本地模型" },
  ],
};

export default function Settings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("openai");

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch("/api/v1/settings/llm");
      if (res.ok) {
        const data = await res.json();
        form.setFieldsValue(data);
        setProvider(data.provider || "openai");
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

  return (
    <div className="p-6">
      <h1 className="text-2xl font-display mb-6 text-text-primary">系统设置</h1>
      
      <Card className="bg-background-secondary border-gray-700 mb-6">
        <h2 className="text-lg font-medium mb-4 text-text-primary">LLM 模型配置</h2>
        
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            provider: "openai",
            model: "gpt-4o",
            apiKey: "",
            baseUrl: "",
          }}
        >
          <Form.Item label="模型供应商" name="provider" rules={[{ required: true }]}>
            <Select
              onChange={(value) => setProvider(value)}
              options={providerOptions.map((p) => ({
                ...p,
                label: <Tag color={p.color}>{p.label}</Tag>,
              }))}
            />
          </Form.Item>

          <Form.Item label="模型" name="model" rules={[{ required: true }]}>
            <Select options={modelOptions[provider] || []} />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="apiKey"
            rules={[{ required: provider !== "local" }]}
          >
            <Input.Password placeholder="请输入 API Key" />
          </Form.Item>

          {provider === "local" ? (
            <Form.Item label="本地模型地址" name="baseUrl">
              <Input placeholder="http://localhost:11434/v1" />
            </Form.Item>
          ) : null}

          {provider === "qwen" ? (
            <Form.Item label="DashScope API Key" name="apiKey">
              <Input.Password placeholder="请输入 DashScope API Key" />
            </Form.Item>
          ) : null}

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={loading}
              >
                保存配置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleTest}
                loading={loading}
              >
                测试连接
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Divider />

      <Card className="bg-background-secondary border-gray-700">
        <h2 className="text-lg font-medium mb-4 text-text-primary">环境变量参考</h2>
        <pre className="bg-gray-900 p-4 rounded text-sm text-gray-300 overflow-x-auto">
{`# OpenAI (默认)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
LLM_BASE_URL=

# Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-...

# 阿里 Qwen
LLM_PROVIDER=qwen
LLM_MODEL=qwen-max
LLM_API_KEY=sk-...

# 本地模型 (Ollama)
LLM_PROVIDER=local
LLM_MODEL=local-model
LLM_BASE_URL=http://localhost:11434/v1`}
        </pre>
      </Card>
    </div>
  );
}
