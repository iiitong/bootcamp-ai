import { Button, Space, Tooltip } from "antd";
import { FileExcelOutlined, FileTextOutlined } from "@ant-design/icons";
import { exportToCSV, exportToJSON } from "../utils/export";
import type { QueryResult } from "../types";

interface ExportButtonsProps {
  result: QueryResult | null;
  disabled?: boolean;
}

/**
 * Export buttons for downloading query results as CSV or JSON
 * - Disabled when no results or empty results
 * - CSV includes UTF-8 BOM for Excel compatibility
 */
export function ExportButtons({ result, disabled }: ExportButtonsProps) {
  // Don't render if no result or empty result
  if (!result || result.rowCount === 0) {
    return null;
  }

  const handleExportCSV = () => {
    exportToCSV(result.columns, result.rows);
  };

  const handleExportJSON = () => {
    exportToJSON(result.rows);
  };

  return (
    <Space>
      <Tooltip title="Export as CSV (Excel compatible)">
        <Button
          icon={<FileExcelOutlined />}
          onClick={handleExportCSV}
          disabled={disabled}
          size="small"
        >
          Export CSV
        </Button>
      </Tooltip>
      <Tooltip title="Export as JSON">
        <Button
          icon={<FileTextOutlined />}
          onClick={handleExportJSON}
          disabled={disabled}
          size="small"
        >
          Export JSON
        </Button>
      </Tooltip>
    </Space>
  );
}
