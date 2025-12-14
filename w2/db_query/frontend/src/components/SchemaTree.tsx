import { Tree, Typography, Tag, Empty } from "antd";
import {
  TableOutlined,
  EyeOutlined,
  KeyOutlined,
  LinkOutlined,
} from "@ant-design/icons";
import type { DataNode } from "antd/es/tree";
import type { TableInfo, ColumnInfo } from "../types";

const { Text } = Typography;

interface SchemaTreeProps {
  tables: TableInfo[];
  views: TableInfo[];
  onSelect?: (schemaName: string, tableName: string) => void;
}

function buildTreeData(tables: TableInfo[], views: TableInfo[]): DataNode[] {
  const treeData: DataNode[] = [];

  // Group by schema
  const schemas = new Map<string, { tables: TableInfo[]; views: TableInfo[] }>();

  for (const table of tables) {
    const key = table.schemaName;
    if (!schemas.has(key)) {
      schemas.set(key, { tables: [], views: [] });
    }
    schemas.get(key)!.tables.push(table);
  }

  for (const view of views) {
    const key = view.schemaName;
    if (!schemas.has(key)) {
      schemas.set(key, { tables: [], views: [] });
    }
    schemas.get(key)!.views.push(view);
  }

  for (const [schemaName, { tables: schemaTables, views: schemaViews }] of schemas) {
    const schemaNode: DataNode = {
      title: <Text strong>{schemaName}</Text>,
      key: schemaName,
      children: [],
    };

    // Add tables
    if (schemaTables.length > 0) {
      const tablesNode: DataNode = {
        title: (
          <span>
            <TableOutlined /> Tables ({schemaTables.length})
          </span>
        ),
        key: `${schemaName}-tables`,
        children: schemaTables.map((table) => buildTableNode(schemaName, table)),
      };
      schemaNode.children!.push(tablesNode);
    }

    // Add views
    if (schemaViews.length > 0) {
      const viewsNode: DataNode = {
        title: (
          <span>
            <EyeOutlined /> Views ({schemaViews.length})
          </span>
        ),
        key: `${schemaName}-views`,
        children: schemaViews.map((view) => buildTableNode(schemaName, view)),
      };
      schemaNode.children!.push(viewsNode);
    }

    treeData.push(schemaNode);
  }

  return treeData;
}

function buildTableNode(schemaName: string, table: TableInfo): DataNode {
  return {
    title: (
      <span>
        {table.type === "VIEW" ? <EyeOutlined /> : <TableOutlined />}{" "}
        {table.name}
        <Text type="secondary" style={{ marginLeft: 8, fontSize: 11 }}>
          ({table.columns.length} columns)
        </Text>
      </span>
    ),
    key: `${schemaName}.${table.name}`,
    children: table.columns.map((col) => buildColumnNode(schemaName, table.name, col)),
  };
}

function buildColumnNode(
  schemaName: string,
  tableName: string,
  column: ColumnInfo
): DataNode {
  return {
    title: (
      <span>
        {column.isPrimaryKey && (
          <KeyOutlined style={{ color: "#faad14", marginRight: 4 }} />
        )}
        {column.isForeignKey && (
          <LinkOutlined style={{ color: "#1890ff", marginRight: 4 }} />
        )}
        <Text code>{column.name}</Text>
        <Tag
          color={column.nullable ? "default" : "blue"}
          style={{ marginLeft: 8, fontSize: 10 }}
        >
          {column.dataType}
        </Tag>
        {!column.nullable && (
          <Tag color="red" style={{ fontSize: 10 }}>
            NOT NULL
          </Tag>
        )}
      </span>
    ),
    key: `${schemaName}.${tableName}.${column.name}`,
    isLeaf: true,
  };
}

export function SchemaTree({ tables, views, onSelect }: SchemaTreeProps) {
  const treeData = buildTreeData(tables, views);

  if (treeData.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="No tables or views found"
      />
    );
  }

  return (
    <Tree
      showLine
      defaultExpandAll
      treeData={treeData}
      onSelect={(selectedKeys) => {
        if (onSelect && selectedKeys.length > 0) {
          const key = selectedKeys[0] as string;
          const parts = key.split(".");
          if (parts.length >= 2) {
            onSelect(parts[0], parts[1]);
          }
        }
      }}
      style={{ padding: 8 }}
    />
  );
}
