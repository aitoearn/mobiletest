import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  message,
  Spin,
  Empty,
} from "antd";
import {
  ReloadOutlined,
  MobileOutlined,
  AndroidOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

interface Device {
  device_id: string;
  status: string;
  model: string | null;
  brand: string | null;
  android_version: string | null;
  screen_size: string | null;
  screen_density: string | null;
  battery_level: number | null;
  connected: boolean;
}

export default function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);

  const fetchDevices = async (showLoading: boolean = true) => {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const response = await fetch("/api/v1/devices/scan");
      const data = await response.json();
      setDevices(data.devices || []);
    } catch (error) {
      if (showLoading) {
        message.error("获取设备列表失败");
      }
      console.error(error);
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchDevices(true);
    const interval = setInterval(() => fetchDevices(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    fetchDevices(true);
  };

  const handleConnect = async (deviceId: string) => {
    setConnecting(deviceId);
    try {
      const response = await fetch(
        `/api/v1/devices/${deviceId}/connect`,
        { method: "POST" }
      );
      if (response.ok) {
        message.success("设备已连接");
        fetchDevices(false);
      } else {
        message.error("连接失败");
      }
    } catch (error) {
      message.error("连接失败");
    } finally {
      setConnecting(null);
    }
  };

  const columns = [
    {
      title: "设备 ID",
      dataIndex: "device_id",
      key: "device_id",
      render: (text: string) => (
        <Space>
          <AndroidOutlined style={{ color: "#52c41a" }} />
          <Text code>{text}</Text>
        </Space>
      ),
    },
    {
      title: "型号",
      dataIndex: "model",
      key: "model",
      render: (text: string) => text || "-",
    },
    {
      title: "品牌",
      dataIndex: "brand",
      key: "brand",
      render: (text: string) => text || "-",
    },
    {
      title: "Android 版本",
      dataIndex: "android_version",
      key: "android_version",
      render: (text: string) =>
        text ? <Tag color="blue">Android {text}</Tag> : "-",
    },
    {
      title: "屏幕尺寸",
      dataIndex: "screen_size",
      key: "screen_size",
      render: (text: string) => text || "-",
    },
    {
      title: "电量",
      dataIndex: "battery_level",
      key: "battery_level",
      render: (level: number) =>
        level !== null ? (
          <Tag color={level > 20 ? "green" : "red"}>{level}%</Tag>
        ) : (
          "-"
        ),
    },
    {
      title: "状态",
      dataIndex: "connected",
      key: "connected",
      render: (connected: boolean) =>
        connected ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            已连接
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="default">
            未连接
          </Tag>
        ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: Device) => (
        <Space>
          <Button
            type="primary"
            size="small"
            onClick={() => handleConnect(record.device_id)}
            loading={connecting === record.device_id}
            disabled={record.connected}
          >
            {record.connected ? "已连接" : "连接"}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        style={{ marginBottom: 16 }}
        styles={{ body: { padding: "16px 24px" } }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <MobileOutlined style={{ marginRight: 8 }} />
              设备管理
            </Title>
            <Text type="secondary">
              检测并管理已连接的 Android 设备
            </Text>
          </div>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        </div>
      </Card>

      <Card>
        <Spin spinning={loading}>
          {devices.length === 0 ? (
            <Empty
              description="未检测到设备"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Text type="secondary">
                请确保设备已通过 USB 连接并开启 USB 调试
              </Text>
            </Empty>
          ) : (
            <Table
              columns={columns}
              dataSource={devices}
              rowKey="device_id"
              pagination={false}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
}
