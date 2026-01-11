# PostgreSQL MCP Server 设计文档

**版本**: 1.2
**日期**: 2026-01-10
**状态**: 已审核
**关联 PRD**: [0001-pg-mcp-prd.md](./0001-pg-mcp-prd.md)

---

## 1. 设计概述

### 1.1 设计目标

基于 PRD 需求，设计一个高内聚、低耦合的 PostgreSQL MCP 服务器，实现：

- **模块化**: 各组件职责单一，便于测试和维护
- **可扩展**: 预留扩展点，支持未来添加 MySQL 等数据库
- **类型安全**: 使用 Pydantic 进行数据验证和序列化
- **异步优先**: 全链路异步，充分利用 asyncpg 性能

### 1.2 技术栈确认

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.13.5 | 运行时 |
| FastMCP | latest | MCP 服务器框架 |
| asyncpg | ^0.29.0 | PostgreSQL 异步驱动 |
| sqlglot | ^26.0 | SQL 解析与验证 |
| Pydantic | ^2.10 | 数据模型与验证 |
| pydantic-settings | ^2.7 | 环境变量配置管理 |
| openai | ^1.60 | OpenAI API 客户端 |
| structlog | ^24.0 | 结构化日志 |

---

## 2. 系统架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client (Claude, etc.)                │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ MCP Protocol (stdio/SSE)
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Layer (FastMCP)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Resources     │  │     Tools       │  │    Lifecycle    │  │
│  │  - databases    │  │  - query        │  │  - on_startup   │  │
│  │  - schema       │  │                 │  │  - on_shutdown  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  QueryService   │  │ SchemaService   │  │ ValidationSvc   │  │
│  │  - generate_sql │  │ - get_schema    │  │ - validate_sql  │  │
│  │  - execute      │  │ - refresh       │  │ - check_safety  │  │
│  │  - validate_res │  │ - format        │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ DatabasePool    │  │  SchemaCache    │  │  OpenAIClient   │  │
│  │ (asyncpg)       │  │  (in-memory)    │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌───────────┐  ┌───────────┐  ┌───────────┐
             │ PostgreSQL│  │ PostgreSQL│  │  OpenAI   │
             │    DB 1   │  │    DB 2   │  │    API    │
             └───────────┘  └───────────┘  └───────────┘
```

### 2.2 项目结构

```
pg-mcp/
├── pyproject.toml                 # 项目配置 (uv)
├── .env.example                   # 环境变量配置示例
├── README.md
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── __main__.py            # 入口点
│       ├── server.py              # FastMCP 服务器定义
│       │
│       ├── config/                # 配置模块
│       │   ├── __init__.py
│       │   ├── models.py          # Pydantic 配置模型 (pydantic-settings)
│       │   └── loader.py          # 配置加载器 (环境变量)
│       │
│       ├── models/                # 数据模型
│       │   ├── __init__.py
│       │   ├── schema.py          # Schema 相关模型
│       │   ├── query.py           # 查询请求/响应模型
│       │   └── errors.py          # 错误模型
│       │
│       ├── services/              # 业务逻辑层
│       │   ├── __init__.py
│       │   ├── query_service.py   # 查询服务
│       │   ├── schema_service.py  # Schema 服务
│       │   └── validation_service.py  # SQL 验证服务
│       │
│       ├── infrastructure/        # 基础设施层
│       │   ├── __init__.py
│       │   ├── database.py        # 数据库连接池
│       │   ├── schema_cache.py    # Schema 缓存
│       │   ├── openai_client.py   # OpenAI 客户端封装
│       │   ├── sql_parser.py      # SQLGlot 封装
│       │   └── rate_limiter.py    # 速率限制器
│       │
│       └── utils/                 # 工具函数
│           ├── __init__.py
│           ├── logging.py         # 日志配置
│           └── env.py             # 环境变量处理
│
└── tests/
    ├── __init__.py
    ├── conftest.py                # pytest fixtures
    ├── unit/                      # 单元测试
    │   ├── test_sql_parser.py
    │   ├── test_validation.py
    │   └── test_schema_cache.py
    ├── integration/               # 集成测试
    │   ├── test_query_flow.py
    │   └── test_mcp_server.py
    └── fixtures/                  # 测试数据
        └── sample_schemas.py
```

---

## 3. 数据模型设计 (Pydantic)

### 3.1 配置模型 (环境变量驱动)

配置完全通过环境变量管理，使用 `pydantic-settings` 实现。每个配置类有独立的环境变量前缀。

**环境变量示例**:
```bash
# 数据库配置 (PG_MCP_DATABASE_*)
PG_MCP_DATABASE_HOST=localhost
PG_MCP_DATABASE_PORT=5432
PG_MCP_DATABASE_DBNAME=mydb
PG_MCP_DATABASE_USER=postgres
PG_MCP_DATABASE_PASSWORD=secret
# 或使用连接字符串
PG_MCP_DATABASE_URL=postgresql://user:pass@host:5432/db

# OpenAI 配置 (PG_MCP_OPENAI_*)
PG_MCP_OPENAI_API_KEY=sk-xxx
PG_MCP_OPENAI_MODEL=gpt-4o-mini

# 服务器配置 (PG_MCP_SERVER_*)
PG_MCP_SERVER_MAX_RESULT_ROWS=1000
PG_MCP_SERVER_QUERY_TIMEOUT=30.0

# 速率限制 (PG_MCP_RATE_LIMIT_*)
PG_MCP_RATE_LIMIT_ENABLED=true
PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

```python
# src/pg_mcp/config/models.py

from enum import Enum
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSLMode(str, Enum):
    """PostgreSQL SSL 模式"""
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"


class DatabaseConfig(BaseModel):
    """单个数据库连接配置"""
    name: str = Field(default="main", description="数据库别名")
    host: str | None = None
    port: int = 5432
    dbname: str | None = Field(default=None, description="数据库名称")
    user: str | None = None
    password: SecretStr | None = None
    url: SecretStr | None = Field(default=None, description="连接字符串")
    ssl_mode: SSLMode = SSLMode.PREFER
    min_pool_size: int = Field(default=2, ge=1, le=20)
    max_pool_size: int = Field(default=10, ge=1, le=100)

    def get_dsn(self) -> str:
        """获取数据库连接字符串"""
        if self.url:
            return self.url.get_secret_value()
        password = self.password.get_secret_value() if self.password else ""
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.dbname}"


class DatabaseSettings(BaseSettings):
    """数据库配置 - 从环境变量读取"""
    name: str = Field(default="main")
    host: str | None = None
    port: int = 5432
    dbname: str | None = None
    user: str | None = None
    password: SecretStr | None = None
    url: SecretStr | None = None
    ssl_mode: SSLMode = SSLMode.PREFER
    min_pool_size: int = Field(default=2)
    max_pool_size: int = Field(default=10)

    model_config = SettingsConfigDict(env_prefix="PG_MCP_DATABASE_", extra="ignore")


class OpenAISettings(BaseSettings):
    """OpenAI 配置 - 从环境变量读取"""
    api_key: SecretStr = Field(..., description="OpenAI API Key")
    model: str = Field(default="gpt-4o-mini")
    base_url: str | None = None
    max_retries: int = Field(default=3)
    timeout: float = Field(default=30.0)

    model_config = SettingsConfigDict(env_prefix="PG_MCP_OPENAI_", extra="ignore")


class RateLimitSettings(BaseSettings):
    """速率限制配置 - 从环境变量读取"""
    enabled: bool = Field(default=True)
    requests_per_minute: int = Field(default=60)
    requests_per_hour: int = Field(default=1000)
    openai_tokens_per_minute: int = Field(default=100000)

    model_config = SettingsConfigDict(env_prefix="PG_MCP_RATE_LIMIT_", extra="ignore")


class ServerSettings(BaseSettings):
    """服务器配置 - 从环境变量读取"""
    cache_refresh_interval: int = Field(default=3600)
    max_result_rows: int = Field(default=1000)
    query_timeout: float = Field(default=30.0)
    use_readonly_transactions: bool = Field(default=True)
    max_sql_retry: int = Field(default=2)

    model_config = SettingsConfigDict(env_prefix="PG_MCP_SERVER_", extra="ignore")


class AppConfig(BaseModel):
    """应用程序总配置"""
    databases: list[DatabaseConfig] = Field(..., min_length=1)
    openai: OpenAISettings
    server: ServerSettings = Field(default_factory=ServerSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
```

### 3.2 Schema 模型

```python
# src/pg_mcp/models/schema.py

from enum import Enum
from pydantic import BaseModel, Field


class IndexType(str, Enum):
    """索引类型"""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"


class ColumnInfo(BaseModel):
    """列信息"""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_unique: bool = False
    default_value: str | None = None
    comment: str | None = None

    # 外键信息
    foreign_key_table: str | None = None
    foreign_key_column: str | None = None

    # ENUM 类型的可选值
    enum_values: list[str] | None = None


class IndexInfo(BaseModel):
    """索引信息"""
    name: str
    columns: list[str]
    index_type: IndexType = IndexType.BTREE
    is_unique: bool = False
    is_primary: bool = False


class TableInfo(BaseModel):
    """表信息"""
    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    indexes: list[IndexInfo] = Field(default_factory=list)
    comment: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.name}"


class ViewInfo(BaseModel):
    """视图信息"""
    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    definition: str | None = None  # CREATE VIEW 语句


class EnumTypeInfo(BaseModel):
    """枚举类型信息"""
    name: str
    schema_name: str = "public"
    values: list[str]


class DatabaseSchema(BaseModel):
    """数据库完整 Schema"""
    name: str  # 数据库别名
    tables: list[TableInfo] = Field(default_factory=list)
    views: list[ViewInfo] = Field(default_factory=list)
    enum_types: list[EnumTypeInfo] = Field(default_factory=list)

    # 缓存元数据
    cached_at: float | None = None  # Unix timestamp

    @property
    def tables_count(self) -> int:
        return len(self.tables)

    @property
    def views_count(self) -> int:
        return len(self.views)

    def to_prompt_text(self) -> str:
        """生成用于 LLM Prompt 的 Schema 描述"""
        lines = [f"Database: {self.name}\n"]

        # 表信息
        if self.tables:
            lines.append("## Tables\n")
            for table in self.tables:
                lines.append(f"### {table.name}")
                lines.append("Columns:")
                for col in table.columns:
                    col_desc = f"  - {col.name}: {col.data_type}"
                    attrs = []
                    if col.is_primary_key:
                        attrs.append("PRIMARY KEY")
                    if not col.is_nullable:
                        attrs.append("NOT NULL")
                    if col.is_unique:
                        attrs.append("UNIQUE")
                    if col.foreign_key_table:
                        attrs.append(f"FK -> {col.foreign_key_table}.{col.foreign_key_column}")
                    if col.enum_values:
                        attrs.append(f"ENUM: {col.enum_values}")
                    if attrs:
                        col_desc += f" ({', '.join(attrs)})"
                    lines.append(col_desc)

                if table.indexes:
                    lines.append("Indexes:")
                    for idx in table.indexes:
                        idx_attrs = []
                        if idx.is_primary:
                            idx_attrs.append("PRIMARY")
                        if idx.is_unique:
                            idx_attrs.append("UNIQUE")
                        idx_attrs.append(idx.index_type.value)
                        lines.append(f"  - {idx.name} ({', '.join(idx_attrs)} on {', '.join(idx.columns)})")
                lines.append("")

        # 枚举类型
        if self.enum_types:
            lines.append("## Custom Types")
            for enum in self.enum_types:
                lines.append(f"- {enum.name}: ENUM ({', '.join(repr(v) for v in enum.values)})")

        return "\n".join(lines)
```

### 3.3 查询请求/响应模型

```python
# src/pg_mcp/models/query.py

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ReturnType(str, Enum):
    """查询返回类型"""
    SQL = "sql"
    RESULT = "result"
    BOTH = "both"


class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="自然语言查询需求")
    database: str | None = Field(default=None, description="目标数据库名称")
    return_type: ReturnType = Field(default=ReturnType.RESULT, description="返回类型")
    limit: int | None = Field(default=None, ge=1, le=10000, description="限制返回行数")


class QueryResult(BaseModel):
    """查询结果数据"""
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool = False


class QueryResponse(BaseModel):
    """查询成功响应"""
    success: bool = True
    sql: str | None = None
    result: QueryResult | None = None
    explanation: str | None = None


class SQLGenerationResult(BaseModel):
    """SQL 生成结果（内部使用）"""
    sql: str
    explanation: str | None = None
    tokens_used: int = 0


class SQLValidationResult(BaseModel):
    """SQL 验证结果（内部使用）"""
    is_valid: bool
    is_safe: bool  # 是否为只读查询
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)
```

### 3.4 错误模型

```python
# src/pg_mcp/models/errors.py

from enum import Enum
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """错误码"""
    UNKNOWN_DATABASE = "UNKNOWN_DATABASE"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    UNSAFE_SQL = "UNSAFE_SQL"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    OPENAI_ERROR = "OPENAI_ERROR"
    RESULT_TOO_LARGE = "RESULT_TOO_LARGE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"  # 速率限制超出
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: ErrorCode
    error_message: str
    details: dict | None = None  # 额外错误信息


class PgMcpError(Exception):
    """基础异常类"""
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.code,
            error_message=self.message,
            details=self.details
        )


class UnknownDatabaseError(PgMcpError):
    def __init__(self, database: str, available: list[str]):
        super().__init__(
            ErrorCode.UNKNOWN_DATABASE,
            f"Database '{database}' not found. Available: {', '.join(available)}",
            {"available_databases": available}
        )


class UnsafeSQLError(PgMcpError):
    def __init__(self, reason: str):
        super().__init__(
            ErrorCode.UNSAFE_SQL,
            f"Generated SQL is not safe for execution: {reason}"
        )


class SQLSyntaxError(PgMcpError):
    def __init__(self, sql: str, error: str):
        super().__init__(
            ErrorCode.SYNTAX_ERROR,
            f"SQL syntax error: {error}",
            {"sql": sql}
        )


class QueryTimeoutError(PgMcpError):
    def __init__(self, timeout: float):
        super().__init__(
            ErrorCode.EXECUTION_TIMEOUT,
            f"Query execution timed out after {timeout} seconds"
        )


class DatabaseConnectionError(PgMcpError):
    """数据库连接错误（避免与内置 ConnectionError 冲突）"""
    def __init__(self, database: str, error: str):
        super().__init__(
            ErrorCode.CONNECTION_ERROR,
            f"Failed to connect to database '{database}': {error}",
            {"database": database}
        )


class OpenAIError(PgMcpError):
    def __init__(self, error: str):
        super().__init__(
            ErrorCode.OPENAI_ERROR,
            f"OpenAI API error: {error}"
        )
```

---

## 4. 核心模块设计

### 4.1 数据库连接池 (DatabasePool)

```python
# src/pg_mcp/infrastructure/database.py

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from asyncpg import Pool, Connection

from pg_mcp.config.models import DatabaseConfig, SSLMode
from pg_mcp.models.errors import DatabaseConnectionError, UnknownDatabaseError


def _get_ssl_context(ssl_mode: SSLMode):
    """根据 SSL 模式创建 SSL 上下文"""
    import ssl
    if ssl_mode == SSLMode.DISABLE:
        return False
    if ssl_mode == SSLMode.REQUIRE:
        # 严格模式：验证证书
        ctx = ssl.create_default_context()
        return ctx
    # prefer/allow 模式：不验证证书
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class DatabasePool:
    """数据库连接池管理器"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Pool | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """初始化连接池"""
        async with self._lock:
            if self._pool is not None:
                return

            try:
                self._pool = await asyncpg.create_pool(
                    dsn=self.config.get_dsn(),
                    min_size=self.config.min_pool_size,
                    max_size=self.config.max_pool_size,
                    command_timeout=60,
                    # SSL 配置 - 使用正确的 SSLContext
                    ssl=_get_ssl_context(self.config.ssl_mode),
                )
            except Exception as e:
                raise DatabaseConnectionError(self.config.name, str(e))

    async def close(self) -> None:
        """关闭连接池"""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Connection]:
        """获取数据库连接"""
        if self._pool is None:
            await self.initialize()

        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args, timeout: float | None = None) -> str:
        """执行 SQL（无返回）"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def fetch(self, query: str, *args, timeout: float | None = None) -> list[asyncpg.Record]:
        """执行查询并返回结果"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchrow(self, query: str, *args, timeout: float | None = None) -> asyncpg.Record | None:
        """执行查询并返回单行"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def health_check(self) -> tuple[bool, str]:
        """
        健康检查 - 验证数据库连接是否正常

        Returns:
            tuple[bool, str]: (是否健康, 详细信息)
        """
        if self._pool is None:
            return False, "Pool not initialized"

        try:
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1", timeout=5.0)
                if result == 1:
                    return True, f"OK (pool_size={self._pool.get_size()}, free={self._pool.get_idle_size()})"
                return False, "Unexpected health check result"
        except Exception as e:
            return False, f"Health check failed: {e}"

    @property
    def pool_stats(self) -> dict:
        """获取连接池统计信息"""
        if self._pool is None:
            return {"status": "not_initialized"}
        return {
            "status": "active",
            "size": self._pool.get_size(),
            "idle": self._pool.get_idle_size(),
            "min_size": self._pool.get_min_size(),
            "max_size": self._pool.get_max_size(),
        }


class DatabasePoolManager:
    """多数据库连接池管理器"""

    def __init__(self):
        self._pools: dict[str, DatabasePool] = {}

    def add_database(self, config: DatabaseConfig) -> None:
        """添加数据库配置"""
        self._pools[config.name] = DatabasePool(config)

    async def initialize_all(self) -> None:
        """初始化所有连接池"""
        await asyncio.gather(*[pool.initialize() for pool in self._pools.values()])

    async def close_all(self) -> None:
        """关闭所有连接池"""
        await asyncio.gather(*[pool.close() for pool in self._pools.values()])

    def get_pool(self, name: str) -> DatabasePool:
        """获取指定数据库的连接池"""
        if name not in self._pools:
            raise UnknownDatabaseError(name, list(self._pools.keys()))
        return self._pools[name]

    def list_databases(self) -> list[str]:
        """列出所有数据库名称"""
        return list(self._pools.keys())

    def get_default_database(self) -> str | None:
        """获取默认数据库（仅当只有一个数据库时）"""
        if len(self._pools) == 1:
            return next(iter(self._pools.keys()))
        return None
```

### 4.2 Schema 缓存 (SchemaCache)

```python
# src/pg_mcp/infrastructure/schema_cache.py

import asyncio
import time
from typing import Callable, Awaitable

import structlog

from pg_mcp.models.schema import (
    DatabaseSchema, TableInfo, ViewInfo, ColumnInfo,
    IndexInfo, IndexType, EnumTypeInfo
)
from pg_mcp.infrastructure.database import DatabasePool

logger = structlog.get_logger()


# Schema 查询 SQL
TABLES_QUERY = """
SELECT
    c.relname AS table_name,
    n.nspname AS schema_name,
    obj_description(c.oid) AS comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n.nspname, c.relname;
"""

COLUMNS_QUERY = """
SELECT
    a.attname AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    NOT a.attnotnull AS is_nullable,
    COALESCE(
        (SELECT TRUE FROM pg_constraint pc
         WHERE pc.conrelid = c.oid AND pc.contype = 'p' AND a.attnum = ANY(pc.conkey)),
        FALSE
    ) AS is_primary_key,
    pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
    col_description(c.oid, a.attnum) AS comment,
    t.typtype AS type_type,
    t.typname AS type_name
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
JOIN pg_type t ON t.oid = a.atttypid
LEFT JOIN pg_attrdef ad ON ad.adrelid = c.oid AND ad.adnum = a.attnum
WHERE c.relname = $1
  AND n.nspname = $2
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;
"""

INDEXES_QUERY = """
SELECT
    i.relname AS index_name,
    am.amname AS index_type,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary,
    array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) AS columns
FROM pg_class t
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_index ix ON ix.indrelid = t.oid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_am am ON am.oid = i.relam
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE t.relname = $1
  AND n.nspname = $2
GROUP BY i.relname, am.amname, ix.indisunique, ix.indisprimary;
"""

FOREIGN_KEYS_QUERY = """
SELECT
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = $1
  AND tc.table_schema = $2;
"""

ENUM_TYPES_QUERY = """
SELECT
    t.typname AS type_name,
    n.nspname AS schema_name,
    array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
JOIN pg_enum e ON e.enumtypid = t.oid
WHERE t.typtype = 'e'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
GROUP BY t.typname, n.nspname;
"""

VIEWS_QUERY = """
SELECT
    c.relname AS view_name,
    n.nspname AS schema_name,
    pg_get_viewdef(c.oid) AS definition
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'v'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema');
"""


class SchemaCache:
    """单个数据库的 Schema 缓存"""

    def __init__(self, database_name: str, pool: DatabasePool):
        self.database_name = database_name
        self._pool = pool
        self._schema: DatabaseSchema | None = None
        self._lock = asyncio.Lock()

    async def load(self) -> DatabaseSchema:
        """加载数据库 Schema"""
        async with self._lock:
            log = logger.bind(database=self.database_name)
            log.info("Loading database schema")
            start_time = time.time()

            tables = await self._load_tables()
            views = await self._load_views()
            enum_types = await self._load_enum_types()

            self._schema = DatabaseSchema(
                name=self.database_name,
                tables=tables,
                views=views,
                enum_types=enum_types,
                cached_at=time.time()
            )

            duration = time.time() - start_time
            log.info(
                "Schema loaded",
                tables_count=len(tables),
                views_count=len(views),
                enum_types_count=len(enum_types),
                duration_ms=int(duration * 1000)
            )

            return self._schema

    async def get(self) -> DatabaseSchema:
        """获取缓存的 Schema"""
        if self._schema is None:
            await self.load()
        return self._schema

    async def refresh(self) -> DatabaseSchema:
        """强制刷新 Schema（使用原子交换避免竞态条件）"""
        async with self._lock:
            log = logger.bind(database=self.database_name)
            log.info("Refreshing database schema")
            start_time = time.time()

            # 加载新 schema（不清空旧的，避免并发请求看到 None）
            tables = await self._load_tables()
            views = await self._load_views()
            enum_types = await self._load_enum_types()

            new_schema = DatabaseSchema(
                name=self.database_name,
                tables=tables,
                views=views,
                enum_types=enum_types,
                cached_at=time.time()
            )

            # 原子交换 - 并发请求要么看到旧 schema，要么看到新 schema
            self._schema = new_schema

            duration = time.time() - start_time
            log.info(
                "Schema refreshed",
                tables_count=len(tables),
                duration_ms=int(duration * 1000)
            )

            return new_schema

    async def _load_tables(self) -> list[TableInfo]:
        """加载所有表信息"""
        tables = []
        rows = await self._pool.fetch(TABLES_QUERY)

        for row in rows:
            table_name = row["table_name"]
            schema_name = row["schema_name"]

            columns = await self._load_columns(table_name, schema_name)
            indexes = await self._load_indexes(table_name, schema_name)

            tables.append(TableInfo(
                name=table_name,
                schema_name=schema_name,
                columns=columns,
                indexes=indexes,
                comment=row["comment"]
            ))

        return tables

    async def _load_columns(self, table_name: str, schema_name: str) -> list[ColumnInfo]:
        """加载表的列信息"""
        columns = []

        # 获取列基本信息
        col_rows = await self._pool.fetch(COLUMNS_QUERY, table_name, schema_name)

        # 获取外键信息
        fk_rows = await self._pool.fetch(FOREIGN_KEYS_QUERY, table_name, schema_name)
        fk_map = {row["column_name"]: row for row in fk_rows}

        # 获取 ENUM 值（如果是 ENUM 类型）
        enum_cache = {}

        for row in col_rows:
            col = ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"],
                is_primary_key=row["is_primary_key"],
                default_value=row["default_value"],
                comment=row["comment"]
            )

            # 处理外键
            if row["column_name"] in fk_map:
                fk = fk_map[row["column_name"]]
                col.foreign_key_table = fk["foreign_table_name"]
                col.foreign_key_column = fk["foreign_column_name"]

            # 处理 ENUM 类型 - 使用 schema 限定名避免歧义
            if row["type_type"] == "e":
                type_name = row["type_name"]
                if type_name not in enum_cache:
                    # 使用 pg_type OID 查询，比 regtype 更可靠
                    enum_rows = await self._pool.fetch(
                        """SELECT e.enumlabel
                           FROM pg_enum e
                           JOIN pg_type t ON t.oid = e.enumtypid
                           WHERE t.typname = $1
                           ORDER BY e.enumsortorder""",
                        type_name
                    )
                    enum_cache[type_name] = [r["enumlabel"] for r in enum_rows]
                col.enum_values = enum_cache[type_name]

            columns.append(col)

        return columns

    async def _load_indexes(self, table_name: str, schema_name: str) -> list[IndexInfo]:
        """加载表的索引信息"""
        indexes = []
        rows = await self._pool.fetch(INDEXES_QUERY, table_name, schema_name)

        for row in rows:
            try:
                index_type = IndexType(row["index_type"])
            except ValueError:
                index_type = IndexType.BTREE

            indexes.append(IndexInfo(
                name=row["index_name"],
                columns=row["columns"],
                index_type=index_type,
                is_unique=row["is_unique"],
                is_primary=row["is_primary"]
            ))

        return indexes

    async def _load_views(self) -> list[ViewInfo]:
        """加载所有视图信息"""
        views = []
        rows = await self._pool.fetch(VIEWS_QUERY)

        for row in rows:
            view_name = row["view_name"]
            schema_name = row["schema_name"]

            # 加载视图的列信息（复用表的列查询逻辑）
            columns = await self._load_view_columns(view_name, schema_name)

            views.append(ViewInfo(
                name=view_name,
                schema_name=schema_name,
                columns=columns,
                definition=row["definition"]
            ))

        return views

    async def _load_view_columns(self, view_name: str, schema_name: str) -> list[ColumnInfo]:
        """加载视图的列信息"""
        columns = []
        # 视图列信息查询
        query = """
        SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            NOT a.attnotnull AS is_nullable
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE c.relname = $1
          AND n.nspname = $2
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum;
        """
        rows = await self._pool.fetch(query, view_name, schema_name)

        for row in rows:
            columns.append(ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"]
            ))

        return columns

    async def _load_enum_types(self) -> list[EnumTypeInfo]:
        """加载所有枚举类型"""
        enum_types = []
        rows = await self._pool.fetch(ENUM_TYPES_QUERY)

        for row in rows:
            enum_types.append(EnumTypeInfo(
                name=row["type_name"],
                schema_name=row["schema_name"],
                values=row["enum_values"]
            ))

        return enum_types


class SchemaCacheManager:
    """Schema 缓存管理器"""

    def __init__(self, pool_manager: DatabasePoolManager, refresh_interval: int = 3600):
        self._pool_manager = pool_manager
        self._refresh_interval = refresh_interval
        self._caches: dict[str, SchemaCache] = {}
        self._refresh_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """初始化所有数据库的 Schema 缓存"""
        for db_name in self._pool_manager.list_databases():
            pool = self._pool_manager.get_pool(db_name)
            cache = SchemaCache(db_name, pool)
            await cache.load()
            self._caches[db_name] = cache

        # 启动定时刷新任务
        self._refresh_task = asyncio.create_task(self._auto_refresh())

    async def close(self) -> None:
        """关闭缓存管理器"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def get_schema(self, database: str) -> DatabaseSchema:
        """获取指定数据库的 Schema"""
        if database not in self._caches:
            raise UnknownDatabaseError(database, list(self._caches.keys()))
        return await self._caches[database].get()

    async def refresh_schema(self, database: str | None = None) -> list[str]:
        """刷新 Schema 缓存"""
        refreshed = []

        if database:
            if database not in self._caches:
                raise UnknownDatabaseError(database, list(self._caches.keys()))
            await self._caches[database].refresh()
            refreshed.append(database)
        else:
            for name, cache in self._caches.items():
                await cache.refresh()
                refreshed.append(name)

        return refreshed

    def list_databases(self) -> list[tuple[str, int, int]]:
        """列出所有数据库及其表/视图数量"""
        result = []
        for name, cache in self._caches.items():
            schema = cache._schema
            if schema:
                result.append((name, schema.tables_count, schema.views_count))
            else:
                result.append((name, 0, 0))
        return result

    async def _auto_refresh(self) -> None:
        """定时刷新所有 Schema"""
        while True:
            await asyncio.sleep(self._refresh_interval)
            logger.info("Auto-refreshing all schemas")
            try:
                await self.refresh_schema()
            except Exception as e:
                logger.error("Failed to auto-refresh schemas", error=str(e))
```

### 4.3 SQL 解析与验证 (SQLParser)

```python
# src/pg_mcp/infrastructure/sql_parser.py

from typing import Set
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from pg_mcp.models.query import SQLValidationResult
from pg_mcp.models.errors import UnsafeSQLError, SQLSyntaxError


# 禁止的语句类型
FORBIDDEN_STATEMENT_TYPES: Set[type] = {
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Truncate,
    exp.Grant,
    exp.Command,  # 包括 COPY, VACUUM 等
}

# 禁止的危险函数
FORBIDDEN_FUNCTIONS: Set[str] = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_reload_conf",
    "pg_rotate_logfile",
    "lo_import",
    "lo_export",
    "lo_unlink",
    "dblink",
    "dblink_exec",
}

# 禁止的关键字（PostgreSQL 特定的危险模式）
FORBIDDEN_KEYWORDS: Set[str] = {
    "COPY TO",           # 文件导出
    "COPY FROM",         # 文件导入
    "PG_READ_FILE",      # 读取服务器文件
    "PG_WRITE_FILE",     # 写入服务器文件
    "PG_READ_BINARY_FILE",  # 读取二进制文件
}


class SQLParser:
    """SQL 解析与验证器"""

    def __init__(self, dialect: str = "postgres"):
        self.dialect = dialect

    def parse(self, sql: str) -> list[exp.Expression]:
        """解析 SQL 语句"""
        try:
            return sqlglot.parse(sql, dialect=self.dialect)
        except ParseError as e:
            raise SQLSyntaxError(sql, str(e))

    def validate(self, sql: str) -> SQLValidationResult:
        """验证 SQL 是否安全"""
        warnings = []

        # 1. 解析 SQL
        try:
            statements = self.parse(sql)
        except SQLSyntaxError as e:
            return SQLValidationResult(
                is_valid=False,
                is_safe=False,
                error_message=e.message
            )

        if not statements:
            return SQLValidationResult(
                is_valid=False,
                is_safe=False,
                error_message="No valid SQL statement found"
            )

        # 2. 检查 stacked queries（多语句攻击）
        valid_statements = [s for s in statements if s is not None]
        if len(valid_statements) > 1:
            return SQLValidationResult(
                is_valid=True,
                is_safe=False,
                error_message="Multiple statements (stacked queries) not allowed for security reasons"
            )

        # 3. 检查每个语句
        for stmt in statements:
            if stmt is None:
                continue

            # 2.1 检查语句类型
            if not self._is_select_statement(stmt):
                return SQLValidationResult(
                    is_valid=True,
                    is_safe=False,
                    error_message=f"Only SELECT statements are allowed, got {type(stmt).__name__}"
                )

            # 2.2 检查是否包含危险函数
            unsafe_funcs = self._find_forbidden_functions(stmt)
            if unsafe_funcs:
                return SQLValidationResult(
                    is_valid=True,
                    is_safe=False,
                    error_message=f"Forbidden functions found: {', '.join(unsafe_funcs)}"
                )

            # 2.3 检查 CTE 中是否有修改操作
            cte_issue = self._check_cte_safety(stmt)
            if cte_issue:
                return SQLValidationResult(
                    is_valid=True,
                    is_safe=False,
                    error_message=cte_issue
                )

            # 2.4 检查子查询
            subquery_issue = self._check_subqueries(stmt)
            if subquery_issue:
                return SQLValidationResult(
                    is_valid=True,
                    is_safe=False,
                    error_message=subquery_issue
                )

        # 3. 额外的文本检查（防止某些边界情况）
        sql_upper = sql.upper()
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return SQLValidationResult(
                    is_valid=True,
                    is_safe=False,
                    error_message=f"Forbidden keyword found: {keyword}"
                )

        return SQLValidationResult(
            is_valid=True,
            is_safe=True,
            warnings=warnings
        )

    def _is_select_statement(self, stmt: exp.Expression) -> bool:
        """检查是否为 SELECT 语句"""
        return isinstance(stmt, exp.Select)

    def _find_forbidden_functions(self, stmt: exp.Expression) -> list[str]:
        """查找禁止的函数调用"""
        found = []
        for func in stmt.find_all(exp.Func):
            func_name = func.name.lower() if hasattr(func, 'name') else ""
            if func_name in FORBIDDEN_FUNCTIONS:
                found.append(func_name)
        return found

    def _check_cte_safety(self, stmt: exp.Expression) -> str | None:
        """检查 CTE (WITH 子句) 安全性"""
        for cte in stmt.find_all(exp.CTE):
            # 检查 CTE 内部是否有非 SELECT 语句
            for child in cte.walk():
                if isinstance(child, tuple(FORBIDDEN_STATEMENT_TYPES)):
                    return f"CTE contains forbidden statement type: {type(child).__name__}"
        return None

    def _check_subqueries(self, stmt: exp.Expression) -> str | None:
        """检查所有子查询是否安全"""
        for subquery in stmt.find_all(exp.Subquery):
            for child in subquery.walk():
                if isinstance(child, tuple(FORBIDDEN_STATEMENT_TYPES)):
                    return f"Subquery contains forbidden statement type: {type(child).__name__}"
        return None

    def add_limit(self, sql: str, limit: int) -> str:
        """为 SQL 添加或修改 LIMIT"""
        try:
            statements = self.parse(sql)
            if not statements or not isinstance(statements[0], exp.Select):
                return sql

            stmt = statements[0]

            # 检查是否已有 LIMIT
            existing_limit = stmt.find(exp.Limit)
            if existing_limit:
                # 如果现有 LIMIT 大于指定值，则修改
                try:
                    existing_value = int(existing_limit.expression.this)
                    if existing_value > limit:
                        stmt = stmt.limit(limit)
                except (ValueError, AttributeError):
                    pass
            else:
                stmt = stmt.limit(limit)

            return stmt.sql(dialect=self.dialect)
        except Exception:
            # 解析失败时返回原 SQL
            return sql

    def format_sql(self, sql: str) -> str:
        """格式化 SQL"""
        try:
            return sqlglot.transpile(sql, read=self.dialect, write=self.dialect, pretty=True)[0]
        except Exception:
            return sql
```

### 4.4 OpenAI 客户端封装

```python
# src/pg_mcp/infrastructure/openai_client.py

import asyncio
from typing import AsyncIterator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
import structlog

from pg_mcp.config.models import OpenAIConfig
from pg_mcp.models.query import SQLGenerationResult
from pg_mcp.models.schema import DatabaseSchema
from pg_mcp.models.errors import OpenAIError

logger = structlog.get_logger()


SYSTEM_PROMPT = """你是一个 PostgreSQL SQL 生成专家。你的任务是根据用户的自然语言需求生成安全、高效的 SQL 查询语句。

## 规则
1. **仅生成 SELECT 语句**，禁止任何修改数据的操作（INSERT、UPDATE、DELETE、DROP 等）
2. 使用标准 PostgreSQL 语法
3. 优先使用已有索引的列进行过滤和排序
4. 对于可能返回大量数据的查询，建议添加 LIMIT
5. 使用有意义的列别名提高可读性
6. 正确处理 NULL 值比较（使用 IS NULL / IS NOT NULL）

## 输出格式
直接返回 SQL 语句，不要包含 markdown 代码块或其他说明文字。
"""


def build_user_prompt(question: str, schema: DatabaseSchema) -> str:
    """构建用户 Prompt"""
    return f"""## 数据库 Schema

{schema.to_prompt_text()}

## 用户需求
{question}

请生成 SQL 查询语句。"""


class OpenAIClient:
    """OpenAI API 客户端封装"""

    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            max_retries=config.max_retries,
            timeout=config.timeout
        )

    async def generate_sql(
        self,
        question: str,
        schema: DatabaseSchema,
    ) -> SQLGenerationResult:
        """生成 SQL 语句"""
        log = logger.bind(question=question[:100], database=schema.name)
        log.info("Generating SQL via OpenAI")

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(question, schema)}
                ],
                temperature=0.1,  # 低温度以获得更确定性的输出
                max_tokens=2000,
            )

            sql = self._extract_sql(response)
            tokens_used = response.usage.total_tokens if response.usage else 0

            log.info("SQL generated", sql_length=len(sql), tokens=tokens_used)

            return SQLGenerationResult(
                sql=sql,
                tokens_used=tokens_used
            )

        except Exception as e:
            log.error("OpenAI API error", error=str(e))
            raise OpenAIError(str(e))

    async def validate_result(
        self,
        question: str,
        sql: str,
        sample_rows: list[list],
        columns: list[str]
    ) -> tuple[bool, str]:
        """验证查询结果是否符合用户意图"""
        # 构建验证 prompt
        result_preview = self._format_result_preview(columns, sample_rows)

        prompt = f"""用户需求: {question}
生成的 SQL: {sql}
查询结果 (前 5 行):
{result_preview}

请判断:
1. SQL 是否正确理解了用户意图？
2. 返回的结果是否符合预期？

只返回 JSON: {{"valid": true/false, "reason": "简短说明"}}"""

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200,
            )

            content = response.choices[0].message.content or ""
            # 简单解析 JSON
            import json
            result = json.loads(content)
            return result.get("valid", True), result.get("reason", "")

        except Exception as e:
            logger.warning("Result validation failed", error=str(e))
            return True, "Validation skipped due to error"

    def _extract_sql(self, response: ChatCompletion) -> str:
        """从响应中提取 SQL"""
        content = response.choices[0].message.content or ""

        # 移除可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```sql"):
            content = content[6:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _format_result_preview(self, columns: list[str], rows: list[list]) -> str:
        """格式化结果预览"""
        if not rows:
            return "(无数据)"

        lines = [" | ".join(columns)]
        lines.append("-" * 40)
        for row in rows[:5]:
            lines.append(" | ".join(str(v) for v in row))

        return "\n".join(lines)
```

### 4.5 速率限制器 (RateLimiter)

```python
# src/pg_mcp/infrastructure/rate_limiter.py

import asyncio
import time
from collections import deque
from typing import Deque

from pg_mcp.config.models import RateLimitConfig
from pg_mcp.models.errors import PgMcpError, ErrorCode


class RateLimitExceededError(PgMcpError):
    """速率限制超出异常"""
    def __init__(self, limit_type: str, retry_after: float):
        super().__init__(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded: {limit_type}. Retry after {retry_after:.1f} seconds.",
            {"limit_type": limit_type, "retry_after": retry_after}
        )


class SlidingWindowCounter:
    """滑动窗口计数器实现"""

    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._timestamps: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """尝试获取一个请求配额，返回是否成功"""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # 移除窗口外的旧时间戳
            while self._timestamps and self._timestamps[0] < window_start:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                return False

            self._timestamps.append(now)
            return True

    async def get_retry_after(self) -> float:
        """获取需要等待的时间（秒）"""
        async with self._lock:
            if not self._timestamps:
                return 0.0
            oldest = self._timestamps[0]
            return max(0.0, oldest + self.window_seconds - time.time())

    @property
    def current_count(self) -> int:
        """当前窗口内的请求数"""
        now = time.time()
        window_start = now - self.window_seconds
        return sum(1 for ts in self._timestamps if ts >= window_start)


class RateLimiter:
    """速率限制器 - 支持多种限制策略"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._enabled = config.enabled

        # 创建滑动窗口计数器
        self._per_minute = SlidingWindowCounter(60, config.requests_per_minute)
        self._per_hour = SlidingWindowCounter(3600, config.requests_per_hour)
        self._tokens_per_minute = SlidingWindowCounter(60, config.openai_tokens_per_minute)

    async def check_request_limit(self) -> None:
        """检查请求速率限制，超出时抛出异常"""
        if not self._enabled:
            return

        # 检查每分钟限制
        if not await self._per_minute.acquire():
            retry_after = await self._per_minute.get_retry_after()
            raise RateLimitExceededError("requests_per_minute", retry_after)

        # 检查每小时限制
        if not await self._per_hour.acquire():
            retry_after = await self._per_hour.get_retry_after()
            raise RateLimitExceededError("requests_per_hour", retry_after)

    async def check_token_limit(self, tokens: int) -> None:
        """检查 token 使用限制"""
        if not self._enabled:
            return

        # 简化实现：每个 token 算一次
        for _ in range(tokens):
            if not await self._tokens_per_minute.acquire():
                retry_after = await self._tokens_per_minute.get_retry_after()
                raise RateLimitExceededError("openai_tokens_per_minute", retry_after)

    def get_status(self) -> dict:
        """获取当前速率限制状态"""
        return {
            "enabled": self._enabled,
            "requests_per_minute": {
                "current": self._per_minute.current_count,
                "limit": self.config.requests_per_minute,
            },
            "requests_per_hour": {
                "current": self._per_hour.current_count,
                "limit": self.config.requests_per_hour,
            },
        }
```

### 4.6 查询服务 (QueryService)

```python
# src/pg_mcp/services/query_service.py

import asyncio
import time
from typing import Any

import structlog
from asyncpg import PostgresError

from pg_mcp.config.models import ServerConfig
from pg_mcp.models.query import (
    QueryRequest, QueryResponse, QueryResult,
    ReturnType, SQLGenerationResult, SQLValidationResult
)
from pg_mcp.models.errors import (
    PgMcpError, ErrorCode, SQLSyntaxError,
    QueryTimeoutError, UnsafeSQLError, UnknownDatabaseError
)
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.schema_cache import SchemaCacheManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.infrastructure.openai_client import OpenAIClient

logger = structlog.get_logger()


class QueryService:
    """查询服务 - 核心业务逻辑"""

    def __init__(
        self,
        config: ServerConfig,
        pool_manager: DatabasePoolManager,
        schema_manager: SchemaCacheManager,
        sql_parser: SQLParser,
        openai_client: OpenAIClient,
    ):
        self.config = config
        self._pool_manager = pool_manager
        self._schema_manager = schema_manager
        self._sql_parser = sql_parser
        self._openai = openai_client

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """执行自然语言查询"""
        log = logger.bind(
            question=request.question[:100],
            database=request.database,
            return_type=request.return_type.value
        )
        log.info("Processing query request")
        start_time = time.time()

        try:
            # 1. 确定目标数据库
            database = self._resolve_database(request.database)
            log = log.bind(resolved_database=database)

            # 2. 获取 Schema
            schema = await self._schema_manager.get_schema(database)

            # 3. 生成 SQL（带重试）
            sql = await self._generate_sql_with_retry(
                request.question, schema, database
            )
            log.info("SQL generated", sql=sql[:200])

            # 4. 如果只需要 SQL，直接返回
            if request.return_type == ReturnType.SQL:
                return QueryResponse(sql=sql)

            # 5. 执行查询
            limit = request.limit or self.config.max_result_rows
            result = await self._execute_sql(database, sql, limit)

            # 6. 可选：验证结果
            if self.config.enable_result_validation and result.rows:
                is_valid, reason = await self._openai.validate_result(
                    request.question,
                    sql,
                    result.rows[:5],
                    result.columns
                )
                if not is_valid:
                    log.warning("Result validation failed", reason=reason)

            # 7. 构建响应
            duration = time.time() - start_time
            log.info("Query completed", duration_ms=int(duration * 1000), row_count=result.row_count)

            if request.return_type == ReturnType.BOTH:
                return QueryResponse(sql=sql, result=result)
            else:
                return QueryResponse(result=result)

        except PgMcpError:
            raise
        except Exception as e:
            log.exception("Unexpected error in query execution")
            raise PgMcpError(ErrorCode.INTERNAL_ERROR, str(e))

    def _resolve_database(self, database: str | None) -> str:
        """解析目标数据库"""
        if database:
            if database not in self._pool_manager.list_databases():
                raise UnknownDatabaseError(database, self._pool_manager.list_databases())
            return database

        # 如果未指定，尝试使用默认数据库
        default = self._pool_manager.get_default_database()
        if default:
            return default

        raise PgMcpError(
            ErrorCode.AMBIGUOUS_QUERY,
            "Multiple databases available. Please specify 'database' parameter.",
            {"available_databases": self._pool_manager.list_databases()}
        )

    async def _generate_sql_with_retry(
        self,
        question: str,
        schema,
        database: str
    ) -> str:
        """生成 SQL，失败时重试"""
        last_error = None

        for attempt in range(self.config.max_sql_retry + 1):
            # 生成 SQL
            result = await self._openai.generate_sql(question, schema)
            sql = result.sql

            # 验证 SQL
            validation = self._sql_parser.validate(sql)

            if not validation.is_valid:
                last_error = validation.error_message
                logger.warning(
                    "SQL syntax error, retrying",
                    attempt=attempt + 1,
                    error=last_error
                )
                continue

            if not validation.is_safe:
                raise UnsafeSQLError(validation.error_message or "Unknown safety issue")

            # 通过语法验证 - 使用 EXPLAIN 进行进一步验证（在只读事务中）
            try:
                pool = self._pool_manager.get_pool(database)
                async with pool.acquire() as conn:
                    # 使用只读事务确保 EXPLAIN 不会产生任何副作用
                    async with conn.transaction(readonly=True):
                        await conn.execute(f"EXPLAIN {sql}")
                return sql
            except PostgresError as e:
                last_error = str(e)
                logger.warning(
                    "SQL EXPLAIN failed, retrying",
                    attempt=attempt + 1,
                    error=last_error
                )
                continue

        raise SQLSyntaxError("", last_error or "Failed to generate valid SQL")

    async def _execute_sql(
        self,
        database: str,
        sql: str,
        limit: int
    ) -> QueryResult:
        """执行 SQL 并返回结果"""
        pool = self._pool_manager.get_pool(database)

        # 添加 LIMIT（如果需要）
        sql_with_limit = self._sql_parser.add_limit(sql, limit + 1)  # +1 用于检测截断

        try:
            rows = await asyncio.wait_for(
                pool.fetch(sql_with_limit),
                timeout=self.config.query_timeout
            )
        except asyncio.TimeoutError:
            raise QueryTimeoutError(self.config.query_timeout)
        except PostgresError as e:
            raise PgMcpError(ErrorCode.SYNTAX_ERROR, str(e))

        # 处理结果
        if not rows:
            return QueryResult(columns=[], rows=[], row_count=0)

        columns = list(rows[0].keys())
        truncated = len(rows) > limit
        result_rows = [list(row.values()) for row in rows[:limit]]

        # 处理特殊类型（如 datetime）
        result_rows = self._serialize_rows(result_rows)

        return QueryResult(
            columns=columns,
            rows=result_rows,
            row_count=len(result_rows),
            truncated=truncated
        )

    def _serialize_rows(self, rows: list[list[Any]]) -> list[list[Any]]:
        """序列化行数据，处理特殊类型"""
        import datetime
        from decimal import Decimal

        def serialize_value(v):
            if v is None:
                return None
            if isinstance(v, datetime.datetime):
                return v.isoformat()
            if isinstance(v, datetime.date):
                return v.isoformat()
            if isinstance(v, Decimal):
                return float(v)
            if isinstance(v, bytes):
                return v.hex()
            return v

        return [[serialize_value(v) for v in row] for row in rows]
```

---

## 5. MCP 服务器实现

### 5.1 FastMCP 服务器

```python
# src/pg_mcp/server.py

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from fastmcp import FastMCP
from fastmcp.resources import Resource
from pydantic import Field

from pg_mcp.config.loader import load_config
from pg_mcp.config.models import AppConfig
from pg_mcp.models.query import QueryRequest, QueryResponse, ReturnType
from pg_mcp.models.errors import PgMcpError, ErrorResponse
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.schema_cache import SchemaCacheManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.infrastructure.openai_client import OpenAIClient
from pg_mcp.services.query_service import QueryService


@dataclass
class AppContext:
    """应用上下文容器 - 依赖注入模式，避免全局变量"""
    pool_manager: DatabasePoolManager
    schema_manager: SchemaCacheManager
    query_service: QueryService


# 使用单例上下文替代多个全局变量
_context: AppContext | None = None


def get_context() -> AppContext:
    """获取应用上下文，未初始化时抛出异常"""
    if _context is None:
        raise RuntimeError("Server not initialized. Lifespan not started.")
    return _context


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    """应用生命周期管理"""
    global _context

    # 加载配置
    config = load_config()

    # 初始化数据库连接池
    pool_manager = DatabasePoolManager()
    schema_manager: SchemaCacheManager | None = None

    try:
        for db_config in config.databases:
            pool_manager.add_database(db_config)
        await pool_manager.initialize_all()

        # 初始化 Schema 缓存
        schema_manager = SchemaCacheManager(
            pool_manager,
            refresh_interval=config.server.cache_refresh_interval
        )
        await schema_manager.initialize()

        # 初始化其他组件
        sql_parser = SQLParser()
        openai_client = OpenAIClient(config.openai)

        # 初始化查询服务
        query_service = QueryService(
            config=config.server,
            pool_manager=pool_manager,
            schema_manager=schema_manager,
            sql_parser=sql_parser,
            openai_client=openai_client
        )

        # 创建应用上下文
        _context = AppContext(
            pool_manager=pool_manager,
            schema_manager=schema_manager,
            query_service=query_service
        )

    except Exception:
        # 初始化失败时确保清理已创建的资源
        if schema_manager:
            await schema_manager.close()
        await pool_manager.close_all()
        raise

    yield

    # 正常关闭时清理资源
    await schema_manager.close()
    await pool_manager.close_all()
    _context = None


# 创建 FastMCP 应用
mcp = FastMCP(
    "PostgreSQL Query Assistant",
    description="A natural language interface for querying PostgreSQL databases",
    lifespan=lifespan
)


# ============== Resources ==============

@mcp.resource("databases://list")
async def list_databases() -> str:
    """List all available databases configured in this MCP server."""
    try:
        ctx = get_context()
    except RuntimeError as e:
        return str(e)

    databases = ctx.schema_manager.list_databases()

    lines = ["Available Databases:"]
    for name, tables_count, views_count in databases:
        lines.append(f"- {name} ({tables_count} tables, {views_count} views)")

    return "\n".join(lines)


@mcp.resource("schema://{database}")
async def get_schema(database: str) -> str:
    """Get the complete schema information for a specific database."""
    try:
        ctx = get_context()
        schema = await ctx.schema_manager.get_schema(database)
        return schema.to_prompt_text()
    except RuntimeError as e:
        return str(e)
    except PgMcpError as e:
        return f"Error: {e.message}"


# ============== Tools ==============

@mcp.tool()
async def query(
    question: str = Field(..., description="Natural language query describing what data you want to retrieve"),
    database: str | None = Field(None, description="Target database name. Required if multiple databases are configured"),
    return_type: str = Field("result", description="What to return: 'sql' for SQL only, 'result' for data only, 'both' for both"),
    limit: int | None = Field(None, description="Maximum number of rows to return", ge=1, le=10000)
) -> dict:
    """
    Execute a natural language query against a PostgreSQL database.

    This tool converts your natural language question into SQL, validates it for safety,
    executes it, and returns the results. Only SELECT queries are allowed.

    Examples:
    - "Show me the top 10 users by order count"
    - "What's the average order value per month in 2024?"
    - "Find all products that have never been ordered"
    """
    try:
        ctx = get_context()
    except RuntimeError:
        return {"success": False, "error_code": "INTERNAL_ERROR", "error_message": "Server not initialized"}

    try:
        # 解析 return_type
        try:
            rt = ReturnType(return_type.lower())
        except ValueError:
            rt = ReturnType.RESULT

        request = QueryRequest(
            question=question,
            database=database,
            return_type=rt,
            limit=limit
        )

        response = await ctx.query_service.execute_query(request)
        return response.model_dump(exclude_none=True)

    except PgMcpError as e:
        return e.to_response().model_dump()
    except Exception as e:
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": str(e)
        }


# ============== Entry Point ==============

def main():
    """主入口点"""
    import asyncio
    mcp.run()


if __name__ == "__main__":
    main()
```

### 5.2 配置加载器

```python
# src/pg_mcp/config/loader.py
"""配置加载器 - 从环境变量加载配置"""

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    DatabaseSettings,
    OpenAISettings,
    RateLimitSettings,
    ServerSettings,
)


def load_config() -> AppConfig:
    """从环境变量加载配置

    使用 pydantic-settings 直接从环境变量读取配置:
    - PG_MCP_DATABASE_*: 数据库配置
    - PG_MCP_OPENAI_*: OpenAI 配置
    - PG_MCP_SERVER_*: 服务器配置
    - PG_MCP_RATE_LIMIT_*: 速率限制配置

    Returns:
        AppConfig: 完整应用配置

    Raises:
        ValidationError: 必需环境变量缺失或无效
    """
    database_settings = DatabaseSettings()
    openai_settings = OpenAISettings()
    server_settings = ServerSettings()
    rate_limit_settings = RateLimitSettings()

    # 转换为 DatabaseConfig
    database_config = DatabaseConfig(
        name=database_settings.name,
        host=database_settings.host,
        port=database_settings.port,
        dbname=database_settings.dbname,
        user=database_settings.user,
        password=database_settings.password,
        url=database_settings.url,
        ssl_mode=database_settings.ssl_mode,
        min_pool_size=database_settings.min_pool_size,
        max_pool_size=database_settings.max_pool_size,
    )

    return AppConfig(
        databases=[database_config],
        openai=openai_settings,
        server=server_settings,
        rate_limit=rate_limit_settings,
    )
```

---

## 6. 关键流程时序图

### 6.1 查询执行流程

```
┌────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌────────┐     ┌────────────┐
│MCP     │     │FastMCP  │     │QueryService │     │OpenAI    │     │SQLParser│    │DatabasePool│
│Client  │     │Server   │     │             │     │Client    │     │         │    │            │
└───┬────┘     └────┬────┘     └──────┬──────┘     └────┬─────┘     └────┬────┘    └─────┬──────┘
    │               │                 │                 │                │               │
    │ query(question, database)       │                 │                │               │
    │──────────────>│                 │                 │                │               │
    │               │                 │                 │                │               │
    │               │ execute_query(request)            │                │               │
    │               │────────────────>│                 │                │               │
    │               │                 │                 │                │               │
    │               │                 │ get_schema(db)  │                │               │
    │               │                 │─────────────────────────────────────────────────>│
    │               │                 │<─────────────────────────────────────────────────│
    │               │                 │    schema       │                │               │
    │               │                 │                 │                │               │
    │               │                 │ generate_sql(question, schema)   │               │
    │               │                 │────────────────>│                │               │
    │               │                 │<────────────────│                │               │
    │               │                 │    sql          │                │               │
    │               │                 │                 │                │               │
    │               │                 │ validate(sql)   │                │               │
    │               │                 │─────────────────────────────────>│               │
    │               │                 │<─────────────────────────────────│               │
    │               │                 │   validation_result              │               │
    │               │                 │                 │                │               │
    │               │                 │                 │   [if unsafe]  │               │
    │               │                 │ UnsafeSQLError  │                │               │
    │               │                 │X                │                │               │
    │               │                 │                 │                │               │
    │               │                 │                 │   [if valid]   │               │
    │               │                 │ EXPLAIN sql     │                │               │
    │               │                 │─────────────────────────────────────────────────>│
    │               │                 │<─────────────────────────────────────────────────│
    │               │                 │                 │                │               │
    │               │                 │ execute sql     │                │               │
    │               │                 │─────────────────────────────────────────────────>│
    │               │                 │<─────────────────────────────────────────────────│
    │               │                 │    rows         │                │               │
    │               │                 │                 │                │               │
    │               │<────────────────│                 │                │               │
    │               │  QueryResponse  │                 │                │               │
    │<──────────────│                 │                 │                │               │
    │   result      │                 │                 │                │               │
```

### 6.2 服务器启动流程

```
┌──────────┐     ┌───────────┐     ┌────────────────┐     ┌─────────────┐     ┌─────────────┐
│  main()  │     │ FastMCP   │     │DatabasePoolMgr │     │SchemaCacheMgr│    │  PostgreSQL │
└────┬─────┘     └─────┬─────┘     └───────┬────────┘     └──────┬──────┘     └──────┬──────┘
     │                 │                   │                     │                   │
     │  mcp.run()      │                   │                     │                   │
     │────────────────>│                   │                     │                   │
     │                 │                   │                     │                   │
     │                 │ lifespan()        │                     │                   │
     │                 │───────┐           │                     │                   │
     │                 │       │           │                     │                   │
     │                 │<──────┘           │                     │                   │
     │                 │                   │                     │                   │
     │                 │ add_database()    │                     │                   │
     │                 │──────────────────>│                     │                   │
     │                 │                   │                     │                   │
     │                 │ initialize_all()  │                     │                   │
     │                 │──────────────────>│                     │                   │
     │                 │                   │                     │                   │
     │                 │                   │ create_pool()       │                   │
     │                 │                   │──────────────────────────────────────────>
     │                 │                   │<──────────────────────────────────────────
     │                 │                   │    pool             │                   │
     │                 │<──────────────────│                     │                   │
     │                 │                   │                     │                   │
     │                 │ initialize()      │                     │                   │
     │                 │────────────────────────────────────────>│                   │
     │                 │                   │                     │                   │
     │                 │                   │                     │ load_schema()     │
     │                 │                   │                     │──────────────────>│
     │                 │                   │                     │<──────────────────│
     │                 │                   │                     │    metadata       │
     │                 │<────────────────────────────────────────│                   │
     │                 │                   │                     │                   │
     │                 │ [Server Ready - Accepting Connections]  │                   │
     │<────────────────│                   │                     │                   │
```

---

## 7. 错误处理策略

### 7.1 异常类层次结构

```
Exception
└── PgMcpError (base)
    ├── UnknownDatabaseError      # 数据库不存在
    ├── UnsafeSQLError           # SQL 不安全
    ├── SQLSyntaxError           # SQL 语法错误
    ├── QueryTimeoutError        # 查询超时
    ├── DatabaseConnectionError   # 数据库连接错误（注意：避免与内置 ConnectionError 冲突）
    └── OpenAIError              # OpenAI API 错误
```

### 7.2 错误处理流程

```python
# 在 MCP Tool 中的错误处理
@mcp.tool()
async def query(...) -> dict:
    try:
        response = await _query_service.execute_query(request)
        return response.model_dump(exclude_none=True)

    except PgMcpError as e:
        # 业务错误 - 返回结构化错误响应
        return e.to_response().model_dump()

    except Exception as e:
        # 未预期错误 - 记录日志并返回通用错误
        logger.exception("Unexpected error")
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": str(e)
        }
```

### 7.3 重试策略

| 场景 | 重试策略 |
|------|---------|
| SQL 语法错误 | 最多重试 2 次，每次让 LLM 重新生成 |
| OpenAI API 错误 | 指数退避重试，最多 3 次 |
| 数据库连接错误 | 自动重连，连接池管理 |
| 查询超时 | 不重试，直接返回错误 |

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/unit/test_sql_parser.py

import pytest
from pg_mcp.infrastructure.sql_parser import SQLParser


class TestSQLParser:
    @pytest.fixture
    def parser(self):
        return SQLParser()

    def test_valid_select(self, parser):
        result = parser.validate("SELECT * FROM users")
        assert result.is_valid
        assert result.is_safe

    def test_reject_insert(self, parser):
        result = parser.validate("INSERT INTO users VALUES (1)")
        assert result.is_valid  # 语法正确
        assert not result.is_safe  # 但不安全

    def test_reject_delete(self, parser):
        result = parser.validate("DELETE FROM users WHERE id = 1")
        assert not result.is_safe

    def test_reject_pg_sleep(self, parser):
        result = parser.validate("SELECT pg_sleep(10)")
        assert not result.is_safe
        assert "pg_sleep" in result.error_message

    def test_cte_with_select(self, parser):
        sql = """
        WITH active_users AS (
            SELECT * FROM users WHERE status = 'active'
        )
        SELECT * FROM active_users
        """
        result = parser.validate(sql)
        assert result.is_safe

    def test_cte_with_delete(self, parser):
        sql = """
        WITH deleted AS (
            DELETE FROM users WHERE id = 1 RETURNING *
        )
        SELECT * FROM deleted
        """
        result = parser.validate(sql)
        assert not result.is_safe

    def test_add_limit(self, parser):
        sql = "SELECT * FROM users"
        result = parser.add_limit(sql, 100)
        assert "LIMIT 100" in result.upper()

    def test_preserve_smaller_limit(self, parser):
        sql = "SELECT * FROM users LIMIT 10"
        result = parser.add_limit(sql, 100)
        assert "LIMIT 10" in result.upper()
```

### 8.2 集成测试

```python
# tests/integration/test_query_flow.py

import pytest
from unittest.mock import AsyncMock, patch

from pg_mcp.services.query_service import QueryService
from pg_mcp.models.query import QueryRequest, ReturnType


@pytest.fixture
def mock_openai_response():
    return "SELECT id, name, email FROM users WHERE status = 'active' LIMIT 10"


@pytest.fixture
async def query_service(mock_openai_response):
    # 使用 mock 对象创建服务
    with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
        # 配置 mock
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=MockChatCompletion(mock_openai_response)
        )

        # ... 初始化其他组件
        yield service


class TestQueryFlow:
    @pytest.mark.asyncio
    async def test_simple_query(self, query_service):
        request = QueryRequest(
            question="Show me all active users",
            return_type=ReturnType.BOTH
        )

        response = await query_service.execute_query(request)

        assert response.success
        assert response.sql is not None
        assert "SELECT" in response.sql

    @pytest.mark.asyncio
    async def test_unsafe_sql_rejected(self, query_service):
        # 模拟 LLM 返回不安全的 SQL
        with patch.object(query_service._openai, "generate_sql") as mock:
            mock.return_value.sql = "DELETE FROM users"

            request = QueryRequest(question="Delete all users")

            with pytest.raises(UnsafeSQLError):
                await query_service.execute_query(request)
```

### 8.3 测试覆盖目标

| 模块 | 目标覆盖率 |
|------|-----------|
| sql_parser | >= 95% |
| query_service | >= 90% |
| schema_cache | >= 85% |
| config | >= 90% |
| 总体 | >= 85% |

---

## 9. 部署配置

### 9.1 环境变量配置示例

```bash
# .env.example - 复制为 .env 并配置

# 数据库配置 (必需)
PG_MCP_DATABASE_NAME=production
PG_MCP_DATABASE_HOST=localhost
PG_MCP_DATABASE_PORT=5432
PG_MCP_DATABASE_DBNAME=mydb
PG_MCP_DATABASE_USER=postgres
PG_MCP_DATABASE_PASSWORD=your_password
PG_MCP_DATABASE_SSL_MODE=prefer

# 或使用连接字符串
# PG_MCP_DATABASE_URL=postgresql://user:pass@host:5432/db

# OpenAI 配置 (必需)
PG_MCP_OPENAI_API_KEY=sk-your-api-key
PG_MCP_OPENAI_MODEL=gpt-4o-mini
PG_MCP_OPENAI_TIMEOUT=30.0

# 服务器配置 (可选)
PG_MCP_SERVER_CACHE_REFRESH_INTERVAL=3600
PG_MCP_SERVER_MAX_RESULT_ROWS=1000
PG_MCP_SERVER_QUERY_TIMEOUT=30.0
PG_MCP_SERVER_USE_READONLY_TRANSACTIONS=true

# 速率限制 (可选)
PG_MCP_RATE_LIMIT_ENABLED=true
PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE=60
PG_MCP_RATE_LIMIT_REQUESTS_PER_HOUR=1000
```

### 9.2 Docker 配置

```dockerfile
# Dockerfile

FROM python:3.13.5-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# 复制源代码
COPY src/ ./src/

# 设置环境变量
ENV PYTHONPATH=/app/src

# 入口点
ENTRYPOINT ["python", "-m", "pg_mcp"]
```

### 9.3 MCP 客户端配置

```json
// Claude Desktop 配置示例
{
  "mcpServers": {
    "pg-query": {
      "command": "python",
      "args": ["-m", "pg_mcp"],
      "env": {
        "PG_MCP_OPENAI_API_KEY": "sk-your-api-key",
        "PG_MCP_DATABASE_HOST": "localhost",
        "PG_MCP_DATABASE_PORT": "5432",
        "PG_MCP_DATABASE_DBNAME": "your_database",
        "PG_MCP_DATABASE_USER": "postgres",
        "PG_MCP_DATABASE_PASSWORD": "your_password"
      }
    }
  }
}
```

---

## 10. 依赖管理

### 10.1 pyproject.toml

```toml
[project]
name = "pg-mcp"
version = "0.1.0"
description = "PostgreSQL MCP Server with natural language query support"
requires-python = ">=3.13"
dependencies = [
    "fastmcp>=0.1.0",
    "asyncpg>=0.29.0",
    "sqlglot>=26.0.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "openai>=1.60.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.14.0",
]

[project.scripts]
pg-mcp = "pg_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.mypy]
python_version = "3.13"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## 11. 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-10 | 初始设计文档 | - |
| 1.1 | 2026-01-10 | Code Review 修复: (1) 将 ConnectionError 重命名为 DatabaseConnectionError 避免与内置异常冲突; (2) 修复 SSL 配置使用 SSLContext; (3) 改进全局变量为 AppContext 依赖注入模式; (4) 修复 ENUM 类型查询使用 OID; (5) 添加 View 列信息加载; (6) 添加连接池健康检查功能 | Claude |
| 1.2 | 2026-01-10 | Codex Review 修复: (1) 修复 SQL EXPLAIN 注入风险，使用只读事务; (2) 将 FORBIDDEN_KEYWORDS 从 MySQL 改为 PostgreSQL 特定关键字; (3) 添加 stacked queries（多语句）攻击检测; (4) 修复 Schema 缓存刷新竞态条件，使用原子交换; (5) 添加初始化失败时的资源清理; (6) 新增速率限制器设计（RateLimiter）及配置 | Claude |
| 1.3 | 2026-01-10 | 明确使用 uv 作为唯一的 Python 环境管理工具（移除 poetry 备选） | Claude |
