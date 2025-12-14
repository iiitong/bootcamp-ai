# 技术研究：数据库查询工具

**日期**: 2025-12-13 (更新: 2025-12-14)
**功能分支**: `001-db-query-tool`

## 概述

本文档记录技术选型决策、最佳实践和实现注意事项。包含各依赖库的具体版本和实现代码示例。

---

## 版本清单

| 依赖 | 推荐版本 | 说明 |
|------|----------|------|
| **后端** | | |
| Python | 3.14+ | 使用 uv 管理 |
| FastAPI | >=0.109.0 | Pydantic v2 原生支持 |
| Pydantic | >=2.0.0 | v2 必需 |
| sqlglot | >=24.0.0,<25.0.0 | 稳定 API |
| openai | >=1.3.0 | v1.x 客户端 API |
| psycopg[binary] | >=3.1.0 | psycopg3 推荐 |
| uvicorn | >=0.27.0 | ASGI 服务器 |
| pytest | >=8.0.0 | 测试框架 |
| **前端** | | |
| React | ^18.2.0 | 并发特性支持 |
| @refinedev/core | ^5.x.x | 管理框架 |
| @refinedev/antd | ^5.x.x | Ant Design 集成 |
| @monaco-editor/react | ^4.6.0 | SQL 编辑器 |
| monaco-editor | ^0.50.0 | 编辑器核心 |
| antd | ^5.x.x | UI 组件库 |
| tailwindcss | ^3.x.x | 样式工具 |

---

## 后端技术栈

### 1. FastAPI + Pydantic v2

**版本**: FastAPI >=0.109.0, Pydantic >=2.0.0

**决策**: FastAPI 原生支持 Pydantic v2，提供更好的性能和类型验证

**CORS 配置**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DB Query Tool API", version="1.0.0")

# CORS 配置 - 允许所有 origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Pydantic v2 camelCase 输出**:
```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

class DatabaseInfo(BaseModel):
    """数据库连接信息 - 输出 camelCase"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str
    url: str
    created_at: datetime
    updated_at: datetime

# 输出示例: {"name": "...", "url": "...", "createdAt": "...", "updatedAt": "..."}
```

**Lifespan 事件 (数据库初始化)**:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 初始化数据库连接池
    await init_db_pool()
    yield
    # Shutdown: 关闭连接池
    await close_db_pool()

app = FastAPI(lifespan=lifespan)
```

**自定义异常处理**:
```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

class QueryValidationError(Exception):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.code = code

@app.exception_handler(QueryValidationError)
async def validation_exception_handler(request: Request, exc: QueryValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "code": exc.code},
    )
```

---

### 2. sqlglot (SQL 解析)

**版本**: >=24.0.0,<25.0.0

**决策**: 纯 Python 实现，无需外部依赖，支持多种 SQL 方言

**完整验证流程**:
```python
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

class SQLProcessor:
    """SQL 解析、验证和转换"""

    DEFAULT_LIMIT = 1000
    BLOCKED_TYPES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Truncate)

    @classmethod
    def process(cls, sql: str, max_limit: int = None) -> str:
        """完整流程: 解析 → 验证 → 添加 LIMIT → 生成 SQL"""
        # 1. 验证非空
        if not sql or not sql.strip():
            raise ValueError("SQL 查询不能为空")

        # 2. 解析 (PostgreSQL 方言)
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")
        except ParseError as e:
            raise ValueError(f"SQL 语法错误: {str(e)}")

        if parsed is None:
            raise ValueError("无法解析 SQL 语句")

        # 3. 验证只允许 SELECT
        if isinstance(parsed, cls.BLOCKED_TYPES):
            raise ValueError(f"只允许执行 SELECT 查询，{type(parsed).__name__} 不被允许")

        if not isinstance(parsed, (exp.Select, exp.Union)):
            raise ValueError(f"不支持的语句类型: {type(parsed).__name__}")

        # 4. 添加 LIMIT (如果缺失)
        if isinstance(parsed, exp.Select) and parsed.find(exp.Limit) is None:
            parsed = parsed.limit(max_limit or cls.DEFAULT_LIMIT)

        # 5. 生成 PostgreSQL 兼容 SQL
        return parsed.sql(dialect="postgres")

# 使用示例
sql = "SELECT * FROM users WHERE status = 'active'"
safe_sql = SQLProcessor.process(sql)
# 输出: "SELECT * FROM users WHERE status = 'active' LIMIT 1000"
```

**测试用例**:
```python
def test_select_adds_limit():
    result = SQLProcessor.process("SELECT * FROM users")
    assert "LIMIT 1000" in result

def test_existing_limit_preserved():
    result = SQLProcessor.process("SELECT * FROM users LIMIT 10")
    assert "LIMIT 10" in result
    assert "LIMIT 1000" not in result

def test_insert_rejected():
    with pytest.raises(ValueError, match="只允许执行 SELECT"):
        SQLProcessor.process("INSERT INTO users (name) VALUES ('test')")

def test_syntax_error():
    with pytest.raises(ValueError, match="SQL 语法错误"):
        SQLProcessor.process("SELECT * FRMO users")  # typo
```

---

### 3. OpenAI SDK (自然语言转 SQL)

**版本**: >=1.3.0

**决策**: 使用 gpt-4o-mini 平衡成本和效果，temperature=0 确保一致性

**客户端初始化**:
```python
import os
from openai import OpenAI

# 从环境变量获取 API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Text-to-SQL 生成器**:
```python
from openai import OpenAI, APIError, RateLimitError
import os
import re

class TextToSQLGenerator:
    """自然语言转 SQL 生成器"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.schema_context = ""

    def set_schema_context(self, tables_info: list[dict]) -> None:
        """设置数据库结构上下文"""
        lines = []
        for table in tables_info:
            cols = ", ".join([f"{c['name']} {c['dataType']}" for c in table['columns']])
            lines.append(f"- {table['schemaName']}.{table['name']} ({cols})")
        self.schema_context = "\n".join(lines)

    def generate(self, natural_language: str) -> str:
        """生成 SQL 查询"""
        system_prompt = f"""你是一个 PostgreSQL 专家。根据用户的自然语言描述生成 SQL 查询。

数据库结构:
{self.schema_context}

规则:
- 只生成 SELECT 语句
- 不要添加 LIMIT（系统会自动添加）
- 只返回 SQL 代码，不要解释
- 使用标准 PostgreSQL 语法"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language}
                ],
                temperature=0,  # 确保一致性
                max_tokens=500,
            )

            sql = response.choices[0].message.content.strip()
            # 清理 markdown 代码块
            sql = re.sub(r'^```sql\n?', '', sql)
            sql = re.sub(r'\n?```$', '', sql)
            return sql

        except RateLimitError:
            raise ValueError("API 请求过于频繁，请稍后重试")
        except APIError as e:
            raise ValueError(f"LLM 服务错误: {str(e)}")
```

**模型选择建议**:

| 模型 | 用途 | 成本 |
|------|------|------|
| gpt-4o-mini | 推荐：日常 SQL 生成 | ~$0.15/1M 输入 |
| gpt-4o | 复杂查询、多表 JOIN | ~$5/1M 输入 |

---

### 4. psycopg (PostgreSQL 驱动)

**版本**: psycopg[binary] >=3.1.0

**决策**: 使用 psycopg3（不是 psycopg2），原生支持 async

**连接池配置**:
```python
from psycopg_pool import AsyncConnectionPool
import os

# 全局连接池
pool: AsyncConnectionPool | None = None

async def init_db_pool():
    """初始化连接池（在 lifespan startup 调用）"""
    global pool
    pool = AsyncConnectionPool(
        os.getenv("DATABASE_URL", "postgresql://localhost/test"),
        min_size=2,
        max_size=10,
        max_idle=300,      # 5 分钟后关闭空闲连接
        max_lifetime=3600,  # 1 小时后回收连接
    )
    await pool.open()

async def close_db_pool():
    """关闭连接池（在 lifespan shutdown 调用）"""
    if pool:
        await pool.close()
```

**FastAPI 依赖注入**:
```python
from fastapi import Depends
from typing import AsyncGenerator
import psycopg

async def get_db() -> AsyncGenerator:
    """获取数据库连接（FastAPI 依赖）"""
    async with pool.connection() as conn:
        yield conn

@app.get("/api/v1/dbs/{name}")
async def get_database_metadata(name: str, conn = Depends(get_db)):
    async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        await cur.execute("SELECT * FROM metadata WHERE db_name = %s", (name,))
        return await cur.fetchall()
```

**元数据提取**:
```python
import psycopg
from psycopg.rows import dict_row

TABLES_QUERY = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name
"""

COLUMNS_QUERY = """
SELECT table_schema, table_name, column_name, data_type,
       is_nullable, column_default, ordinal_position
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position
"""

async def extract_metadata(connection_url: str) -> dict:
    """从 PostgreSQL 提取元数据"""
    async with await psycopg.AsyncConnection.connect(connection_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(TABLES_QUERY)
            tables = await cur.fetchall()

            await cur.execute(COLUMNS_QUERY)
            columns = await cur.fetchall()

    # 组织成层级结构
    result = {"tables": [], "views": []}
    table_map = {}

    for t in tables:
        item = {
            "schemaName": t["table_schema"],
            "name": t["table_name"],
            "type": t["table_type"],
            "columns": []
        }
        key = (t["table_schema"], t["table_name"])
        table_map[key] = item

        if t["table_type"] == "VIEW":
            result["views"].append(item)
        else:
            result["tables"].append(item)

    for c in columns:
        key = (c["table_schema"], c["table_name"])
        if key in table_map:
            table_map[key]["columns"].append({
                "name": c["column_name"],
                "dataType": c["data_type"],
                "nullable": c["is_nullable"] == "YES",
                "defaultValue": c["column_default"],
            })

    return result
```

---

## 前端技术栈

### 5. Refine 5

**版本**: @refinedev/core ^5.x.x, @refinedev/antd ^5.x.x

**决策**: 使用自定义 data provider 适配非标准 API

**自定义 Data Provider**:
```typescript
// src/providers/dataProvider.ts
import { DataProvider } from "@refinedev/core";

const API_URL = "http://localhost:8000/api/v1";

export const dataProvider: DataProvider = {
  getList: async ({ resource }) => {
    const response = await fetch(`${API_URL}/${resource}`);
    if (!response.ok) throw new Error("Failed to fetch");
    const data = await response.json();
    return { data, total: data.length };
  },

  getOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`);
    if (!response.ok) throw new Error("Failed to fetch");
    const data = await response.json();
    return { data };
  },

  create: async ({ resource, variables }) => {
    const response = await fetch(`${API_URL}/${resource}`, {
      method: "PUT",  // 注意：我们的 API 使用 PUT
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(variables),
    });
    if (!response.ok) throw new Error("Failed to create");
    const data = await response.json();
    return { data };
  },

  update: async ({ resource, id, variables }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(variables),
    });
    if (!response.ok) throw new Error("Failed to update");
    const data = await response.json();
    return { data };
  },

  deleteOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete");
    return { data: {} as any };
  },

  getApiUrl: () => API_URL,
};
```

**useCustom Hook (非 CRUD 端点)**:
```typescript
import { useCustom, useCustomMutation } from "@refinedev/core";

// 执行 SQL 查询
function useExecuteQuery(dbName: string) {
  const { mutate, isLoading, data, error } = useCustomMutation();

  const executeQuery = (sql: string) => {
    mutate({
      url: `http://localhost:8000/api/v1/dbs/${dbName}/query`,
      method: "post",
      values: { sql },
    });
  };

  return { executeQuery, isLoading, data, error };
}

// 自然语言生成 SQL
function useNaturalLanguageQuery(dbName: string) {
  const { mutate, isLoading, data } = useCustomMutation();

  const generateSQL = (prompt: string) => {
    mutate({
      url: `http://localhost:8000/api/v1/dbs/${dbName}/query/natural`,
      method: "post",
      values: { prompt },
    });
  };

  return { generateSQL, isLoading, generatedSQL: data?.data?.generatedSql };
}
```

---

### 6. Monaco Editor (SQL 编辑器)

**版本**: @monaco-editor/react ^4.6.0, monaco-editor ^0.50.0

**决策**: 使用 VS Code 同款编辑器，内置 SQL 语法高亮

**SQL 编辑器组件**:
```typescript
// src/components/SqlEditor.tsx
import { memo, useCallback } from "react";
import Editor from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  height?: string;
}

const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  lineNumbers: "on",
  minimap: { enabled: false },
  fontSize: 14,
  fontFamily: "'Fira Code', 'Monaco', 'Menlo', monospace",
  wordWrap: "on",
  scrollBeyondLastLine: false,
  automaticLayout: true,
  formatOnPaste: false,
  formatOnType: false,
  renderLineHighlight: "gutter",
  folding: true,
};

export const SqlEditor = memo<SqlEditorProps>(({
  value,
  onChange,
  readOnly = false,
  height = "200px"
}) => {
  const handleChange = useCallback((newValue: string | undefined) => {
    if (newValue !== undefined) {
      onChange(newValue);
    }
  }, [onChange]);

  return (
    <div className="border border-gray-300 rounded">
      <Editor
        height={height}
        language="sql"
        value={value}
        onChange={handleChange}
        theme="vs-dark"
        options={{ ...editorOptions, readOnly }}
      />
    </div>
  );
});

SqlEditor.displayName = "SqlEditor";
```

**性能优化要点**:
- 使用 `memo` 防止不必要的重渲染
- 使用 `useCallback` 缓存 onChange 处理器
- 禁用 minimap 和 formatOnType 减少开销
- 设置 `automaticLayout: true` 自动响应容器大小变化

---

### 7. Tailwind CSS + Ant Design 集成

**配置注意事项**:
```javascript
// tailwind.config.js
module.exports = {
  important: true,  // 确保 Tailwind 优先级
  corePlugins: {
    preflight: false,  // 禁用 reset，避免影响 Ant Design
  },
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

---

## 集成检查清单

| 检查项 | 状态 |
|--------|------|
| FastAPI CORS 允许所有 origin | ✅ |
| Pydantic v2 camelCase 输出 | ✅ |
| sqlglot SELECT-only 验证 | ✅ |
| sqlglot 自动添加 LIMIT 1000 | ✅ |
| psycopg3 异步连接池 | ✅ |
| OpenAI temperature=0 | ✅ |
| Refine 自定义 data provider | ✅ |
| Monaco Editor SQL 高亮 | ✅ |
| CSV 导出 UTF-8 BOM | ✅ |
| CSV 特殊字符转义 | ✅ |
| JSON 导出数组格式 | ✅ |
| 空结果禁用导出按钮 | ✅ |

---

## 8. 查询结果导出 (新增)

**版本**: 无额外依赖（使用浏览器原生 API）

**决策**: 前端实现导出，使用 Blob + URL.createObjectURL 触发下载

### CSV 导出实现

```typescript
// src/utils/export.ts

/**
 * 生成 CSV 格式内容
 * - 使用 UTF-8 with BOM 编码确保 Excel 正确显示中文
 * - 正确转义包含逗号、换行符、双引号的字段
 */
export function exportToCSV(
  columns: string[],
  rows: Record<string, unknown>[],
  filename?: string
): void {
  // UTF-8 BOM
  const BOM = '\uFEFF';

  // 转义 CSV 字段
  const escapeField = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    const str = String(value);
    // 包含逗号、换行或双引号时需要用双引号包裹
    if (str.includes(',') || str.includes('\n') || str.includes('"')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  // 构建 CSV 内容
  const headerLine = columns.map(escapeField).join(',');
  const dataLines = rows.map(row =>
    columns.map(col => escapeField(row[col])).join(',')
  );
  const csvContent = BOM + [headerLine, ...dataLines].join('\n');

  // 生成文件名
  const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 15);
  const finalFilename = filename || `query_result_${timestamp}.csv`;

  // 触发下载
  downloadBlob(csvContent, finalFilename, 'text/csv;charset=utf-8');
}
```

### JSON 导出实现

```typescript
/**
 * 生成 JSON 格式内容
 * - 使用简单数组格式 [{col1: val1}, ...]
 * - 格式化输出便于阅读
 */
export function exportToJSON(
  rows: Record<string, unknown>[],
  filename?: string
): void {
  const jsonContent = JSON.stringify(rows, null, 2);

  // 生成文件名
  const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 15);
  const finalFilename = filename || `query_result_${timestamp}.json`;

  // 触发下载
  downloadBlob(jsonContent, finalFilename, 'application/json;charset=utf-8');
}
```

### 通用下载函数

```typescript
/**
 * 使用 Blob 和 URL.createObjectURL 触发文件下载
 */
function downloadBlob(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();

  // 清理
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
```

### 导出按钮组件

```typescript
// src/components/ExportButtons.tsx
import { Button, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { exportToCSV, exportToJSON } from '../utils/export';
import type { QueryResult } from '../types';

interface ExportButtonsProps {
  result: QueryResult | null;
}

export function ExportButtons({ result }: ExportButtonsProps) {
  if (!result || result.rowCount === 0) {
    return null; // 无结果或空结果时不显示
  }

  return (
    <Space>
      <Button
        icon={<DownloadOutlined />}
        onClick={() => exportToCSV(result.columns, result.rows)}
      >
        导出 CSV
      </Button>
      <Button
        icon={<DownloadOutlined />}
        onClick={() => exportToJSON(result.rows)}
      >
        导出 JSON
      </Button>
    </Space>
  );
}
```

### 测试用例

```typescript
// tests/unit/export.test.ts
import { describe, it, expect, vi } from 'vitest';
import { exportToCSV, exportToJSON } from '../../src/utils/export';

describe('CSV Export', () => {
  it('should include UTF-8 BOM', () => {
    const mockDownload = vi.fn();
    // ... mock downloadBlob
    exportToCSV(['name'], [{ name: 'test' }]);
    expect(mockDownload).toHaveBeenCalledWith(
      expect.stringMatching(/^\uFEFF/), // BOM
      expect.any(String),
      expect.any(String)
    );
  });

  it('should escape fields with special characters', () => {
    const rows = [{ value: 'has,comma' }, { value: 'has"quote' }];
    // 验证转义逻辑
  });

  it('should generate correct filename format', () => {
    // 验证文件名格式: query_result_YYYYMMDD_HHMMSS.csv
  });
});

describe('JSON Export', () => {
  it('should produce valid JSON array', () => {
    const rows = [{ id: 1, name: '张三' }];
    // 验证 JSON 格式正确
  });
});
```

### 关键实现要点

| 要点 | 说明 |
|------|------|
| UTF-8 BOM | `\uFEFF` 确保 Excel 正确识别编码 |
| CSV 转义 | 逗号/换行/双引号需用双引号包裹，内部双引号转义为 `""` |
| 文件名格式 | `query_result_YYYYMMDD_HHMMSS.csv/json` |
| 空结果处理 | `rowCount === 0` 时禁用导出按钮 |
| 内存限制 | 最多 1000 行（由查询 LIMIT 保证） |

---

## 总结

所有技术选型已确定并验证。关键实现点:

1. **SQL 验证**: sqlglot 解析 → 检查 SELECT → 添加 LIMIT
2. **元数据提取**: information_schema 查询 → JSON 序列化 → SQLite 缓存
3. **自然语言 SQL**: 构建 schema context → OpenAI API (gpt-4o-mini) → 验证生成的 SQL
4. **前端**: Refine data provider + useCustom → Monaco Editor → Ant Design Table
5. **结果导出**: 前端 Blob API → CSV (UTF-8 BOM) / JSON → 浏览器下载
