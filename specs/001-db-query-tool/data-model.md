# 数据模型：数据库查询工具

**日期**: 2025-12-13 (更新: 2025-12-14)
**功能分支**: `001-db-query-tool`

## 概述

本文档定义数据库查询工具的数据模型，包括 SQLite 本地存储的表结构和 API 交互的数据传输对象 (DTO)。

---

## SQLite 存储模型

### 表结构

#### connections (数据库连接)

存储用户添加的 PostgreSQL 数据库连接信息。

| 列名 | 类型 | 约束 | 描述 |
|------|------|------|------|
| name | TEXT | PRIMARY KEY | 连接的唯一标识名称 |
| url | TEXT | NOT NULL | PostgreSQL 连接 URL |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 创建时间 (ISO 8601) |
| updated_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 更新时间 (ISO 8601) |

```sql
CREATE TABLE IF NOT EXISTS connections (
    name TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### metadata_cache (元数据缓存)

缓存从 PostgreSQL 提取的表和视图元数据。

| 列名 | 类型 | 约束 | 描述 |
|------|------|------|------|
| connection_name | TEXT | PK, FK | 关联的连接名称 |
| schema_name | TEXT | PK | PostgreSQL schema 名称 |
| table_name | TEXT | PK | 表或视图名称 |
| table_type | TEXT | NOT NULL | 类型: 'TABLE' 或 'VIEW' |
| columns_json | TEXT | NOT NULL | 列信息 JSON 数组 |
| cached_at | TEXT | DEFAULT | 缓存时间 (ISO 8601) |

```sql
CREATE TABLE IF NOT EXISTS metadata_cache (
    connection_name TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    table_type TEXT NOT NULL CHECK (table_type IN ('TABLE', 'VIEW')),
    columns_json TEXT NOT NULL,
    cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (connection_name, schema_name, table_name),
    FOREIGN KEY (connection_name) REFERENCES connections(name) ON DELETE CASCADE
);
```

#### columns_json 格式

```json
[
  {
    "name": "id",
    "dataType": "integer",
    "nullable": false,
    "defaultValue": "nextval('users_id_seq'::regclass)",
    "isPrimaryKey": true,
    "isForeignKey": false
  },
  {
    "name": "email",
    "dataType": "character varying",
    "nullable": false,
    "defaultValue": null,
    "isPrimaryKey": false,
    "isForeignKey": false
  }
]
```

---

## API 数据传输对象 (DTO)

### 请求模型

#### DatabaseCreateRequest

添加数据库连接的请求体。

```python
class DatabaseCreateRequest(BaseModel):
    url: str = Field(
        ...,
        description="PostgreSQL 连接 URL",
        examples=["postgresql://user:pass@localhost:5432/mydb"]
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("URL 必须以 postgresql:// 或 postgres:// 开头")
        return v
```

#### QueryRequest

执行 SQL 查询的请求体。

```python
class QueryRequest(BaseModel):
    sql: str = Field(
        ...,
        description="要执行的 SQL 查询",
        examples=["SELECT * FROM users WHERE status = 'active'"]
    )
```

#### NaturalLanguageQueryRequest

自然语言查询的请求体。

```python
class NaturalLanguageQueryRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="自然语言查询描述",
        examples=["查询所有活跃用户的邮箱和注册时间"]
    )
```

---

### 响应模型

#### DatabaseInfo

数据库连接信息。

```python
class DatabaseInfo(BaseModel):
    name: str = Field(..., description="连接名称")
    url: str = Field(..., description="连接 URL (可能隐藏密码)")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)
```

#### ColumnInfo

列信息。

```python
class ColumnInfo(BaseModel):
    name: str = Field(..., description="列名")
    data_type: str = Field(..., alias="dataType", description="数据类型")
    nullable: bool = Field(..., description="是否可空")
    default_value: str | None = Field(None, alias="defaultValue", description="默认值")
    is_primary_key: bool = Field(False, alias="isPrimaryKey", description="是否主键")
    is_foreign_key: bool = Field(False, alias="isForeignKey", description="是否外键")

    model_config = ConfigDict(populate_by_name=True)
```

#### TableInfo

表或视图信息。

```python
class TableInfo(BaseModel):
    schema_name: str = Field(..., alias="schemaName", description="Schema 名称")
    name: str = Field(..., description="表或视图名称")
    type: Literal["TABLE", "VIEW"] = Field(..., description="类型")
    columns: list[ColumnInfo] = Field(default_factory=list, description="列列表")

    model_config = ConfigDict(populate_by_name=True)
```

#### DatabaseMetadata

数据库完整元数据。

```python
class DatabaseMetadata(BaseModel):
    name: str = Field(..., description="连接名称")
    url: str = Field(..., description="连接 URL")
    tables: list[TableInfo] = Field(default_factory=list, description="表列表")
    views: list[TableInfo] = Field(default_factory=list, description="视图列表")
    cached_at: datetime = Field(..., alias="cachedAt", description="缓存时间")

    model_config = ConfigDict(populate_by_name=True)
```

#### QueryResult

查询执行结果。

```python
class QueryResult(BaseModel):
    columns: list[str] = Field(..., description="列名列表")
    rows: list[dict[str, Any]] = Field(..., description="数据行列表")
    row_count: int = Field(..., alias="rowCount", description="返回行数")
    execution_time_ms: float = Field(..., alias="executionTimeMs", description="执行时间(毫秒)")

    model_config = ConfigDict(populate_by_name=True)
```

#### NaturalLanguageQueryResult

自然语言查询结果 (包含生成的 SQL)。

```python
class NaturalLanguageQueryResult(BaseModel):
    generated_sql: str = Field(..., alias="generatedSql", description="生成的 SQL")
    result: QueryResult | None = Field(None, description="执行结果 (如果自动执行)")
    error: str | None = Field(None, description="错误信息")

    model_config = ConfigDict(populate_by_name=True)
```

---

### 错误响应

#### ErrorResponse

统一错误响应格式。

```python
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="错误描述")
    code: str = Field(..., description="错误代码")
```

#### 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|-----------|------|
| `CONNECTION_FAILED` | 400 | 无法连接到数据库 |
| `CONNECTION_NOT_FOUND` | 404 | 数据库连接不存在 |
| `INVALID_URL` | 400 | 连接 URL 格式无效 |
| `INVALID_SQL` | 400 | SQL 语法错误 |
| `NON_SELECT_QUERY` | 400 | 只允许 SELECT 查询 |
| `QUERY_TIMEOUT` | 408 | 查询执行超时 |
| `LLM_ERROR` | 500 | LLM 服务错误 |

---

## 实体关系图

```
┌─────────────────────┐
│    connections      │
├─────────────────────┤
│ PK name             │───────────┐
│    url              │           │
│    created_at       │           │
│    updated_at       │           │
└─────────────────────┘           │
                                  │ 1:N
                                  ▼
┌─────────────────────────────────────────┐
│           metadata_cache                │
├─────────────────────────────────────────┤
│ PK,FK connection_name                   │
│ PK     schema_name                      │
│ PK     table_name                       │
│        table_type                       │
│        columns_json                     │
│        cached_at                        │
└─────────────────────────────────────────┘
```

---

## 数据流

### 添加数据库连接

```
用户输入 URL
    ↓
验证 URL 格式 (DatabaseCreateRequest)
    ↓
尝试连接 PostgreSQL
    ↓
成功: 存储到 connections 表
    ↓
提取元数据 (tables, columns)
    ↓
存储到 metadata_cache 表
    ↓
返回 DatabaseMetadata
```

### 执行 SQL 查询

```
用户输入 SQL (QueryRequest)
    ↓
sqlglot 解析验证
    ↓
检查是否为 SELECT
    ↓
检查/添加 LIMIT 1000
    ↓
执行查询
    ↓
返回 QueryResult
```

### 自然语言查询

```
用户输入自然语言 (NaturalLanguageQueryRequest)
    ↓
从 metadata_cache 获取 schema context
    ↓
调用 OpenAI API 生成 SQL
    ↓
返回 NaturalLanguageQueryResult (含 generatedSql)
    ↓
用户确认执行
    ↓
走 SQL 查询流程
```

---

## 导出功能 (前端)

导出功能完全在前端实现，使用现有的 `QueryResult` 类型，不需要新的后端模型或 API 端点。

### 导出配置类型

```typescript
// types/export.ts

/**
 * 导出格式枚举
 */
export type ExportFormat = 'csv' | 'json';

/**
 * 导出选项
 */
export interface ExportOptions {
  /** 导出格式 */
  format: ExportFormat;
  /** 自定义文件名 (不含扩展名) */
  filename?: string;
}
```

### 导出工具函数签名

```typescript
// utils/export.ts

/**
 * 导出为 CSV 格式
 * @param columns - 列名数组
 * @param rows - 数据行数组
 * @param filename - 可选文件名
 */
export function exportToCSV(
  columns: string[],
  rows: Record<string, unknown>[],
  filename?: string
): void;

/**
 * 导出为 JSON 格式
 * @param rows - 数据行数组
 * @param filename - 可选文件名
 */
export function exportToJSON(
  rows: Record<string, unknown>[],
  filename?: string
): void;
```

### 导出数据流

```
QueryResult (内存中)
    ↓
用户点击导出按钮
    ↓
选择格式 (CSV/JSON)
    ↓
exportToCSV/exportToJSON
    ↓
生成文件内容 (含 UTF-8 BOM for CSV)
    ↓
创建 Blob → URL.createObjectURL
    ↓
触发浏览器下载
    ↓
清理临时 URL
```

### 文件命名规则

| 格式 | 文件名模板 | 示例 |
|------|-----------|------|
| CSV | `query_result_YYYYMMDD_HHMMSS.csv` | `query_result_20251214_153022.csv` |
| JSON | `query_result_YYYYMMDD_HHMMSS.json` | `query_result_20251214_153022.json` |

---

## 类型定义 (TypeScript)

前端对应的 TypeScript 类型:

```typescript
// types/index.ts

export interface DatabaseInfo {
  name: string;
  url: string;
  createdAt: string;
  updatedAt: string;
}

export interface ColumnInfo {
  name: string;
  dataType: string;
  nullable: boolean;
  defaultValue: string | null;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
}

export interface TableInfo {
  schemaName: string;
  name: string;
  type: "TABLE" | "VIEW";
  columns: ColumnInfo[];
}

export interface DatabaseMetadata {
  name: string;
  url: string;
  tables: TableInfo[];
  views: TableInfo[];
  cachedAt: string;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  executionTimeMs: number;
}

export interface NaturalLanguageQueryResult {
  generatedSql: string;
  result?: QueryResult;
  error?: string;
}

export interface ErrorResponse {
  detail: string;
  code: string;
}
```
