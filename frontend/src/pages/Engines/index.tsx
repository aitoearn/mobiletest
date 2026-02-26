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
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  ApiOutlined,
  KeyOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface Engine {
  id: string;
  name: string;
  model: string;
  prompt: string;
  baseUrl: string;
  apiKey: string;
  createdAt: string;
  updatedAt: string;
}

interface ModelOption {
  value: string;
  label: string;
  baseUrl: string;
}

export default function Engines() {
  const [engines, setEngines] = useState<Engine[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEngine, setEditingEngine] = useState<Engine | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchEngines();
    fetchModels();
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

  const fetchModels = async () => {
    try {
      const res = await fetch("/api/v1/engines/models");
      if (res.ok) {
        const data = await res.json();
        setModels(data.data || []);
      }
    } catch (error) {
      console.error("Failed to fetch models:", error);
      // 使用默认模型列表
      setModels([
        { value: "autoglm-phone", label: "AutoGLM Phone", baseUrl: "" },
        { value: "gpt-4o", label: "GPT-4o", baseUrl: "" },
        { value: "gpt-4o-mini", label: "GPT-4o Mini", baseUrl: "" },
        { value: "glm-4-plus", label: "GLM-4 Plus", baseUrl: "" },
        { value: "qwen-max", label: "Qwen Max", baseUrl: "" },
        { value: "qwen-vl-max", label: "Qwen VL Max", baseUrl: "" },
      ]);
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
      model: record.model,
      prompt: record.prompt,
      baseUrl: record.baseUrl,
      apiKey: record.apiKey,
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

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
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

  const handleModelChange = (value: string) => {
    const selectedModel = models.find((m) => m.value === value);
    if (selectedModel && selectedModel.baseUrl) {
      form.setFieldsValue({ baseUrl: selectedModel.baseUrl });
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
      title: "Base URL",
      dataIndex: "baseUrl",
      key: "baseUrl",
      ellipsis: true,
      render: (text: string) => (
        <Text type="secondary" className="text-xs">
          {text || "-"}
        </Text>
      ),
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
          >
            <Select
              placeholder="选择模型"
              className="rounded-lg"
              onChange={handleModelChange}
            >
              {models.map((model) => (
                <Option key={model.value} value={model.value}>
                  {model.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label={
              <Space>
                <ApiOutlined className="text-gray-400" />
                <span>Base URL</span>
              </Space>
            }
            name="baseUrl"
          >
            <Input
              placeholder="https://api.openai.com/v1"
              className="rounded-lg"
            />
          </Form.Item>

          <Form.Item
            label={
              <Space>
                <KeyOutlined className="text-gray-400" />
                <span>API Key</span>
              </Space>
            }
            name="apiKey"
          >
            <Input.Password
              placeholder="sk-..."
              className="rounded-lg"
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
