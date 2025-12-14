import { useState } from "react";
import { Input, Button, Space, Typography, Alert } from "antd";
import { RobotOutlined, SendOutlined } from "@ant-design/icons";

const { TextArea } = Input;
const { Text } = Typography;

interface NaturalLanguageInputProps {
  onGenerate: (prompt: string) => Promise<void>;
  loading?: boolean;
  disabled?: boolean;
}

export function NaturalLanguageInput({
  onGenerate,
  loading,
  disabled,
}: NaturalLanguageInputProps) {
  const [prompt, setPrompt] = useState("");

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    await onGenerate(prompt.trim());
  };

  const examples = [
    "Show all tables in the public schema",
    "Count the number of records in each table",
    "Find users who registered in the last 7 days",
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: "100%" }} size="small">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <RobotOutlined style={{ color: "#1890ff" }} />
          <Text strong>Natural Language Query</Text>
        </div>

        <TextArea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what you want to query in natural language..."
          autoSize={{ minRows: 2, maxRows: 4 }}
          disabled={disabled || loading}
          onPressEnter={(e) => {
            if (e.ctrlKey || e.metaKey) {
              handleGenerate();
            }
          }}
        />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Press Ctrl+Enter to generate
          </Text>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleGenerate}
            loading={loading}
            disabled={disabled || !prompt.trim()}
          >
            Generate SQL
          </Button>
        </div>

        {disabled && (
          <Alert
            type="warning"
            message="Select a database first"
            showIcon
            style={{ marginTop: 8 }}
          />
        )}

        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Examples:
          </Text>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
            {examples.map((example) => (
              <Button
                key={example}
                size="small"
                type="dashed"
                onClick={() => setPrompt(example)}
                disabled={disabled || loading}
              >
                {example}
              </Button>
            ))}
          </div>
        </div>
      </Space>
    </div>
  );
}
