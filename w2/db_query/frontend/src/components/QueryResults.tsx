import { Table, Typography, Empty, Tag, Space } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { QueryResult } from "../types";
import { ExportButtons } from "./ExportButtons";

const { Text } = Typography;

interface QueryResultsProps {
  result: QueryResult | null;
  loading?: boolean;
}

export function QueryResults({ result, loading }: QueryResultsProps) {
  if (!result && !loading) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="Run a query to see results"
      />
    );
  }

  if (!result) {
    return null;
  }

  // Build columns from result
  const columns: ColumnsType<Record<string, unknown>> = result.columns.map(
    (col) => ({
      title: col,
      dataIndex: col,
      key: col,
      ellipsis: true,
      render: (value: unknown) => {
        if (value === null) {
          return <Text type="secondary" italic>NULL</Text>;
        }
        if (typeof value === "boolean") {
          return <Tag color={value ? "green" : "red"}>{String(value)}</Tag>;
        }
        if (typeof value === "object") {
          return (
            <Text code style={{ fontSize: 11 }}>
              {JSON.stringify(value)}
            </Text>
          );
        }
        return String(value);
      },
    })
  );

  return (
    <div>
      <Space
        style={{
          marginBottom: 8,
          width: "100%",
          justifyContent: "space-between",
        }}
        align="center"
      >
        <Space>
          <Text type="secondary">
            {result.rowCount} row{result.rowCount !== 1 ? "s" : ""}
          </Text>
          <Text type="secondary">|</Text>
          <Text type="secondary">{result.executionTimeMs.toFixed(2)} ms</Text>
        </Space>
        <ExportButtons result={result} disabled={loading} />
      </Space>
      <Table
        loading={loading}
        columns={columns}
        dataSource={result.rows.map((row, idx) => ({ ...row, _key: idx }))}
        rowKey="_key"
        size="small"
        scroll={{ x: "max-content", y: 400 }}
        pagination={{
          defaultPageSize: 50,
          showSizeChanger: true,
          pageSizeOptions: ["10", "25", "50", "100"],
          showTotal: (total) => `Total ${total} rows`,
        }}
        bordered
      />
    </div>
  );
}
