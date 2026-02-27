import { useState, useEffect } from 'react'
import { Card, Table, Tag, Space, Button, Popconfirm, message, Modal, Select } from 'antd'
import { DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

interface TestCase {
  id: number
  name: string
  description: string | null
  status: 'draft' | 'published' | 'archived'
  tags: string[]
  creator_id: number
  created_at: string
  updated_at: string
}

interface Device {
  device_id: string
  model?: string
  brand?: string
  status: string
  connected: boolean
}

export default function Cases() {
  const [cases, setCases] = useState<TestCase[]>([])
  const [loading, setLoading] = useState(false)
  const [devices, setDevices] = useState<Device[]>([])
  const [executeModalOpen, setExecuteModalOpen] = useState(false)
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [executing, setExecuting] = useState(false)

  const fetchCases = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/cases')
      if (res.ok) {
        const data = await res.json()
        setCases(data)
      } else {
        message.error('获取用例列表失败')
      }
    } catch (error) {
      console.error('获取用例列表失败:', error)
      message.error('获取用例列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/cases/${id}`, { method: 'DELETE' })
      if (res.ok) {
        message.success('删除成功')
        fetchCases()
      } else {
        message.error('删除失败')
      }
    } catch (error) {
      console.error('删除用例失败:', error)
      message.error('删除失败')
    }
  }

  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/v1/devices/scan')
      if (res.ok) {
        const data = await res.json()
        setDevices(data.devices || [])
      }
    } catch (error) {
      console.error('获取设备列表失败:', error)
    }
  }

  useEffect(() => {
    fetchCases()
    fetchDevices()
  }, [])

  const handleExecuteClick = (caseId: number) => {
    setSelectedCaseId(caseId)
    setSelectedDeviceId(null)
    setExecuteModalOpen(true)
  }

  const handleExecute = async () => {
    if (!selectedCaseId || !selectedDeviceId) {
      message.warning('请选择设备')
      return
    }

    setExecuting(true)
    try {
      const res = await fetch('/api/v1/executions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_case_id: selectedCaseId,
          device_id: selectedDeviceId,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        message.success('执行创建成功')
        setExecuteModalOpen(false)
        // 跳转到执行详情页或执行列表页
        window.location.href = `/executions/${data.id}`
      } else {
        const error = await res.json()
        message.error(error.detail || '创建执行失败')
      }
    } catch (error) {
      console.error('创建执行失败:', error)
      message.error('创建执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const columns: ColumnsType<TestCase> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
    },
    {
      title: '名称',
      dataIndex: 'name',
      ellipsis: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      render: (desc) => desc || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          draft: { color: 'default', text: '草稿' },
          published: { color: 'success', text: '已发布' },
          archived: { color: 'warning', text: '已归档' },
        }
        const { color, text } = statusMap[status] || { color: 'default', text: status }
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '标签',
      dataIndex: 'tags',
      render: (tags: string[]) => (
        <Space size="small">
          {tags?.map((tag: string) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            title="执行"
            onClick={() => handleExecuteClick(record.id)}
          />
          <Popconfirm
            title="确认删除"
            description="确定要删除这个用例吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              title="删除"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-display mb-6 text-text-primary">用例管理</h1>
      <Card className="bg-background-secondary border-gray-700">
        <Table
          columns={columns}
          dataSource={cases}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="选择执行设备"
        open={executeModalOpen}
        onOk={handleExecute}
        onCancel={() => setExecuteModalOpen(false)}
        confirmLoading={executing}
        okText="执行"
        cancelText="取消"
      >
        <div className="py-4">
          <p className="mb-2">请选择要执行该用例的设备：</p>
          <Select
            placeholder="选择设备"
            style={{ width: '100%' }}
            value={selectedDeviceId}
            onChange={setSelectedDeviceId}
            options={devices.map(d => ({
              value: d.device_id,
              label: `${d.model || d.brand || '未知设备'} (${d.device_id}) - ${d.connected ? '在线' : '离线'}`,
              disabled: !d.connected,
            }))}
          />
        </div>
      </Modal>
    </div>
  )
}
