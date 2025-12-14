/**
 * Export utilities for query results
 * Supports CSV and JSON export with proper encoding for international characters
 */

/**
 * Generate a timestamp-based filename
 * Format: query_result_YYYYMMDD_HHMMSS
 */
function generateFilename(extension: string): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  const timestamp = `${year}${month}${day}_${hours}${minutes}${seconds}`;
  return `query_result_${timestamp}.${extension}`;
}

/**
 * Escape a CSV field value
 * - Wraps in quotes if contains comma, newline, or quote
 * - Escapes internal quotes by doubling them
 */
function escapeCSVField(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  const str = String(value);

  // Check if escaping is needed
  if (str.includes(",") || str.includes("\n") || str.includes('"')) {
    // Escape quotes by doubling them and wrap in quotes
    return `"${str.replace(/"/g, '""')}"`;
  }

  return str;
}

/**
 * Trigger a file download using Blob and URL.createObjectURL
 */
function downloadBlob(
  content: string,
  filename: string,
  mimeType: string
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";

  document.body.appendChild(link);
  link.click();

  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export query results to CSV format
 * - Uses UTF-8 with BOM for Excel compatibility with Chinese characters
 * - Properly escapes special characters (comma, newline, quotes)
 *
 * @param columns - Array of column names
 * @param rows - Array of row data objects
 * @param filename - Optional custom filename (without extension)
 */
export function exportToCSV(
  columns: string[],
  rows: Record<string, unknown>[],
  filename?: string
): void {
  // UTF-8 BOM for Excel compatibility
  const BOM = "\uFEFF";

  // Build header line
  const headerLine = columns.map(escapeCSVField).join(",");

  // Build data lines
  const dataLines = rows.map((row) =>
    columns.map((col) => escapeCSVField(row[col])).join(",")
  );

  // Combine with newlines
  const csvContent = BOM + [headerLine, ...dataLines].join("\n");

  // Generate filename if not provided
  const finalFilename = filename
    ? `${filename}.csv`
    : generateFilename("csv");

  // Trigger download
  downloadBlob(csvContent, finalFilename, "text/csv;charset=utf-8");
}

/**
 * Export query results to JSON format
 * - Uses simple array format [{col1: val1, col2: val2}, ...]
 * - Pretty-printed for readability
 *
 * @param rows - Array of row data objects
 * @param filename - Optional custom filename (without extension)
 */
export function exportToJSON(
  rows: Record<string, unknown>[],
  filename?: string
): void {
  // Format with 2-space indentation for readability
  const jsonContent = JSON.stringify(rows, null, 2);

  // Generate filename if not provided
  const finalFilename = filename
    ? `${filename}.json`
    : generateFilename("json");

  // Trigger download
  downloadBlob(jsonContent, finalFilename, "application/json;charset=utf-8");
}

// Re-export for testing
export { escapeCSVField, generateFilename, downloadBlob };
