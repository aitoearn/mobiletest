import { Input, Button, Space, Tag } from "antd";
import { SendOutlined, StopOutlined } from "@ant-design/icons";

const { TextArea } = Input;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onAbort?: () => void;
  sending: boolean;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  onAbort,
  sending,
  disabled,
}: ChatInputProps) {
  return (
    <div>
      <div className="bg-white rounded-lg border shadow-sm p-2">
        <TextArea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="输入指令 / 使用自然语言描述操作（支持步骤描述）..."
          autoSize={{ minRows: 2, maxRows: 6 }}
          bordered={false}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              if (!sending && value.trim()) {
                onSend();
              }
            }
          }}
          disabled={disabled}
        />
        <div className="flex justify-between items-center mt-2">
          <Space size="small">
            <Tag color="blue" className="m-0">
              自然语言
            </Tag>
            <Tag color="green" className="m-0">
              多步骤
            </Tag>
          </Space>
          {sending ? (
            <Button danger icon={<StopOutlined />} onClick={onAbort}>
              停止
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={onSend}
              disabled={!value.trim() || disabled}
            >
              发送
            </Button>
          )}
        </div>
      </div>
      <div className="text-xs text-gray-400 mt-2 text-center">
        按 Enter 发送，Shift+Enter 换行
      </div>
    </div>
  );
}
