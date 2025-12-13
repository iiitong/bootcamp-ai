# Data Model: Database Query Tool

**Date**: 2025-12-13
**Branch**: `001-db-query-tool`

## Overview

This document defines the data models used throughout the application. All models follow the constitution requirements:
- Pydantic v2 for backend models
- CamelCase JSON serialization via `alias_generator`
- TypeScript interfaces matching backend contracts

## Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│  DatabaseConnection │       │   DatabaseMetadata  │
├─────────────────────┤       ├─────────────────────┤
│ name (PK)           │──────▶│ database_name (FK)  │
│ url                 │       │ tables              │
│ created_at          │       │ views               │
│ last_connected_at   │       │ extracted_at        │
└─────────────────────┘       └─────────────────────┘
                                       │
                                       │ contains
                                       ▼
                              ┌─────────────────────┐
                              │    TableInfo        │
                              ├─────────────────────┤
                              │ name                │
                              │ schema              │
                              │ type (table/view)   │
                              │ columns             │
                              └─────────────────────┘
                                       │
                                       │ contains
                                       ▼
                              ┌─────────────────────┐
                              │    ColumnInfo       │
                              ├─────────────────────┤
                              │ name                │
                              │ data_type           │
                              │ is_nullable         │
                              │ is_primary_key      │
                              │ is_foreign_key      │
                              │ default_value       │
                              └─────────────────────┘
```

## Backend Models (Pydantic)

### Base Model

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    """Base model with camelCase JSON serialization."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
```

### Database Connection Models

```python
class DatabaseConnectionCreate(CamelModel):
    """Request model for creating/updating a database connection."""
    url: str  # postgresql://user:pass@host:port/dbname

class DatabaseConnection(CamelModel):
    """Database connection stored in local SQLite."""
    name: str
    url: str
    created_at: datetime
    last_connected_at: datetime | None = None

class DatabaseConnectionResponse(CamelModel):
    """API response for database connection (URL masked)."""
    name: str
    url_masked: str  # postgresql://user:***@host:port/dbname
    created_at: datetime
    last_connected_at: datetime | None = None
```

### Metadata Models

```python
class ColumnInfo(CamelModel):
    """Column metadata from PostgreSQL information_schema."""
    name: str
    data_type: str  # PostgreSQL type (varchar, integer, etc.)
    is_nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    default_value: str | None = None
    description: str | None = None  # Column comment if available

class TableInfo(CamelModel):
    """Table or view metadata."""
    name: str
    schema_name: str  # PostgreSQL schema (usually 'public')
    table_type: str  # 'table' or 'view'
    columns: list[ColumnInfo]
    row_count_estimate: int | None = None  # From pg_stat_user_tables

class DatabaseMetadata(CamelModel):
    """Complete database schema metadata."""
    database_name: str
    tables: list[TableInfo]
    views: list[TableInfo]
    extracted_at: datetime
```

### Query Models

```python
class QueryRequest(CamelModel):
    """Request model for executing SQL query."""
    sql: str

class QueryResult(CamelModel):
    """Response model for query execution."""
    columns: list[str]
    rows: list[dict]  # Each row as {columnName: value}
    row_count: int
    execution_time_ms: float
    truncated: bool  # True if LIMIT was auto-applied

class QueryError(CamelModel):
    """Error response for query failures."""
    error: str
    error_type: str  # 'syntax_error', 'validation_error', 'execution_error'
    details: str | None = None
```

### Natural Language Query Models

```python
class NaturalQueryRequest(CamelModel):
    """Request model for natural language SQL generation."""
    prompt: str  # e.g., "查询用户表的所有信息"

class GeneratedSQL(CamelModel):
    """Response model for generated SQL."""
    sql: str
    explanation: str | None = None  # Optional explanation of the query
    confidence: float | None = None  # 0.0-1.0 confidence score
```

## Frontend Types (TypeScript)

### types/database.ts

```typescript
export interface DatabaseConnectionCreate {
  url: string;
}

export interface DatabaseConnection {
  name: string;
  urlMasked: string;
  createdAt: string;  // ISO 8601
  lastConnectedAt: string | null;
}

export interface ColumnInfo {
  name: string;
  dataType: string;
  isNullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  defaultValue: string | null;
  description: string | null;
}

export interface TableInfo {
  name: string;
  schemaName: string;
  tableType: 'table' | 'view';
  columns: ColumnInfo[];
  rowCountEstimate: number | null;
}

export interface DatabaseMetadata {
  databaseName: string;
  tables: TableInfo[];
  views: TableInfo[];
  extractedAt: string;  // ISO 8601
}
```

### types/query.ts

```typescript
export interface QueryRequest {
  sql: string;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  executionTimeMs: number;
  truncated: boolean;
}

export interface QueryError {
  error: string;
  errorType: 'syntax_error' | 'validation_error' | 'execution_error';
  details: string | null;
}
```

### types/natural.ts

```typescript
export interface NaturalQueryRequest {
  prompt: string;
}

export interface GeneratedSQL {
  sql: string;
  explanation: string | null;
  confidence: number | null;
}
```

## SQLite Schema (Local Storage)

```sql
-- ~/.db_query/db_query.db

CREATE TABLE IF NOT EXISTS database_connections (
    name TEXT PRIMARY KEY,
    url TEXT NOT NULL,  -- Base64 encoded for basic obfuscation
    created_at TEXT NOT NULL,  -- ISO 8601
    last_connected_at TEXT  -- ISO 8601, nullable
);

CREATE TABLE IF NOT EXISTS database_metadata (
    database_name TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,  -- JSON blob of DatabaseMetadata
    extracted_at TEXT NOT NULL,  -- ISO 8601
    FOREIGN KEY (database_name) REFERENCES database_connections(name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metadata_extracted
ON database_metadata(extracted_at);
```

## Validation Rules

### DatabaseConnectionCreate

| Field | Rule | Error Message |
|-------|------|---------------|
| url | Must start with `postgresql://` or `postgres://` | "Invalid PostgreSQL URL format" |
| url | Must contain host | "Missing host in connection URL" |
| url | Must contain database name | "Missing database name in connection URL" |

### QueryRequest

| Field | Rule | Error Message |
|-------|------|---------------|
| sql | Must not be empty | "SQL query cannot be empty" |
| sql | Must be valid SQL syntax | "SQL syntax error: {details}" |
| sql | Must be SELECT statement | "Only SELECT queries are allowed" |

### NaturalQueryRequest

| Field | Rule | Error Message |
|-------|------|---------------|
| prompt | Must not be empty | "Prompt cannot be empty" |
| prompt | Max 1000 characters | "Prompt exceeds maximum length (1000 characters)" |

## State Transitions

### DatabaseConnection Lifecycle

```
[Not Exists] ──PUT /dbs/{name}──▶ [Created]
                                     │
                                     │ GET /dbs/{name} (metadata extraction)
                                     ▼
                                 [Connected]
                                     │
                                     │ Connection failure
                                     ▼
                                 [Error State]
                                     │
                                     │ Retry connection
                                     ▼
                                 [Connected]
```

### Query Execution Flow

```
[SQL Input] ──parse──▶ [Parsed AST]
                           │
                           │ validate (SELECT only)
                           ▼
                      [Validated]
                           │
                           │ add LIMIT if missing
                           ▼
                      [Transformed]
                           │
                           │ execute
                           ▼
                      [Results] or [Error]
```
