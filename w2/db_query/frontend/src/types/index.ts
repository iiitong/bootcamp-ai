/**
 * TypeScript type definitions for DB Query Tool
 * Matches backend Pydantic models with camelCase JSON output
 */

// Database connection info (list view)
export interface DatabaseInfo {
  name: string;
  url: string;
  createdAt: string;
  updatedAt: string;
}

// Column information
export interface ColumnInfo {
  name: string;
  dataType: string;
  nullable: boolean;
  defaultValue: string | null;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
}

// Table or view information
export interface TableInfo {
  schemaName: string;
  name: string;
  type: "TABLE" | "VIEW";
  columns: ColumnInfo[];
}

// Complete database metadata
export interface DatabaseMetadata {
  name: string;
  url: string;
  tables: TableInfo[];
  views: TableInfo[];
  cachedAt: string;
}

// Request for creating/updating database connection
export interface DatabaseCreateRequest {
  url: string;
}

// SQL query request
export interface QueryRequest {
  sql: string;
}

// Query execution result
export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  executionTimeMs: number;
}

// Natural language query request
export interface NaturalLanguageQueryRequest {
  prompt: string;
}

// Natural language query result
export interface NaturalLanguageQueryResult {
  generatedSql: string;
  result?: QueryResult;
  error?: string;
}

// Error response from API
export interface ErrorResponse {
  detail: string;
  code: string;
}

// Error codes
export type ErrorCode =
  | "CONNECTION_FAILED"
  | "CONNECTION_NOT_FOUND"
  | "INVALID_URL"
  | "INVALID_SQL"
  | "NON_SELECT_QUERY"
  | "QUERY_TIMEOUT"
  | "LLM_ERROR";
