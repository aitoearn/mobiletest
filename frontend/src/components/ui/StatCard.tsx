import type { ReactNode } from 'react'
import { Card, Statistic } from 'antd'

interface StatCardProps {
  title: string
  value: number
  suffix?: string
  prefix?: ReactNode
  color?: string
}

export default function StatCard({
  title,
  value,
  suffix,
  prefix,
  color = '#00FFD1',
}: StatCardProps) {
  return (
    <Card
      className="bg-background-secondary border-gray-700"
      styles={{ body: { padding: '20px' } }}
    >
      <Statistic
        title={<span className="text-text-secondary">{title}</span>}
        value={value}
        suffix={suffix}
        prefix={prefix}
        styles={{ content: { color, fontSize: '32px', fontWeight: 'bold' } }}
      />
    </Card>
  )
}
