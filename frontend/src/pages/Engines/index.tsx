import { useState, useEffect } from "react";
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Space,
  Table,
  Modal,
  Select,
  Typography,
  Popconfirm,
  Tag,
  Cascader,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  ApiOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const { TextArea } = Input;
const { Title, Text } = Typography;

// 供应商配置（与 Settings 页面保持一致）
const PROVIDER_PRESETS = [
  { name: "bigmodel", displayName: "智谱 BigModel", baseUrl: "https://open.bigmodel.cn/api/paas/v4" },
  { name: "qwen", displayName: "阿里通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  { name: "modelscope", displayName: "阿里云魔搭社区", baseUrl: "https://api-inference.modelscope.cn/v1" },
  { name: "custom", displayName: "自建服务", baseUrl: "http://localhost:11434/v1" },
];

interface Engine {
  id: string;
  name: string;
  model: string;
  prompt: string;
  provider: string;  // 供应商名称
  createdAt: string;
  updatedAt: string;
}

interface ProviderModels {
  provider: string;
  providerName: string;
  models: string[];
}

export default function Engines() {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [providerModels, setProviderModels] = useState<ProviderModels[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEngine, setEditingEngine] = useState<Engine | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchEngines();
    fetchProviderModels();
  }, []);

  const fetchEngines = async () => {
    try {
      const res = await fetch("/api/v1/engines");
      if (res.ok) {
        const data = await res.json();
        setEngines(data.data || []);
      }
    } catch (error) {
      console.error("Failed to fetch engines:", error);
      message.error("获取引擎列表失败");
    }
  };

  const fetchProviderModels = async () => {
    try {
      const res = await fetch("/api/v1/settings/llm");
      if (res.ok) {
        const data = await res.json();
        const providerApiKeys = data.providerApiKeys || {};
        const providerModels = data.providerModels || {};
        
        // 构建供应商-模型列表
        const providers: ProviderModels[] = [];
        
        for (const preset of PROVIDER_PRESETS) {
          const hasApiKey = providerApiKeys[preset.name];
          const models = providerModels[preset.name] || [];
          
          // 显示有配置 API Key 的供应商（不管有没有选模型）
          if (hasApiKey) {
            providers.push({
              provider: preset.name,
              providerName: preset.displayName,
              models: models.length > 0 ? models : [],  // 如果没有选模型，显示空列表
            });
          }
        }
        
        setProviderModels(providers);
        
        // 调试信息
        console.log("Provider API Keys:", providerApiKeys);
        console.log("Provider Models:", providerModels);
        console.log("Available Providers:", providers);
      }
    } catch (error) {
      console.error("Failed to fetch provider models:", error);
      message.error("获取供应商模型列表失败");
    }
  };

  const handleCreate = () => {
    setEditingEngine(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Engine) => {
    setEditingEngine(record);
    form.setFieldsValue({
      name: record.name,
      model: [record.provider, record.model],  // Cascader 需要数组格式
      prompt: record.prompt,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/engines/${id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        message.success("删除成功");
        fetchEngines();
      } else {
        message.error("删除失败");
      }
    } catch (error) {
      message.error("删除失败: " + error);
    }
  };

  const handleSave = async (values: any) => {
    setLoading(true);
    try {
      const url = editingEngine
        ? `/api/v1/engines/${editingEngine.id}`
        : "/api/v1/engines";
      const method = editingEngine ? "PUT" : "POST";

      // 从 Cascader 值中解析供应商和模型
      const [provider, model] = values.model;
      const providerPreset = PROVIDER_PRESETS.find(p => p.name === provider);
      
      const saveData = {
        name: values.name,
        model: model,
        prompt: values.prompt,
        provider: provider,
        baseUrl: providerPreset?.baseUrl || "",
      };

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saveData),
      });

      if (res.ok) {
        message.success(editingEngine ? "更新成功" : "创建成功");
        setModalVisible(false);
        fetchEngines();
      } else {
        const error = await res.json();
        message.error(error.message || "保存失败");
      }
    } catch (error) {
      message.error("保存失败: " + error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: "引擎名称",
      dataIndex: "name",
      key: "name",
      render: (text: string) => (
        <Space>
          <RobotOutlined className="text-blue-500" />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: "模型",
      dataIndex: "model",
      key: "model",
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: "供应商",
      dataIndex: "provider",
      key: "provider",
      render: (text: string) => {
        const preset = PROVIDER_PRESETS.find(p => p.name === text);
        return <Tag color="purple">{preset?.displayName || text}</Tag>;
      },
    },
    {
      title: "提示词",
      dataIndex: "prompt",
      key: "prompt",
      ellipsis: true,
      render: (text: string) => (
        <Text type="secondary" className="text-xs">
          {text ? text.substring(0, 50) + "..." : "-"}
        </Text>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      key: "createdAt",
      render: (text: string) => (
        <Text type="secondary" className="text-xs">
          {text ? new Date(text).toLocaleString() : "-"}
        </Text>
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 150,
      render: (_: any, record: Engine) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确认删除"
            description="确定要删除这个执行引擎吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="px-8 py-6">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                <ThunderboltOutlined className="text-white text-lg" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">引擎管理</h1>
                <p className="text-gray-500 text-sm">
                  创建和管理执行引擎，配置模型和提示词
                </p>
              </div>
            </div>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              className="rounded-lg"
            >
              创建引擎
            </Button>
          </div>
        </div>

        <Card className="shadow-sm border-0 rounded-xl">
          <Table
            columns={columns}
            dataSource={engines}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      </div>

      <Modal
        title={editingEngine ? "编辑引擎" : "创建引擎"}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          className="mt-4"
        >
          <Form.Item
            label={
              <Space>
                <RobotOutlined className="text-gray-400" />
                <span>引擎名称</span>
              </Space>
            }
            name="name"
            rules={[{ required: true, message: "请输入引擎名称" }]}
          >
            <Input placeholder="例如：默认视觉引擎" className="rounded-lg" />
          </Form.Item>

          <Form.Item
            label={
              <Space>
                <ApiOutlined className="text-gray-400" />
                <span>选择模型</span>
              </Space>
            }
            name="model"
            rules={[{ required: true, message: "请选择模型" }]}
            help={providerModels.length === 0 ? "请先在系统设置中配置供应商和模型" : ""}
          >
            <Cascader
              placeholder="选择供应商和模型"
              className="w-full"
              options={providerModels.map(pm => ({
                value: pm.provider,
                label: pm.providerName,
                children: pm.models.map(m => ({
                  value: m,
                  label: m,
                })),
              }))}
              disabled={providerModels.length === 0}
            />
          </Form.Item>

          <Form.Item
            label="提示词 (Prompt)"
            name="prompt"
            rules={[{ required: true, message: "请输入提示词" }]}
          >
            <TextArea
              rows={10}
              placeholder="输入系统提示词..."
              className="rounded-lg font-mono text-sm"
            />
          </Form.Item>

          <div className="flex justify-end gap-2 mt-6">
            <Button onClick={() => setModalVisible(false)}>取消</Button>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={loading}
            >
              {editingEngine ? "更新" : "创建"}
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
