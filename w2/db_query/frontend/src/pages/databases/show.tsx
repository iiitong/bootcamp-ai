import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useNotification } from "@refinedev/core";
import {
  Button,
  Card,
  Space,
  Spin,
  Typography,
  Breadcrumb,
  Statistic,
  Row,
  Col,
  Flex,
} from "antd";
import {
  ReloadOutlined,
  CodeOutlined,
  TableOutlined,
  EyeOutlined,
  ArrowLeftOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  AppstoreOutlined,
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
      <Spin size="large" tip="Loading metadata...">
        <div style={{ display: "flex", justifyContent: "center", padding: 48, minHeight: 200 }} />
      </Spin>
    );
  }

  if (!metadata) {
    return (
      <div>
        <Breadcrumb
          items={[
            { title: <><DatabaseOutlined /> Databases</>, href: "/databases" },
            { title: "Show" },
          ]}
          style={{ marginBottom: 16 }}
        />
        <Text type="danger">Failed to load database metadata</Text>
      </div>
    );
  }

  const tableCount = metadata.tables.length;
  const viewCount = metadata.views.length;
  const columnCount = [...metadata.tables, ...metadata.views].reduce(
    (sum, t) => sum + t.columns.length,
    0
  );

  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          {
            title: (
              <a onClick={() => navigate("/databases")} style={{ cursor: "pointer" }}>
                <DatabaseOutlined /> Databases
              </a>
            ),
          },
          { title: "Show" },
        ]}
        style={{ marginBottom: 16 }}
      />

      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 16
      }}>
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/databases")}
          />
          <Typography.Title level={4} style={{ margin: 0 }}>
            {metadata.name}
          </Typography.Title>
        </Space>
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
      </div>

      {/* Content */}
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        {/* Connection Info */}
        <Card size="small" variant="outlined">
          <Flex vertical gap={16}>
            {/* Connection URL */}
            <Flex align="center" gap={8}>
              <LinkOutlined style={{ color: "#8c8c8c" }} />
              <Text type="secondary" style={{ flexShrink: 0 }}>Connection:</Text>
              <Text copyable code style={{ fontSize: 12 }}>
                {metadata.url}
              </Text>
            </Flex>

            {/* Statistics Row */}
            <Row gutter={[24, 16]}>
              <Col xs={12} sm={6}>
                <Statistic
                  title={<Text type="secondary"><TableOutlined /> Tables</Text>}
                  value={tableCount}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title={<Text type="secondary"><EyeOutlined /> Views</Text>}
                  value={viewCount}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title={<Text type="secondary"><AppstoreOutlined /> Columns</Text>}
                  value={columnCount}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title={<Text type="secondary"><ClockCircleOutlined /> Cached At</Text>}
                  value={new Date(metadata.cachedAt).toLocaleString()}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
            </Row>
          </Flex>
        </Card>

        <Card
          title="Database Schema"
          variant="outlined"
          styles={{ body: { padding: 0 } }}
        >
          <div style={{ maxHeight: 600, overflow: "auto" }}>
            <SchemaTree
              tables={metadata.tables}
              views={metadata.views}
              onSelect={(schema, table) => {
                // Could navigate to table detail or copy to clipboard
                console.log(`Selected: ${schema}.${table}`);
              }}
            />
          </div>
        </Card>
      </Space>
    </div>
  );
}
