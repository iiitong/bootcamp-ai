# PostgreSQL MCP Server 实现计划

**版本**: 2.0
**日期**: 2026-01-10
**状态**: 已审核
**关联设计文档**: [0002-pg-mcp-design.md](./0002-pg-mcp-design.md)

---

## 1. 实现概述

### 1.1 目标

基于设计文档 `0002-pg-mcp-design.md`，实现一个功能完整的 PostgreSQL MCP Server，支持通过自然语言查询 PostgreSQL 数据库。

### 1.2 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.13.5 | 运行时 |
| uv | latest | Python 环境与依赖管理 |
| FastMCP | latest | MCP 服务器框架 |
| asyncpg | ^0.29.0 | PostgreSQL 异步驱动 |
| sqlglot | ^26.0 | SQL 解析与验证 |
| Pydantic | ^2.10 | 数据模型与验证 |
| pydantic-settings | ^2.7 | 环境变量配置管理 |
| openai | ^1.60 | OpenAI API 客户端 |
| structlog | ^24.0 | 结构化日志 |

### 1.3 环境管理 (uv)

本项目使用 **uv** 作为唯一的 Python 环境和依赖管理工具。

**为什么选择 uv**:
- 比 pip/poetry 快 10-100 倍
- 内置虚拟环境管理
- 支持 lockfile (`uv.lock`) 确保可复现构建
- 与 `pyproject.toml` 完全兼容

**常用命令**:
```bash
# 创建虚拟环境并安装依赖
uv sync

# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 运行命令
uv run python -m pg_mcp

# 运行测试
uv run pytest
```

### 1.4 实现原则

1. **分层实现**: 按照 Models → Infrastructure → Service → MCP 的顺序，自底向上构建
2. **测试先行**: 每个模块完成后立即编写单元测试
3. **增量集成**: 小步提交，持续验证
4. **安全优先**: SQL 验证模块优先实现，确保安全边界
5. **深度防御**: 多层安全措施，不依赖单点验证

---

## 2. 实施阶段

### 阶段概览 (修订版)

```
Phase 1: 项目初始化与共享模型 (2 天)
    │
    ├── Task 1.1: 项目结构搭建 (uv 初始化)
    ├── Task 1.2: 共享数据模型 (errors, query models)  ← 新增：前置
    ├── Task 1.3: 配置模块实现
    └── Task 1.4: 日志与工具模块
    │
Phase 2: 基础设施层 (3 天)
    │
    ├── Task 2.1: 数据库连接池 (含只读事务支持)
    ├── Task 2.2: SQL 解析与验证 (扩展规则)  ← 修改：扩展验证
    ├── Task 2.3: Schema 缓存
    ├── Task 2.4: OpenAI 客户端
    └── Task 2.5: 速率限制器
    │
Phase 3: 业务服务层 (2 天)
    │
    └── Task 3.1: 查询服务实现 (只读事务执行)  ← 修改：深度防御
    │
Phase 4: MCP 层与集成 (2 天)
    │
    ├── Task 4.1: FastMCP 服务器
    └── Task 4.2: 端到端测试 (含安全测试)
    │
Phase 5: 部署与文档 (1 天)
    │
    ├── Task 5.1: Docker 配置
    └── Task 5.2: 使用文档
```

---

## 3. 详细实施计划

### Phase 1: 项目初始化与共享模型

#### Task 1.1: 项目结构搭建 (uv 初始化)

**目标**: 使用 uv 创建项目目录结构和基础配置文件

**交付物**:
```
pg-mcp/
├── pyproject.toml            # 项目配置 (uv)
├── uv.lock                   # 依赖锁定文件
├── .python-version           # Python 版本指定
├── README.md
├── .env.example              # 环境变量配置示例
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config/
│       │   └── __init__.py
│       ├── models/
│       │   └── __init__.py
│       ├── services/
│       │   └── __init__.py
│       ├── infrastructure/
│       │   └── __init__.py
│       └── utils/
│           └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   └── __init__.py
    ├── integration/
    │   └── __init__.py
    └── fixtures/
        └── __init__.py
```

**实现步骤**:

1. 创建项目根目录并初始化 uv 项目：
   ```bash
   mkdir pg-mcp && cd pg-mcp
   uv init --lib
   ```

2. 配置 `.python-version`：
   ```
   3.13.5
   ```

3. 编写 `pyproject.toml`：
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
       "testcontainers[postgres]>=4.0.0",
       "ruff>=0.8.0",
       "mypy>=1.14.0",
   ]

   [project.scripts]
   pg-mcp = "pg_mcp.server:main"

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [tool.uv]
   dev-dependencies = [
       "pytest>=8.0.0",
       "pytest-asyncio>=0.24.0",
       "pytest-cov>=6.0.0",
       "testcontainers[postgres]>=4.0.0",
       "ruff>=0.8.0",
       "mypy>=1.14.0",
   ]

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

4. 安装依赖：
   ```bash
   uv sync
   ```

5. 创建所有目录结构和 `__init__.py` 文件

6. 创建 `.env.example` 环境变量配置示例文件

7. 编写基础 README.md

**验证标准**:
- [ ] `uv sync` 成功安装所有依赖
- [ ] `uv run ruff check .` 无错误
- [ ] `uv run mypy src/` 无错误
- [ ] 生成 `uv.lock` 文件

---

#### Task 1.2: 共享数据模型 (前置)

**目标**: 实现被多个模块依赖的共享数据模型

> **重要**: 此任务从原 Phase 3 前置到 Phase 1，解决依赖顺序问题

**交付物**:
- `src/pg_mcp/models/errors.py` - 错误模型和异常类
- `src/pg_mcp/models/query.py` - 查询请求/响应模型
- `tests/unit/test_models.py` - 单元测试

**依赖**: Task 1.1

**实现步骤**:

1. **错误模型** (`models/errors.py`):
   ```python
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
       RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
       INTERNAL_ERROR = "INTERNAL_ERROR"

   class ErrorResponse(BaseModel):
       """错误响应"""
       success: bool = False
       error_code: ErrorCode
       error_message: str
       details: dict | None = None

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

   # 派生异常类
   class UnknownDatabaseError(PgMcpError): ...
   class UnsafeSQLError(PgMcpError): ...
   class SQLSyntaxError(PgMcpError): ...
   class QueryTimeoutError(PgMcpError): ...
   class DatabaseConnectionError(PgMcpError): ...
   class OpenAIError(PgMcpError): ...
   class RateLimitExceededError(PgMcpError): ...
   ```

2. **查询模型** (`models/query.py`):
   ```python
   from enum import Enum
   from typing import Any
   from pydantic import BaseModel, Field

   class ReturnType(str, Enum):
       SQL = "sql"
       RESULT = "result"
       BOTH = "both"

   class QueryRequest(BaseModel):
       question: str = Field(..., min_length=1, max_length=2000)
       database: str | None = None
       return_type: ReturnType = ReturnType.RESULT
       limit: int | None = Field(default=None, ge=1, le=10000)

   class QueryResult(BaseModel):
       columns: list[str]
       rows: list[list[Any]]
       row_count: int
       truncated: bool = False

   class QueryResponse(BaseModel):
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
       is_safe: bool
       error_message: str | None = None
       warnings: list[str] = Field(default_factory=list)
   ```

3. **单元测试** (`test_models.py`):
   - 测试模型创建和验证
   - 测试异常转换为响应
   - 测试边界值

**验证标准**:
- [ ] 所有模型可以正常实例化
- [ ] 异常类正确继承和转换
- [ ] 单元测试通过

---

#### Task 1.3: 配置模块实现

**目标**: 实现配置加载和验证

**交付物**:
- `src/pg_mcp/config/models.py` - Pydantic 配置模型
- `src/pg_mcp/config/loader.py` - 配置加载器
- `tests/unit/test_config.py` - 单元测试

**依赖**: Task 1.1

**实现步骤**:

1. **配置模型** (`models.py`):
   - `SSLMode` 枚举 (disable, allow, prefer, require)
   - `DatabaseConfig` - 数据库连接配置
     - 支持分离参数和连接字符串两种方式
     - 使用 `SecretStr` 保护密码
     - `get_dsn()` 方法生成连接字符串
   - `OpenAIConfig` - OpenAI API 配置
   - `RateLimitConfig` - 速率限制配置
   - `ServerConfig` - 服务器配置
     - **新增**: `use_readonly_transactions: bool = True` (深度防御开关)
   - `AppConfig` - 应用总配置（使用 `pydantic-settings`）

2. **配置加载器** (`loader.py`):
   - `expand_env_vars()` - 环境变量展开 (支持 `${VAR_NAME}` 语法)
   - `process_config_dict()` - 递归处理配置字典
   - `load_config()` - 主加载函数
   - `_load_from_env()` - 从环境变量构建配置

3. **单元测试**

**验证标准**:
- [ ] 单元测试覆盖率 >= 90%
- [ ] 配置验证能正确拒绝无效输入
- [ ] 环境变量展开正常工作

---

#### Task 1.4: 日志与工具模块

**目标**: 实现日志配置和通用工具函数

**交付物**:
- `src/pg_mcp/utils/logging.py` - structlog 配置
- `src/pg_mcp/utils/env.py` - 环境变量处理工具

**依赖**: Task 1.1

**实现步骤**: (与原计划相同)

**验证标准**:
- [ ] 日志输出格式正确
- [ ] 环境变量读取正常

---

### Phase 2: 基础设施层

#### Task 2.1: 数据库连接池 (含只读事务支持)

**目标**: 实现异步数据库连接池管理，支持只读事务

**交付物**:
- `src/pg_mcp/infrastructure/database.py`
- `tests/unit/test_database.py`

**依赖**: Task 1.2, Task 1.3

**实现步骤**:

1. **SSL 上下文函数**: (与原计划相同)

2. **DatabasePool 类** (扩展):
   - 所有原有方法
   - **新增**: `fetch_readonly(query, *args, timeout)` - 在只读事务中执行查询
     ```python
     async def fetch_readonly(
         self, query: str, *args, timeout: float | None = None
     ) -> list[asyncpg.Record]:
         """在只读事务中执行查询（深度防御）"""
         async with self.acquire() as conn:
             async with conn.transaction(readonly=True):
                 # 设置服务端超时
                 if timeout:
                     await conn.execute(f"SET LOCAL statement_timeout = '{int(timeout * 1000)}'")
                 return await conn.fetch(query, *args, timeout=timeout)
     ```
   - **新增**: `set_session_readonly()` - 设置会话级只读模式

3. **DatabasePoolManager 类**: (与原计划相同)

4. **单元测试** (扩展):
   - 原有测试
   - **新增**: 测试只读事务执行
   - **新增**: 测试只读事务拒绝修改操作

**验证标准**:
- [ ] 连接池正确管理连接数
- [ ] SSL 模式正确工作
- [ ] **只读事务正确阻止写操作**
- [ ] 健康检查返回正确状态

---

#### Task 2.2: SQL 解析与验证 (扩展规则)

**目标**: 实现 SQL 安全验证，防止 SQL 注入和危险操作

> **重要**: 此任务已扩展验证规则，覆盖更多危险 SQL 模式

**交付物**:
- `src/pg_mcp/infrastructure/sql_parser.py`
- `tests/unit/test_sql_parser.py`

**依赖**: Task 1.2

**实现步骤**:

1. **定义安全规则** (扩展版):
   ```python
   from sqlglot import exp

   # 禁止的语句类型
   FORBIDDEN_STATEMENT_TYPES: set[type] = {
       exp.Insert,
       exp.Update,
       exp.Delete,
       exp.Drop,
       exp.Create,
       exp.Alter,
       exp.Truncate,
       exp.Grant,
       exp.Command,
   }

   # 禁止的 SELECT 变体 (新增)
   FORBIDDEN_SELECT_VARIANTS: set[type] = {
       exp.Into,       # SELECT INTO
       exp.Lock,       # FOR UPDATE/SHARE
   }

   # 禁止的危险函数
   FORBIDDEN_FUNCTIONS: set[str] = {
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

   # 禁止的关键字（PostgreSQL 特定 + 扩展）
   FORBIDDEN_KEYWORDS: set[str] = {
       # 文件操作
       "COPY TO",
       "COPY FROM",
       "PG_READ_FILE",
       "PG_WRITE_FILE",
       "PG_READ_BINARY_FILE",
       # SELECT 变体 (新增)
       "SELECT INTO",
       "FOR UPDATE",
       "FOR SHARE",
       "FOR NO KEY UPDATE",
       "FOR KEY SHARE",
       # 会话/角色操作 (新增)
       "SET ROLE",
       "SET SESSION AUTHORIZATION",
       "RESET ROLE",
       # 其他危险操作 (新增)
       "LISTEN",
       "NOTIFY",
       "UNLISTEN",
       "COPY",
   }
   ```

2. **SQLParser 类** (扩展):
   - 所有原有方法
   - **修改** `validate()`:
     - 检查 `FORBIDDEN_SELECT_VARIANTS`
     - 检查 `FOR UPDATE/SHARE` 子句
     - 检查 `INTO` 子句
   - **新增** `_check_select_variants(stmt)` - 检查危险 SELECT 变体
     ```python
     def _check_select_variants(self, stmt: exp.Expression) -> str | None:
         """检查危险的 SELECT 变体"""
         # 检查 INTO 子句 (SELECT INTO)
         if stmt.find(exp.Into):
             return "SELECT INTO is not allowed (creates tables)"

         # 检查 FOR UPDATE/SHARE 子句
         for lock in stmt.find_all(exp.Lock):
             return f"Locking clause ({lock.key}) is not allowed"

         return None
     ```

3. **全面的单元测试** (扩展):
   ```python
   # 原有测试用例 +
   # 新增测试用例
   - test_reject_select_into()           # 拒绝 SELECT INTO
   - test_reject_create_table_as()       # 拒绝 CREATE TABLE AS SELECT
   - test_reject_for_update()            # 拒绝 FOR UPDATE
   - test_reject_for_share()             # 拒绝 FOR SHARE
   - test_reject_for_no_key_update()     # 拒绝 FOR NO KEY UPDATE
   - test_reject_copy_to_program()       # 拒绝 COPY ... TO PROGRAM
   - test_reject_set_role()              # 拒绝 SET ROLE
   - test_reject_listen()                # 拒绝 LISTEN
   - test_reject_notify()                # 拒绝 NOTIFY
   ```

**验证标准**:
- [ ] 单元测试覆盖率 >= 95%
- [ ] 所有已知攻击模式都被阻止
- [ ] **新增的 SELECT 变体被正确拦截**
- [ ] 正常 SELECT 查询正确通过

---

#### Task 2.3: Schema 缓存

**目标**: 实现数据库 Schema 元数据的加载和缓存

**交付物**:
- `src/pg_mcp/models/schema.py` - Schema 数据模型
- `src/pg_mcp/infrastructure/schema_cache.py` - 缓存实现
- `tests/unit/test_schema_cache.py`

**依赖**: Task 2.1

**实现步骤**: (与原计划相同)

**验证标准**: (与原计划相同)

---

#### Task 2.4: OpenAI 客户端

**目标**: 封装 OpenAI API 调用，实现 SQL 生成

**交付物**:
- `src/pg_mcp/infrastructure/openai_client.py`
- `tests/unit/test_openai_client.py`

**依赖**: Task 1.2, Task 1.3, Task 2.3

**实现步骤**: (与原计划相同)

**验证标准**: (与原计划相同)

---

#### Task 2.5: 速率限制器

**目标**: 实现请求和 Token 使用的速率限制

**交付物**:
- `src/pg_mcp/infrastructure/rate_limiter.py`
- `tests/unit/test_rate_limiter.py`

**依赖**: Task 1.2

**实现步骤**: (与原计划相同)

**验证标准**: (与原计划相同)

---

### Phase 3: 业务服务层

#### Task 3.1: 查询服务实现 (只读事务执行)

**目标**: 实现核心查询业务逻辑，使用只读事务作为深度防御

**交付物**:
- `src/pg_mcp/services/query_service.py`
- `tests/unit/test_query_service.py`

**依赖**: Phase 2 全部完成

**实现步骤**:

1. **QueryService 类** (修改):
   - `__init__()` - 接收配置和依赖
   - `execute_query(request) -> QueryResponse` - 主入口
   - `_resolve_database(database)` - 解析目标数据库
   - `_generate_sql_with_retry(question, schema, database)` - SQL 生成（带重试）
     - **修改**: EXPLAIN 在只读事务中执行
   - **修改** `_execute_sql(database, sql, limit)` - 在只读事务中执行 SQL
     ```python
     async def _execute_sql(
         self,
         database: str,
         sql: str,
         limit: int
     ) -> QueryResult:
         """在只读事务中执行 SQL（深度防御）"""
         pool = self._pool_manager.get_pool(database)
         sql_with_limit = self._sql_parser.add_limit(sql, limit + 1)

         try:
             # 使用只读事务执行（深度防御）
             if self.config.use_readonly_transactions:
                 rows = await asyncio.wait_for(
                     pool.fetch_readonly(sql_with_limit, timeout=self.config.query_timeout),
                     timeout=self.config.query_timeout + 5  # 留一点余量
                 )
             else:
                 rows = await asyncio.wait_for(
                     pool.fetch(sql_with_limit),
                     timeout=self.config.query_timeout
                 )
         except asyncio.TimeoutError:
             raise QueryTimeoutError(self.config.query_timeout)
         except asyncpg.PostgresError as e:
             # 只读事务会拒绝写操作，这是预期行为
             if "cannot execute" in str(e).lower() and "read-only" in str(e).lower():
                 raise UnsafeSQLError("Query attempted to modify data (blocked by read-only transaction)")
             raise PgMcpError(ErrorCode.SYNTAX_ERROR, str(e))

         # ... 处理结果
     ```
   - `_serialize_rows(rows)` - 序列化结果

2. **单元测试** (扩展):
   - 原有测试
   - **新增**: 测试只读事务阻止写操作
   - **新增**: 测试 EXPLAIN 在只读事务中执行

**关键实现细节**:
```python
# 深度防御：即使 SQL 验证被绕过，只读事务也会阻止修改
async with conn.transaction(readonly=True):
    # 设置语句超时（防止长时间查询）
    await conn.execute(f"SET LOCAL statement_timeout = '{timeout_ms}'")
    rows = await conn.fetch(sql)
```

**验证标准**:
- [ ] 完整查询流程正常工作
- [ ] 错误正确传播和处理
- [ ] **只读事务正确阻止未检测到的写操作**
- [ ] 重试逻辑正确执行

---

### Phase 4: MCP 层与集成

#### Task 4.1: FastMCP 服务器

**目标**: 实现 MCP 服务器接口

**交付物**:
- `src/pg_mcp/server.py`
- `src/pg_mcp/__main__.py`
- `tests/integration/test_mcp_server.py`

**依赖**: Task 3.1

**实现步骤**: (与原计划相同)

**验证标准**: (与原计划相同)

---

#### Task 4.2: 端到端测试 (含安全测试)

**目标**: 实现完整的端到端测试，包含安全测试

**交付物**:
- `tests/integration/test_query_flow.py`
- `tests/integration/test_security.py` - 新增安全测试
- `tests/fixtures/sample_schemas.py`

**依赖**: Task 4.1

**实现步骤**:

1. **测试 Fixtures**:
   - 使用 `testcontainers` 启动真实 PostgreSQL
   - 创建测试用 Schema 数据
   - Mock OpenAI 响应

2. **集成测试用例** (`test_query_flow.py`):
   - 测试简单查询
   - 测试多数据库场景
   - 测试超时处理
   - 测试速率限制

3. **安全测试** (`test_security.py`):
   ```python
   import pytest
   from testcontainers.postgres import PostgresContainer

   class TestSecurityDefenseInDepth:
       """深度防御安全测试"""

       @pytest.fixture
       async def real_db(self):
           """使用真实 PostgreSQL 进行测试"""
           with PostgresContainer("postgres:16") as postgres:
               yield postgres

       @pytest.mark.asyncio
       async def test_readonly_transaction_blocks_insert(self, real_db, query_service):
           """测试只读事务阻止 INSERT（即使验证被绕过）"""
           # 模拟 SQL 验证被绕过的场景
           ...

       @pytest.mark.asyncio
       async def test_readonly_transaction_blocks_update(self, real_db, query_service):
           """测试只读事务阻止 UPDATE"""
           ...

       @pytest.mark.asyncio
       async def test_readonly_transaction_blocks_delete(self, real_db, query_service):
           """测试只读事务阻止 DELETE"""
           ...

       @pytest.mark.asyncio
       async def test_select_into_blocked(self, query_service):
           """测试 SELECT INTO 被阻止"""
           ...

       @pytest.mark.asyncio
       async def test_for_update_blocked(self, query_service):
           """测试 FOR UPDATE 被阻止"""
           ...
   ```

**验证标准**:
- [ ] 端到端流程正常
- [ ] 所有错误场景正确处理
- [ ] **安全测试全部通过**
- [ ] **使用真实数据库的测试通过**

---

### Phase 5: 部署与文档

#### Task 5.1: Docker 配置

**目标**: 创建 Docker 部署配置

**交付物**:
- `Dockerfile`
- `docker-compose.yaml`
- `.dockerignore`

**依赖**: Phase 4 完成

**实现步骤**:

1. 编写 Dockerfile (使用 uv):
   ```dockerfile
   FROM python:3.13.5-slim

   WORKDIR /app

   # 安装 uv
   RUN pip install uv

   # 复制依赖文件
   COPY pyproject.toml uv.lock ./

   # 安装依赖
   RUN uv sync --frozen --no-dev

   # 复制源代码
   COPY src/ ./src/

   # 设置环境变量
   ENV PYTHONPATH=/app/src

   # 入口点
   ENTRYPOINT ["uv", "run", "python", "-m", "pg_mcp"]
   ```

2. 编写 docker-compose.yaml (包含测试 PostgreSQL)
   - 使用环境变量配置 (PG_MCP_DATABASE_*, PG_MCP_OPENAI_* 等)

3. 编写 .dockerignore

**验证标准**:
- [ ] Docker 镜像构建成功
- [ ] 容器正常运行

---

#### Task 5.2: 使用文档

**目标**: 完善项目文档

**交付物**:
- `README.md` - 完整使用说明

**依赖**: Phase 4 完成

**实现步骤**:

1. 编写安装说明 (使用 uv)
2. 编写配置说明
3. 编写使用示例
4. 编写 Claude Desktop 配置示例

**验证标准**:
- [ ] 文档清晰完整
- [ ] 示例可运行

---

## 4. 依赖关系图 (修订版)

```
Task 1.1 ─┬─> Task 1.2 (Models) ────────────────┐
          │                                      │
          ├─> Task 1.3 (Config) ─────────────────┤
          │                                      │
          └─> Task 1.4 (Utils)                   │
                                                 │
Task 1.2 ─┬─> Task 2.1 (Database) ──────────────┤
          │                                      │
          ├─> Task 2.2 (SQL Parser) ────────────┤
          │                                      │
          ├─> Task 2.4 (OpenAI) ────────────────┤
          │                                      │
          └─> Task 2.5 (RateLimiter) ───────────┤
                                                 │
Task 2.1 ──> Task 2.3 (Schema Cache) ───────────┤
                                                 │
                                                 ▼
                                            Task 3.1 (QueryService)
                                                 │
                                                 ▼
                                            Task 4.1 (MCP Server)
                                                 │
                                                 ▼
                                            Task 4.2 (E2E Test)
                                                 │
                                                 ▼
                                   Task 5.1 & 5.2 (Deploy & Docs)
```

**关键变化**:
- Task 1.2 (Models) 现在是 Phase 1 的一部分，解决了依赖顺序问题
- Task 2.1, 2.2, 2.4, 2.5 都依赖 Task 1.2

---

## 5. 测试策略

### 5.1 测试层次

| 层次 | 范围 | 工具 |
|------|------|------|
| 单元测试 | 单个函数/类 | pytest, pytest-asyncio |
| 集成测试 | 模块间交互 | pytest, mock |
| E2E 测试 | 完整流程 | pytest, **testcontainers** |
| 安全测试 | 防御机制 | pytest, testcontainers |

### 5.2 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| sql_parser | >= 95% |
| query_service | >= 90% |
| schema_cache | >= 85% |
| config | >= 90% |
| **security tests** | **100%** |
| **总体** | **>= 85%** |

### 5.3 关键测试用例

**安全相关 (必须 100% 覆盖)**:
- [ ] INSERT/UPDATE/DELETE 被拒绝
- [ ] DROP/TRUNCATE 被拒绝
- [ ] pg_sleep 等危险函数被拒绝
- [ ] COPY TO/FROM 被拒绝
- [ ] Stacked queries 被拒绝
- [ ] CTE 中的修改操作被拒绝
- [ ] 子查询中的修改操作被拒绝
- [ ] **SELECT INTO 被拒绝** (新增)
- [ ] **FOR UPDATE/SHARE 被拒绝** (新增)
- [ ] **SET ROLE 被拒绝** (新增)
- [ ] **只读事务阻止写操作** (新增)

**功能相关**:
- [ ] 正常 SELECT 查询通过
- [ ] 多数据库切换
- [ ] Schema 缓存刷新
- [ ] 速率限制触发
- [ ] 超时处理

---

## 6. 风险评估与缓解

### 6.1 技术风险

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|---------|
| SQLGlot 解析边界情况 | 高 | 中 | 文本关键字检查 + 只读事务深度防御 |
| asyncpg 连接池泄漏 | 高 | 低 | 使用上下文管理器确保释放 |
| OpenAI API 不稳定 | 中 | 中 | 实现重试和降级 |
| Schema 缓存不一致 | 中 | 低 | 原子刷新 + 手动刷新接口 |
| Python 3.13 兼容性 | 中 | 低 | 验证所有依赖兼容性 |

### 6.2 安全风险

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|---------|
| SQL 注入 | 高 | 中 | **多层验证 (SQLGlot + 关键字检查 + 只读事务)** |
| 凭证泄露 | 高 | 低 | SecretStr + 环境变量 |
| 拒绝服务 | 中 | 中 | 速率限制 + 查询超时 + statement_timeout |
| 权限提升 | 高 | 低 | 阻止 SET ROLE + 只读事务 |

---

## 7. 检查清单

### Phase 1 完成检查
- [ ] 项目结构完整
- [ ] uv 环境配置正确
- [ ] **共享模型实现完成**
- [ ] 配置加载正常
- [ ] 日志输出正常

### Phase 2 完成检查
- [ ] 数据库连接正常
- [ ] **只读事务支持正常**
- [ ] SQL 解析验证通过安全测试
- [ ] **扩展的 SQL 验证规则通过测试**
- [ ] Schema 缓存正确加载
- [ ] OpenAI 调用正常
- [ ] 速率限制工作正常

### Phase 3 完成检查
- [ ] 查询服务端到端测试通过
- [ ] **只读事务深度防御测试通过**
- [ ] 错误处理完整
- [ ] 重试逻辑正确

### Phase 4 完成检查
- [ ] MCP 服务器启动正常
- [ ] Resources 和 Tools 工作正常
- [ ] 集成测试全部通过
- [ ] **安全测试全部通过**

### Phase 5 完成检查
- [ ] Docker 镜像构建成功
- [ ] 文档完整清晰

---

## 8. 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-10 | 初始实现计划 | Claude |
| 2.0 | 2026-01-10 | 根据 Codex Review 修订: (1) 将共享模型 Task 1.2 前置到 Phase 1; (2) 添加只读事务深度防御到 Task 2.1 和 Task 3.1; (3) 扩展 SQL 验证规则覆盖 SELECT INTO, FOR UPDATE 等; (4) 添加 uv 环境管理详细说明; (5) 添加安全测试 Task 4.2; (6) 更新依赖关系图 | Claude |
