import { useState, useEffect } from "react";
import {
  Card,
  Button,
  Tag,
  Space,
  Typography,
  message,
  Spin,
  Empty,
  Input,
  Select,
  Switch,
  Row,
  Col,
} from "antd";
import {
  ReloadOutlined,
  MobileOutlined,
  SearchOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Text } = Typography;

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
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

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
    let interval: ReturnType<typeof setInterval> | null = null;
    if (autoRefresh) {
      interval = setInterval(() => fetchDevices(false), 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const handleRefresh = () => {
    fetchDevices(true);
  };

  const handleStartTest = (device: Device) => {
    // TODO: 跳转到对话测试界面
    message.info(`准备开始测试设备: ${device.model || device.device_id}`);
    navigate(`/test/${device.device_id}`);
  };

  const filteredDevices = devices.filter((device) => {
    const matchSearch =
      searchText === "" ||
      device.device_id.toLowerCase().includes(searchText.toLowerCase()) ||
      device.model?.toLowerCase().includes(searchText.toLowerCase()) ||
      device.brand?.toLowerCase().includes(searchText.toLowerCase());

    const matchStatus =
      statusFilter === "all" ||
      (statusFilter === "online" && device.connected) ||
      (statusFilter === "offline" && !device.connected);

    return matchSearch && matchStatus;
  });

  return (
    <div>
      {/* 顶部工具栏 */}
      <Card
        className="mb-4"
        styles={{ body: { padding: "16px 24px" } }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space size="middle" wrap>
              <Input
                placeholder="设备 UDID"
                prefix={<SearchOutlined />}
                style={{ width: 200 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                allowClear
              />
              <Select
                style={{ width: 120 }}
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { label: "全部设备", value: "all" },
                  { label: "在线设备", value: "online" },
                  { label: "离线设备", value: "offline" },
                ]}
              />
              <Select
                style={{ width: 120 }}
                defaultValue="all"
                placeholder="设备筛选"
                options={[
                  { label: "全部品牌", value: "all" },
                  { label: "HONOR", value: "honor" },
                  { label: "其他", value: "other" },
                ]}
              />
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Space>
                <Text type="secondary">自动刷新</Text>
                <Switch
                  checked={autoRefresh}
                  onChange={setAutoRefresh}
                />
              </Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 设备列表 */}
      <Spin spinning={loading}>
        {filteredDevices.length === 0 ? (
          <Card>
            <Empty
              description={
                devices.length === 0
                  ? "未检测到设备"
                  : "没有符合条件的设备"
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Text type="secondary">
                请确保设备已通过 USB 连接并开启 USB 调试
              </Text>
            </Empty>
          </Card>
        ) : (
          <Row gutter={[16, 16]}>
            {filteredDevices.map((device) => (
              <Col xs={24} sm={12} lg={8} xl={6} key={device.device_id}>
                <Card
                  className="hover:shadow-lg transition-shadow"
                  styles={{ body: { padding: "20px" } }}
                >
                  {/* 在线状态标签 */}
                  <div className="absolute top-3 right-3">
                    <Tag color={device.connected ? "success" : "default"}>
                      {device.connected ? "在线" : "离线"}
                    </Tag>
                  </div>

                  {/* 设备图标 */}
                  <div className="flex justify-center mb-4">
                    <div className="w-16 h-16 bg-green-50 rounded-lg flex items-center justify-center">
                      <MobileOutlined
                        style={{ fontSize: 32, color: "#52c41a" }}
                      />
                    </div>
                  </div>

                  {/* 设备型号 */}
                  <div className="text-center mb-4">
                    <Text strong className="text-base">
                      {device.model || "未知型号"}
                    </Text>
                  </div>

                  {/* 设备信息 */}
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <Text type="secondary">序列号：</Text>
                      <Text code className="text-xs">
                        {device.device_id.length > 12
                          ? `${device.device_id.substring(0, 12)}...`
                          : device.device_id}
                      </Text>
                    </div>
                    <div className="flex justify-between text-sm">
                      <Text type="secondary">品牌：</Text>
                      <Text>{device.brand || "-"}</Text>
                    </div>
                    <div className="flex justify-between text-sm">
                      <Text type="secondary">系统：</Text>
                      <Text>
                        {device.android_version
                          ? `Android ${device.android_version}`
                          : "-"}
                      </Text>
                    </div>
                    <div className="flex justify-between text-sm">
                      <Text type="secondary">分辨率：</Text>
                      <Text>{device.screen_size || "-"}</Text>
                    </div>
                  </div>

                  {/* 操作按钮 */}
                  <Button
                    block
                    type="primary"
                    danger
                    icon={<PlayCircleOutlined />}
                    onClick={() => handleStartTest(device)}
                    disabled={!device.connected}
                  >
                    立即测试
                  </Button>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  );
}
