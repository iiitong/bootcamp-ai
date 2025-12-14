import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useList, useNotification } from "@refinedev/core";
import { Card, Select, Button, Space, Typography, Collapse } from "antd";
import {
  PlayCircleOutlined,
  DatabaseOutlined,
  ClearOutlined,
} from "@ant-design/icons";

import { SqlEditor } from "../../components/SqlEditor";
import { QueryResults } from "../../components/QueryResults";
import { NaturalLanguageInput } from "../../components/NaturalLanguageInput";
import { handleApiError } from "../../utils/error";
import type { DatabaseInfo, QueryResult, NaturalLanguageQueryResult } from "../../types";

const { Title, Text } = Typography;

const API_URL = "http://localhost:8000/api/v1";

export function QueryPage() {
  const { dbName: urlDbName } = useParams<{ dbName?: string }>();
  const navigate = useNavigate();
  const { open: notify } = useNotification();

  const [selectedDb, setSelectedDb] = useState<string | undefined>(urlDbName);
  const [sql, setSql] = useState("SELECT version()");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [executing, setExecuting] = useState(false);
  const [generating, setGenerating] = useState(false);

  const { data: dbsData } = useList<DatabaseInfo>({
    resource: "dbs",
  });

  const databases = dbsData?.data ?? [];

  // Sync URL param with state
  useEffect(() => {
    if (urlDbName && urlDbName !== selectedDb) {
      setSelectedDb(urlDbName);
    }
  }, [urlDbName, selectedDb]);

  const handleDbChange = (value: string) => {
    setSelectedDb(value);
    navigate(`/query/${value}`, { replace: true });
  };

  const executeQuery = async () => {
    if (!selectedDb || !sql.trim()) return;

    setExecuting(true);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/dbs/${selectedDb}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: sql.trim() }),
      });

      if (!response.ok) {
        await handleApiError(response, "Query failed");
      }

      const data: QueryResult = await response.json();
      setResult(data);

      notify?.({
        type: "success",
        message: "Query executed",
        description: `${data.rowCount} rows in ${data.executionTimeMs.toFixed(2)}ms`,
      });
    } catch (error) {
      notify?.({
        type: "error",
        message: "Query failed",
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setExecuting(false);
    }
  };

  const generateSql = async (prompt: string) => {
    if (!selectedDb) return;

    setGenerating(true);

    try {
      const response = await fetch(
        `${API_URL}/dbs/${selectedDb}/query/natural`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt }),
        }
      );

      if (!response.ok) {
        await handleApiError(response, "Failed to generate SQL");
      }

      const data: NaturalLanguageQueryResult = await response.json();
      setSql(data.generatedSql);

      notify?.({
        type: "success",
        message: "SQL generated",
        description: "Review the generated query and click Execute",
      });
    } catch (error) {
      notify?.({
        type: "error",
        message: "Failed to generate SQL",
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            <DatabaseOutlined /> SQL Query
          </Title>

          <Space>
            <Text>Database:</Text>
            <Select
              value={selectedDb}
              onChange={handleDbChange}
              placeholder="Select a database"
              style={{ width: 200 }}
              options={databases.map((db) => ({
                label: db.name,
                value: db.name,
              }))}
            />
          </Space>
        </div>

        <Collapse
          items={[
            {
              key: "natural",
              label: "Natural Language Query (AI)",
              children: (
                <NaturalLanguageInput
                  onGenerate={generateSql}
                  loading={generating}
                  disabled={!selectedDb}
                />
              ),
            },
          ]}
          defaultActiveKey={[]}
        />

        <Card
          title="SQL Editor"
          extra={
            <Space>
              <Button
                icon={<ClearOutlined />}
                onClick={() => {
                  setSql("");
                  setResult(null);
                }}
              >
                Clear
              </Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={executeQuery}
                loading={executing}
                disabled={!selectedDb || !sql.trim()}
              >
                Execute
              </Button>
            </Space>
          }
        >
          <SqlEditor
            value={sql}
            onChange={setSql}
            height="200px"
            readOnly={executing}
          />
          <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
            Only SELECT queries are allowed. LIMIT 1000 is auto-added if missing.
          </Text>
        </Card>

        <Card title="Results">
          <QueryResults result={result} loading={executing} />
        </Card>
      </Space>
    </div>
  );
}
