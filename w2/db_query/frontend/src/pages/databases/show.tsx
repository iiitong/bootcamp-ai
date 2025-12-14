import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useNotification } from "@refinedev/core";
import { Show } from "@refinedev/antd";
import {
  Button,
  Card,
  Descriptions,
  Space,
  Spin,
  Typography,
  Tabs,
} from "antd";
import {
  ReloadOutlined,
  CodeOutlined,
  TableOutlined,
  EyeOutlined,
} from "@ant-design/icons";

import { SchemaTree } from "../../components/SchemaTree";
import { handleApiError } from "../../utils/error";
import type { DatabaseMetadata } from "../../types";

const { Text } = Typography;

const API_URL = "http://localhost:8000/api/v1";

export function DatabaseShow() {
  const { id: dbName } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { open: notify } = useNotification();

  const [metadata, setMetadata] = useState<DatabaseMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetadata = useCallback(async (refresh: boolean) => {
    if (!dbName) return;

    if (refresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const url = `${API_URL}/dbs/${dbName}${refresh ? "?refresh=true" : ""}`;
      const response = await fetch(url);

      if (!response.ok) {
        await handleApiError(response, "Failed to fetch metadata");
      }

      const data: DatabaseMetadata = await response.json();
      setMetadata(data);

      if (refresh) {
        notify?.({
          type: "success",
          message: "Metadata refreshed",
          description: `Found ${data.tables.length} tables and ${data.views.length} views`,
        });
      }
    } catch (error) {
      notify?.({
        type: "error",
        message: "Failed to fetch metadata",
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [dbName, notify]);

  // Fetch metadata on mount
  useEffect(() => {
    fetchMetadata(false);
  }, [fetchMetadata]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
        <Spin size="large" tip="Loading metadata..." />
      </div>
    );
  }

  if (!metadata) {
    return (
      <Show title={dbName}>
        <Text type="danger">Failed to load database metadata</Text>
      </Show>
    );
  }

  const tableCount = metadata.tables.length;
  const viewCount = metadata.views.length;
  const columnCount = [...metadata.tables, ...metadata.views].reduce(
    (sum, t) => sum + t.columns.length,
    0
  );

  return (
    <Show
      title={metadata.name}
      headerButtons={
        <Space>
          <Button
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={() => fetchMetadata(true)}
            loading={refreshing}
          >
            Refresh Metadata
          </Button>
          <Button
            type="primary"
            icon={<CodeOutlined />}
            onClick={() => navigate(`/query/${dbName}`)}
          >
            Query
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Card size="small">
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
            <Descriptions.Item label="Connection URL">
              <Text copyable code style={{ fontSize: 12 }}>
                {metadata.url}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Cached At">
              {new Date(metadata.cachedAt).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Statistics">
              <Space>
                <Text>
                  <TableOutlined /> {tableCount} tables
                </Text>
                <Text>
                  <EyeOutlined /> {viewCount} views
                </Text>
                <Text>{columnCount} columns</Text>
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          title="Database Schema"
          styles={{ body: { padding: 0, maxHeight: 600, overflow: "auto" } }}
        >
          <Tabs
            defaultActiveKey="tree"
            items={[
              {
                key: "tree",
                label: "Tree View",
                children: (
                  <SchemaTree
                    tables={metadata.tables}
                    views={metadata.views}
                    onSelect={(schema, table) => {
                      // Could navigate to table detail or copy to clipboard
                      console.log(`Selected: ${schema}.${table}`);
                    }}
                  />
                ),
              },
            ]}
          />
        </Card>
      </Space>
    </Show>
  );
}
