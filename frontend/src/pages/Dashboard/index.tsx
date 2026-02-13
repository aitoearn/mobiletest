import { Card, Button, Space, Tag, Row, Col } from 'antd'
import {
  PlayCircleOutlined,
  RocketOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  MobileOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import FeatureCard from '@/components/ui/FeatureCard'

export default function Dashboard() {
  const navigate = useNavigate()
  const features = [
    {
      icon: <MobileOutlined />,
      title: '真机测试',
      description: '实时设备调试 AI 交互',
      badge: 'HOT',
      badgeColor: 'accent-hot',
    },
    {
      icon: <DatabaseOutlined />,
      title: '任务模板',
      description: '配置管理自动化任务模板',
    },
    {
      icon: <HistoryOutlined />,
      title: '执行记录',
      description: '查看任务执行历史与状态',
      badge: 'NEW',
      badgeColor: 'accent-new',
    },
  ]

  return (
    <div>
      <Card
        className="bg-background-primary border-0 shadow-sm mb-6"
        styles={{ body: { padding: '32px' } }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Tag color="accent-secondary" className="font-medium">
            <RocketOutlined className="mr-1" />
            AI POWERED
          </Tag>
        </div>
        
        <h1 className="text-3xl font-display font-bold text-text-primary mb-2">
          UI Genie
        </h1>
        
        <h2 className="text-xl text-text-secondary mb-4">
          智能UI执行精灵
        </h2>
        
        <p className="text-text-secondary mb-6 max-w-2xl">
          基于多模态大模型驱动的移动UI自动化平台，让驱动设备变得更智能、更简单、更高效。
          通过自然语言驱动设备，自动生成执行指令，深度学习端知识。
        </p>
        
        <Space>
          <Button 
            type="primary" 
            size="large"
            icon={<PlayCircleOutlined />}
            className="bg-accent-primary hover:bg-accent-primary/90 text-white font-medium"
            onClick={() => navigate('/devices')}
          >
            开始测试
          </Button>
          <Button 
            type="default" 
            size="large"
            className="border border-gray-300 text-text-primary"
          >
            管理助手
          </Button>
        </Space>
      </Card>

      <div className="mb-6">
        <h3 className="text-xl font-semibold text-text-primary mb-4">
          核心功能
        </h3>
        
        <Row gutter={[16, 16]}>
          {features.map((feature, index) => (
            <Col xs={24} sm={12} md={8} key={index}>
              <FeatureCard
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                badge={feature.badge}
                badgeColor={feature.badgeColor}
              />
            </Col>
          ))}
        </Row>
      </div>
    </div>
  )
}
