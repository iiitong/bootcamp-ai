import { List, Card, Button, Space, Typography, Popconfirm, Empty } from "antd";
import { DeleteOutlined, DatabaseOutlined, EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { DatabaseInfo } from "../types";

const { Text, Paragraph } = Typography;

interface DatabaseListProps {
  databases: DatabaseInfo[];
  loading?: boolean;
  onDelete: (name: string) => void;
}

export function DatabaseList({ databases, loading, onDelete }: DatabaseListProps) {
  const navigate = useNavigate();

  if (!loading && databases.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="No database connections yet"
      />
    );
  }

  return (
    <List
      loading={loading}
      grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3, xxl: 4 }}
      dataSource={databases}
      renderItem={(db) => (
        <List.Item>
          <Card
            hoverable
            actions={[
              <Button
                key="view"
                type="text"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/databases/${db.name}`)}
              >
                View
              </Button>,
              <Button
                key="query"
                type="text"
                icon={<DatabaseOutlined />}
                onClick={() => navigate(`/query/${db.name}`)}
              >
                Query
              </Button>,
              <Popconfirm
                key="delete"
                title="Delete this connection?"
                description="This will remove the connection and cached metadata."
                onConfirm={() => onDelete(db.name)}
                okText="Delete"
                okType="danger"
              >
                <Button type="text" danger icon={<DeleteOutlined />}>
                  Delete
                </Button>
              </Popconfirm>,
            ]}
          >
            <Card.Meta
              avatar={<DatabaseOutlined style={{ fontSize: 24, color: "#1890ff" }} />}
              title={db.name}
              description={
                <Space direction="vertical" size={0}>
                  <Paragraph
                    ellipsis={{ rows: 1 }}
                    style={{ marginBottom: 4 }}
                    copyable={{ text: db.url }}
                  >
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {db.url}
                    </Text>
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Updated: {new Date(db.updatedAt).toLocaleString()}
                  </Text>
                </Space>
              }
            />
          </Card>
        </List.Item>
      )}
    />
  );
}
