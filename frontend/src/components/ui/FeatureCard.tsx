import { Card, Tag } from "antd";
import type { ReactNode } from "react";

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  color?: string;
  badge?: string;
  badgeColor?: string;
}

export default function FeatureCard({
  icon,
  title,
  description,
  color = "#1890ff",
  badge,
  badgeColor,
}: FeatureCardProps) {
  const colorMap: Record<string, string> = {
    "accent-hot": "#ff4d4f",
    "accent-new": "#52c41a",
    "accent-secondary": "#1890ff",
  };

  const actualColor = badgeColor ? colorMap[badgeColor] || color : color;

  return (
    <Card
      hoverable
      style={{
        height: "100%",
        border: "1px solid #f0f0f0",
        borderRadius: "12px",
      }}
      styles={{ body: { padding: "24px" } }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: `${actualColor}15`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: actualColor,
              fontSize: "24px",
            }}
          >
            {icon}
          </div>
          {badge && (
            <Tag
              color={actualColor}
              style={{
                margin: 0,
                fontWeight: 500,
              }}
            >
              {badge}
            </Tag>
          )}
        </div>
        <div>
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px", fontWeight: 600 }}>
            {title}
          </h3>
          <p style={{ margin: 0, color: "#666", fontSize: "14px" }}>
            {description}
          </p>
        </div>
      </div>
    </Card>
  );
}
