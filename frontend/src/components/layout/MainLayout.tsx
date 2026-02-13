import type { ReactNode } from 'react'
import { Layout, Menu, Button, Space } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  MobileOutlined,
  BarChartOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Sider, Content, Header } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/cases', icon: <FileTextOutlined />, label: '用例管理' },
  { key: '/executions', icon: <PlayCircleOutlined />, label: '执行中心' },
  { key: '/devices', icon: <MobileOutlined />, label: '真机调试' },
  { key: '/reports', icon: <BarChartOutlined />, label: '测试报告' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
]

interface MainLayoutProps {
  children: ReactNode
}

export default function MainLayout({ children }: MainLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Layout className="min-h-screen">
      <Header
        style={{
          background: '#FFFFFF',
          borderBottom: '1px solid #E2E8F0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
        }}
      >
        <div className="flex items-center gap-4">
          <span className="text-xl font-display font-bold text-accent-primary">MOBILE TEST AI</span>
        </div>
        <div>
          <Space>
            <Button type="text" className="text-text-secondary">
              帮助
            </Button>
            <Button type="text" className="text-text-secondary">
              文档
            </Button>
            <Button type="text" className="text-text-secondary">
              关于
            </Button>
          </Space>
        </div>
      </Header>
      
      <Layout>
        <Sider
          theme="light"
          style={{ 
            background: '#FFFFFF',
            borderRight: '1px solid #E2E8F0',
          }}
          width={220}
        >
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ 
              background: 'transparent',
              border: 'none',
              marginTop: 24,
            }}
            className="text-text-primary"
          />
        </Sider>
        <Content className="p-6 bg-background-secondary">
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}
