# PostgreSQL MCP Server 增强功能需求文档

**版本**: 1.1
**日期**: 2026-01-14
**状态**: 已审核
**前置文档**:
- [0001-pg-mcp-prd.md](./0001-pg-mcp-prd.md)
- [0002-pg-mcp-design.md](./0002-pg-mcp-design.md)
- [0004-pg-mcp-impl-plan.md](./0004-pg-mcp-impl-plan.md)

---

## 1. 概述

### 1.1 背景

PostgreSQL MCP Server 的核心功能已基本实现，但在代码审查和实际测试中发现，部分设计文档中承诺的功能未能完全落地，主要集中在以下三个领域：

1. **多数据库与安全控制**：多数据库路由、表/列访问控制、EXPLAIN 策略等安全边界未得到强制执行
2. **弹性与可观测性**：速率限制、重试/退避、指标/追踪等弹性机制未整合到请求处理流程
3. **代码质量与测试**：存在冗余代码模式、未使用的配置字段，测试覆盖不足

### 1.2 目标

本需求文档旨在补齐上述功能缺口，确保系统行为与设计文档一致，并提升整体可靠性和可维护性。

### 1.3 范围

| 领域 | 优先级 | 说明 |
|------|--------|------|
| 多数据库与安全控制 | P0 (必须) | 涉及数据安全，必须优先实现 |
| 弹性与可观测性 | P1 (重要) | 生产环境必备能力 |
| 代码质量与测试 | P2 (改进) | 提升可维护性 |

---

## 2. 多数据库与安全控制

### 2.1 问题描述

当前实现存在以下安全隐患：

1. **数据库隔离不足**：
   - `QueryService` 使用 `DatabasePoolManager` 管理多数据库连接，但缺乏针对具体数据库的访问策略执行器
   - 请求可能被路由到错误的数据库，或越权访问其他数据库

2. **表/列访问控制缺失**：
   - 设计中提及的敏感表/列白名单机制未实现
   - 无法限制 LLM 生成的 SQL 只访问特定表或列

3. **EXPLAIN 策略未强制执行**：
   - 虽然在 `_generate_sql_with_retry` 中有 EXPLAIN 验证，但仅用于语法检查
   - 未利用 EXPLAIN 输出分析查询计划，防止资源滥用

### 2.2 功能需求

#### 2.2.1 数据库访问策略执行器 (DatabaseAccessPolicy)

**描述**: 为每个数据库配置独立的访问策略，在 SQL 执行前强制检查

**配置结构**:
```yaml
databases:
  - name: "production_analytics"
    host: "localhost"
    # ... 连接配置 ...

    # 新增: 访问策略配置
    access_policy:
      # 允许访问的 Schema 列表 (默认: ["public"])
      allowed_schemas:
        - "public"
        - "analytics"

      # 表级访问控制
      tables:
        # 白名单模式: 只允许访问指定表 (优先级高于黑名单)
        allowed:
          - "orders"
          - "users"
          - "products"
        # 黑名单模式: 禁止访问指定表
        denied:
          - "user_credentials"
          - "payment_tokens"

      # 列级访问控制 (敏感列保护)
      columns:
        denied:
          - "users.password_hash"
          - "users.ssn"
          - "orders.credit_card"
        # 或使用模式匹配
        denied_patterns:
          - "*._password*"
          - "*._token*"
          - "*._secret*"
        # 处理策略: "reject" (拒绝查询) | "filter" (自动移除敏感列)
        on_denied: "reject"
        # SELECT * 处理: "reject" (包含敏感列时拒绝) | "expand_safe" (展开为安全列)
        select_star_policy: "reject"

      # EXPLAIN 策略
      explain_policy:
        # 是否强制执行 EXPLAIN 检查
        enabled: true
        # 最大估算行数 (超过则拒绝)
        max_estimated_rows: 100000
        # 最大估算成本 (超过则警告)
        max_estimated_cost: 10000
        # 是否禁止全表扫描
        deny_seq_scan_on_large_tables: true
        # "大表"的阈值行数 (使用 pg_class.reltuples 估算，避免额外查询)
        large_table_threshold: 10000
        # 性能优化配置
        timeout_seconds: 5.0           # EXPLAIN 自身的超时限制
        cache_ttl_seconds: 60          # 相同 SQL 的 EXPLAIN 结果缓存时间
        cache_max_size: 1000           # 缓存最大条目数
```

**接口设计**:
```python
class DatabaseAccessPolicy:
    """数据库访问策略执行器"""

    def __init__(self, config: AccessPolicyConfig):
        # 构造时验证配置一致性
        self._validate_config(config)
        ...

    def _validate_config(self, config: AccessPolicyConfig) -> None:
        """验证配置一致性，发现冲突时抛出 ConfigurationError"""
        # 检查表配置冲突
        table_conflicts = set(config.tables.allowed) & set(config.tables.denied)
        if table_conflicts:
            raise ConfigurationError(
                f"Tables in both allowed and denied lists: {table_conflicts}"
            )

        # 检查列配置合法性
        for col in config.columns.denied:
            if '.' not in col:
                raise ConfigurationError(
                    f"Column '{col}' must be in 'table.column' format"
                )

    def validate_sql(self, sql: str, parsed_tables: list[str]) -> PolicyValidationResult:
        """验证 SQL 是否符合访问策略"""
        ...

    def check_columns(self, columns: list[tuple[str, str]]) -> list[str]:
        """检查列访问，返回被禁止的列列表"""
        ...

    async def validate_explain(
        self,
        conn: Connection,
        sql: str
    ) -> ExplainValidationResult:
        """验证 EXPLAIN 输出是否符合策略"""
        ...
```

**配置优先级规则**:
1. **表级**: `allowed` (白名单) 优先级高于 `denied` (黑名单)
   - 若 `allowed` 非空，则只有列表中的表可访问
   - 若 `allowed` 为空，则除 `denied` 外的表都可访问
2. **列级**: 仅检查 `denied` 列表，无白名单模式
3. **Schema 级**: 仅检查 `allowed_schemas`，默认 `["public"]`

**配置验证命令** (建议实现):
```bash
# 验证配置文件正确性，不启动服务
pg-mcp config validate --config /path/to/config.yaml

# 输出示例
✓ Database connections: 2 configured
✓ Access policies: No conflicts detected
✓ EXPLAIN policy: Enabled (max_rows=100000, max_cost=10000)
⚠ Warning: Column pattern '*._password*' may match too broadly
```

**验收标准**:
- [ ] SQL 访问未授权的表时返回 `TABLE_ACCESS_DENIED` 错误
- [ ] SQL 显式访问敏感列时返回 `COLUMN_ACCESS_DENIED` 错误（`on_denied: reject`）
- [ ] SQL 使用 `SELECT *` 且表包含敏感列时：
  - `select_star_policy: reject` → 返回 `COLUMN_ACCESS_DENIED` 错误并提示具体敏感列名
  - `select_star_policy: expand_safe` → 自动展开为非敏感列列表
- [ ] `on_denied: filter` 时自动从 SELECT 中移除敏感列（需配合 SQL 重写）
- [ ] EXPLAIN 估算超限时返回 `QUERY_TOO_EXPENSIVE` 错误
- [ ] 全表扫描大表时返回 `SEQ_SCAN_DENIED` 错误（可配置为警告）
- [ ] 配置冲突时（如同一表同时在 allowed 和 denied 中）启动时报错

#### 2.2.2 多数据库路由增强

**描述**: 确保请求被正确路由到目标数据库，防止跨库访问

**功能点**:

1. **请求上下文绑定**:
   - 每个查询请求必须明确绑定到一个数据库
   - 若未指定且存在多个数据库，返回错误而非猜测

2. **执行器隔离**:
   - 为每个数据库创建独立的 `QueryExecutor` 实例
   - `QueryExecutor` 持有对应的 `DatabasePool` 和 `AccessPolicy`
   - 禁止跨 `QueryExecutor` 共享连接

**`QueryExecutor` 与 `QueryService` 的关系**:

```
┌─────────────────────────────────────────────────────────────┐
│                      QueryService                           │
│  - 业务逻辑编排 (SQL 生成、验证、结果处理)                    │
│  - 持有: OpenAIClient, SQLParser, SchemaCacheManager        │
│  - 调用 QueryExecutorManager 获取执行器                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 委托执行
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  QueryExecutorManager                        │
│  - 管理多个 QueryExecutor 实例                               │
│  - get_executor(database) -> QueryExecutor                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │ Executor A │  │ Executor B │  │ Executor C │
       │ (db: prod) │  │ (db: stage)│  │ (db: dev)  │
       │ + Pool     │  │ + Pool     │  │ + Pool     │
       │ + Policy   │  │ + Policy   │  │ + Policy   │
       └────────────┘  └────────────┘  └────────────┘
```

- `QueryService`: 负责整体业务流程（SQL 生成 → 验证 → 执行 → 结果处理）
- `QueryExecutor`: 负责单数据库的 SQL 执行，强制应用该库的访问策略
- 职责分离: `QueryService` 不直接持有 `DatabasePool`，通过 `QueryExecutorManager` 间接访问

3. **审计日志**:
   - 记录每次查询的目标数据库、用户标识、SQL、执行时间
   - 日志格式支持后续安全审计分析

**审计日志详细设计**:

```yaml
# 审计日志配置
audit:
  enabled: true
  # 存储方式: "file" | "stdout" | "database"
  storage: "file"
  # 文件路径 (仅 file 模式)
  file_path: "/var/log/pg-mcp/audit.jsonl"
  # 日志轮转
  rotation:
    max_size_mb: 100
    max_files: 10
    compress: true
  # 敏感数据处理
  redact_sql: false  # 是否脱敏 SQL 中的字面量
```

**审计日志格式** (JSON Lines):
```json
{
  "timestamp": "2026-01-14T10:30:45.123Z",
  "event_type": "query_executed",
  "request_id": "req_abc123",
  "session_id": "sess_xyz789",
  "database": "production_analytics",
  "client_info": {
    "ip": "192.168.1.100",
    "user_agent": "claude-desktop/1.0"
  },
  "query": {
    "question": "查询最近7天的订单总额",
    "sql": "SELECT SUM(total_amount) FROM orders WHERE created_at > NOW() - INTERVAL '7 days'",
    "sql_hash": "sha256:abc123..."
  },
  "result": {
    "status": "success",
    "rows_returned": 1,
    "execution_time_ms": 45,
    "truncated": false
  },
  "policy_checks": {
    "table_access": "passed",
    "column_access": "passed",
    "explain_check": "passed"
  }
}
```

> **注意**: `client_info.ip` 仅在 SSE 模式下可用；stdio 模式下该字段为 `null`。用户标识来源于 MCP 会话上下文（如可用）或配置的默认用户。

**接口设计**:
```python
class QueryExecutor:
    """单数据库查询执行器"""

    def __init__(
        self,
        database_name: str,
        pool: DatabasePool,
        access_policy: DatabaseAccessPolicy
    ):
        ...

    async def execute(
        self,
        sql: str,
        limit: int,
        audit_context: AuditContext
    ) -> QueryResult:
        """执行查询 (强制应用访问策略)"""
        ...

class QueryExecutorManager:
    """查询执行器管理器"""

    def get_executor(self, database: str) -> QueryExecutor:
        """获取指定数据库的执行器"""
        ...
```

**验收标准**:
- [ ] 每个数据库有独立的执行器实例
- [ ] 未指定数据库时，若存在多个库则返回明确错误
- [ ] 审计日志包含完整的查询上下文

---

## 3. 弹性与可观测性

### 3.1 问题描述

当前实现存在以下可靠性问题：

1. **速率限制未生效**：
   - `RateLimiter` 类已实现，但未整合到 `QueryService` 或 MCP 层
   - 恶意或高频请求可能耗尽 OpenAI 配额或数据库连接

2. **重试/退避机制不完整**：
   - OpenAI 客户端依赖 SDK 内置重试，缺乏自定义退避策略
   - 数据库查询超时后直接失败，未实现智能重试

3. **可观测性缺失**：
   - 无指标暴露（如 Prometheus 格式）
   - 无分布式追踪（如 OpenTelemetry）
   - 日志虽结构化但缺乏关键性能指标

### 3.2 功能需求

#### 3.2.1 速率限制集成

**描述**: 将速率限制整合到请求处理流程中

**整合点**:

```
MCP Request
    │
    ▼
┌─────────────────┐
│  RateLimiter    │ ← 检查请求速率
│  (pre-check)    │
└────────┬────────┘
         │ 通过
         ▼
┌─────────────────┐
│  QueryService   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OpenAI API     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RateLimiter    │ ← 记录 Token 消耗
│  (post-record)  │
└────────┬────────┘
         │
         ▼
     Response
```

**配置增强**:
```yaml
rate_limit:
  enabled: true

  # 请求速率限制
  requests:
    per_minute: 60
    per_hour: 1000
    # 新增: 基于客户端的限制 (SSE 模式使用 IP，stdio 模式使用 session_id)
    per_client_per_minute: 20
    # 客户端标识方式: "ip" (仅 SSE) | "session" | "auto" (自动选择)
    client_identifier: "auto"

  # Token 消耗限制
  tokens:
    per_minute: 100000
    per_hour: 1000000

  # 新增: 限流策略
  strategy:
    # 超限时的行为: "reject" | "queue" | "delay"
    on_limit_exceeded: "reject"
    # 队列模式下的最大等待时间 (秒)
    max_queue_wait: 30
    # 响应头中包含限流信息
    include_headers: true
```

**响应头示例**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

**验收标准**:
- [ ] 超过速率限制时返回 `RATE_LIMIT_EXCEEDED` 错误
- [ ] 错误响应包含 `retry_after` 字段
- [ ] Token 消耗被正确累计
- [ ] 可通过配置禁用速率限制

#### 3.2.2 重试与退避机制

**描述**: 为关键操作实现智能重试，提升可靠性

**重试策略配置**:
```yaml
retry:
  # OpenAI API 重试
  openai:
    max_retries: 3
    # 退避策略: "exponential" | "fixed" | "fibonacci"
    backoff_strategy: "exponential"
    # 初始等待时间 (秒)
    initial_delay: 1.0
    # 最大等待时间 (秒)
    max_delay: 30.0
    # 指数退避乘数
    multiplier: 2.0
    # 可重试的错误类型
    retryable_errors:
      - "rate_limit"
      - "timeout"
      - "server_error"

  # 数据库操作重试
  database:
    max_retries: 2
    backoff_strategy: "fixed"
    initial_delay: 0.5
    retryable_errors:
      - "connection_lost"
      - "timeout"
      # 注意: 不重试语法错误
```

**接口设计**:
```python
class RetryExecutor:
    """带重试的执行器"""

    def __init__(self, config: RetryConfig):
        ...

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
        is_retryable: Callable[[Exception], bool] | None = None
    ) -> T:
        """执行操作，失败时按策略重试"""
        ...

class BackoffStrategy(ABC):
    """退避策略接口"""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试前的等待时间"""
        ...

class ExponentialBackoff(BackoffStrategy):
    """指数退避"""
    ...

class FibonacciBackoff(BackoffStrategy):
    """斐波那契退避"""
    ...
```

**验收标准**:
- [ ] OpenAI API 临时错误触发重试
- [ ] 数据库连接丢失触发重试
- [ ] 重试次数和延迟符合配置
- [ ] 非可重试错误立即失败
- [ ] 日志记录每次重试的尝试

#### 3.2.3 指标与追踪

**描述**: 暴露关键指标并支持分布式追踪

**指标定义** (Prometheus 格式):

```python
# 请求指标
pg_mcp_requests_total{database, status, error_code}          # 请求总数
pg_mcp_request_duration_seconds{database, quantile}          # 请求延迟分布
pg_mcp_request_in_flight{database}                           # 正在处理的请求数

# SQL 生成指标
pg_mcp_sql_generation_total{database, status}                # SQL 生成次数
pg_mcp_sql_generation_duration_seconds{database, quantile}   # SQL 生成延迟
pg_mcp_sql_retries_total{database, reason}                   # SQL 重试次数

# 数据库指标
pg_mcp_db_pool_size{database}                                # 连接池大小
pg_mcp_db_pool_available{database}                           # 可用连接数
pg_mcp_db_query_duration_seconds{database, quantile}         # 查询执行延迟

# OpenAI 指标
pg_mcp_openai_tokens_used_total{type}                        # Token 消耗 (prompt/completion)
pg_mcp_openai_requests_total{status}                         # API 调用次数
pg_mcp_openai_request_duration_seconds{quantile}             # API 调用延迟

# 速率限制指标
pg_mcp_rate_limit_current{limit_type}                        # 当前使用量
pg_mcp_rate_limit_exceeded_total{limit_type}                 # 超限次数
```

**追踪集成** (OpenTelemetry):

```python
# 追踪 span 示例
with tracer.start_as_current_span("query.execute") as span:
    span.set_attribute("db.name", database)
    span.set_attribute("query.question", question[:100])

    with tracer.start_as_current_span("sql.generate"):
        sql = await generate_sql(...)
        span.set_attribute("sql.length", len(sql))

    with tracer.start_as_current_span("db.execute"):
        result = await execute_query(...)
        span.set_attribute("db.rows_returned", result.row_count)
```

**配置**:
```yaml
observability:
  # 指标配置
  metrics:
    enabled: true
    # 暴露方式: "prometheus" | "otlp"
    exporter: "prometheus"
    # Prometheus 端口 (仅 prometheus 模式)
    port: 9090
    # 指标路径
    path: "/metrics"

  # 追踪配置
  tracing:
    enabled: false
    # 导出方式: "jaeger" | "zipkin" | "otlp"
    exporter: "otlp"
    # OTLP 端点
    endpoint: "http://localhost:4317"
    # 采样率 (0.0 - 1.0)
    sample_rate: 0.1
    # 服务名称
    service_name: "pg-mcp"

  # 日志增强
  logging:
    # 是否在日志中包含 trace_id
    include_trace_id: true
    # 是否记录 SQL (可能包含敏感数据)
    log_sql: false
    # 慢查询阈值 (秒)
    slow_query_threshold: 5.0
```

**验收标准**:
- [ ] `/metrics` 端点返回 Prometheus 格式指标
- [ ] 关键操作有对应的追踪 span
- [ ] 日志中包含 trace_id (如果追踪启用)
- [ ] 慢查询被特别记录

---

## 4. 代码质量与测试

### 4.1 问题描述

代码审查发现以下质量问题：

1. **冗余代码模式**:
   - 多个模型类实现了重复的 `to_dict()` 方法，但 Pydantic 已提供 `model_dump()`
   - 部分工具函数在多处重复定义

2. **未使用的配置字段**:
   - `ServerConfig.enable_result_validation` 定义但从未使用
   - 部分配置字段有默认值但缺乏运行时验证

3. **测试覆盖不足**:
   - 安全相关模块（SQL 验证、访问控制）测试用例不完整
   - 集成测试缺乏真实数据库验证
   - 边界条件测试缺失

### 4.2 功能需求

#### 4.2.1 代码清理

**任务清单**:

1. **移除冗余 `to_dict()` 方法**:
   - 审计所有 Pydantic 模型，移除自定义 `to_dict()` 方法
   - 统一使用 `model_dump()` 或 `model_dump_json()`
   - 若有特殊序列化需求，使用 `model_serializer` 装饰器

2. **统一工具函数**:
   - 将分散的工具函数合并到 `utils/` 目录
   - 创建 `utils/serialization.py` 处理所有序列化逻辑
   - 创建 `utils/validation.py` 处理通用验证逻辑

3. **清理未使用的配置**:
   - 审计 `config/models.py`，移除或实现所有配置字段
   - 为必要的配置字段添加运行时验证
   - 添加配置项弃用警告机制

4. **`enable_result_validation` 配置处理** (决策: 实现):
   - 原 PRD 承诺该功能但未实现，应当补全
   - 实现位置: `QueryService._execute_sql()` 执行后调用 `OpenAIClient.validate_result()`
   - 触发条件:
     - 配置 `server.enable_result_validation: true` 时启用
     - 查询结果为空时自动触发（确认是数据问题还是 SQL 问题）
   - 验证失败时记录警告日志，但不阻止返回结果（避免影响可用性）

**验收标准**:
- [ ] 无自定义 `to_dict()` 方法
- [ ] 所有配置字段都有使用点
- [ ] `ruff check .` 无警告

#### 4.2.2 测试覆盖增强

**目标覆盖率** (与 0004-pg-mcp-impl-plan.md 统一，取最高值):

| 模块 | 当前覆盖率 | 目标覆盖率 | 说明 |
|------|-----------|-----------|------|
| `sql_parser.py` | ~70% | **>= 95%** | 安全关键模块 |
| `database.py` | ~50% | >= 80% | |
| `query_service.py` | ~60% | **>= 90%** | 核心业务逻辑 |
| `access_policy.py` (新增) | 0% | **>= 95%** | 安全关键模块 |
| `rate_limiter.py` | ~40% | >= 80% | |
| `security tests` | - | **100%** | 安全测试必须全覆盖 |
| **总体** | ~55% | **>= 85%** | 与实施计划保持一致 |

**测试类型**:

1. **单元测试增强**:
   - SQL 验证器: 覆盖所有已知攻击模式（见附录 A）
   - 访问策略: 覆盖所有配置组合
   - 速率限制器: 覆盖边界条件和并发场景

2. **集成测试增强**:
   - 使用 `testcontainers` 运行真实 PostgreSQL
   - 测试多数据库路由
   - 测试只读事务深度防御
   - 测试 EXPLAIN 策略执行

3. **端到端测试** (新增):
   - 模拟 MCP 客户端完整请求流程
   - 测试错误传播和响应格式
   - 性能基准测试

4. **安全测试** (新增):
   - SQL 注入 fuzz 测试
   - 访问控制绕过测试
   - 速率限制绕过测试

**测试框架增强**:
```python
# tests/conftest.py 增强

import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """启动真实 PostgreSQL 容器"""
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture
async def real_database(postgres_container):
    """创建测试数据库和 Schema"""
    # 创建连接、初始化 Schema、返回 pool
    ...

@pytest.fixture
def sql_injection_payloads():
    """SQL 注入测试向量"""
    return [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "1; TRUNCATE orders",
        "UNION SELECT * FROM user_credentials",
        "1); DELETE FROM orders WHERE (1=1",
        # ... 更多 payload
    ]
```

**验收标准**:
- [ ] 总体测试覆盖率 >= 80%
- [ ] 安全模块覆盖率 >= 95%
- [ ] 所有 CI 测试通过
- [ ] 性能基准测试建立基线

---

## 5. 数据模型变更

### 5.1 新增模型

#### AccessPolicyConfig

```python
class TableAccessConfig(BaseModel):
    """表访问控制配置"""
    allowed: list[str] = Field(default_factory=list)
    denied: list[str] = Field(default_factory=list)

class ColumnAccessConfig(BaseModel):
    """列访问控制配置"""
    denied: list[str] = Field(default_factory=list)
    denied_patterns: list[str] = Field(default_factory=list)

class ExplainPolicyConfig(BaseModel):
    """EXPLAIN 策略配置"""
    enabled: bool = True
    max_estimated_rows: int = Field(default=100000)
    max_estimated_cost: float = Field(default=10000.0)
    deny_seq_scan_on_large_tables: bool = True
    large_table_threshold: int = Field(default=10000)

class AccessPolicyConfig(BaseModel):
    """数据库访问策略配置"""
    allowed_schemas: list[str] = Field(default=["public"])
    tables: TableAccessConfig = Field(default_factory=TableAccessConfig)
    columns: ColumnAccessConfig = Field(default_factory=ColumnAccessConfig)
    explain_policy: ExplainPolicyConfig = Field(default_factory=ExplainPolicyConfig)
```

#### 新增错误码

```python
class ErrorCode(str, Enum):
    # ... 现有错误码 ...

    # 新增: 访问控制相关
    ACCESS_DENIED = "ACCESS_DENIED"
    TABLE_ACCESS_DENIED = "TABLE_ACCESS_DENIED"
    COLUMN_ACCESS_DENIED = "COLUMN_ACCESS_DENIED"
    SCHEMA_ACCESS_DENIED = "SCHEMA_ACCESS_DENIED"

    # 新增: EXPLAIN 策略相关
    QUERY_TOO_EXPENSIVE = "QUERY_TOO_EXPENSIVE"
    SEQ_SCAN_DENIED = "SEQ_SCAN_DENIED"

    # 新增: 配置相关
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
```

**错误码与 HTTP 状态码映射** (用于 SSE 模式和 API 网关集成):

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `UNKNOWN_DATABASE` | 404 Not Found | 资源不存在 |
| `AMBIGUOUS_QUERY` | 400 Bad Request | 请求参数不明确 |
| `UNSAFE_SQL` | 400 Bad Request | 请求内容不安全 |
| `SYNTAX_ERROR` | 400 Bad Request | SQL 语法错误 |
| `TABLE_ACCESS_DENIED` | 403 Forbidden | 表访问被拒绝 |
| `COLUMN_ACCESS_DENIED` | 403 Forbidden | 列访问被拒绝 |
| `SCHEMA_ACCESS_DENIED` | 403 Forbidden | Schema 访问被拒绝 |
| `QUERY_TOO_EXPENSIVE` | 400 Bad Request | 查询代价过高 |
| `SEQ_SCAN_DENIED` | 400 Bad Request | 全表扫描被拒绝 |
| `RATE_LIMIT_EXCEEDED` | 429 Too Many Requests | 速率限制超出 |
| `EXECUTION_TIMEOUT` | 504 Gateway Timeout | 执行超时 |
| `CONNECTION_ERROR` | 503 Service Unavailable | 数据库连接失败 |
| `OPENAI_ERROR` | 502 Bad Gateway | 上游服务错误 |
| `CONFIGURATION_ERROR` | 500 Internal Server Error | 配置错误 |
| `INTERNAL_ERROR` | 500 Internal Server Error | 内部错误 |

### 5.2 配置模型扩展

```python
class DatabaseConfig(BaseModel):
    """扩展: 包含访问策略"""
    # ... 现有字段 ...

    # 新增
    access_policy: AccessPolicyConfig = Field(
        default_factory=AccessPolicyConfig
    )

class ObservabilityConfig(BaseModel):
    """新增: 可观测性配置"""
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

class RetryConfig(BaseModel):
    """新增: 重试配置"""
    openai: OpenAIRetryConfig = Field(default_factory=OpenAIRetryConfig)
    database: DatabaseRetryConfig = Field(default_factory=DatabaseRetryConfig)

class AppConfig(BaseModel):
    """扩展: 应用总配置"""
    # ... 现有字段 ...

    # 新增
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig
    )
    retry: RetryConfig = Field(default_factory=RetryConfig)
```

---

## 6. 非功能需求

### 6.1 性能影响

| 操作 | 预期增加延迟 | 说明 |
|------|-------------|------|
| 访问策略检查 | < 1ms | 内存中策略匹配 |
| EXPLAIN 验证 (缓存命中) | < 1ms | 从缓存读取 |
| EXPLAIN 验证 (缓存未命中) | < 50ms | 需要数据库交互，有 5s 超时保护 |
| 速率限制检查 | < 1ms | 内存中计数器 |
| 指标记录 | < 0.1ms | 异步写入 |
| 追踪记录 | < 0.5ms | 异步导出 |

> **注意**: EXPLAIN 验证配置了 5 秒超时和结果缓存（60 秒 TTL），避免复杂查询阻塞请求。大表行数阈值使用 `pg_class.reltuples` 估算值（来自 Schema 缓存），无需额外查询。

### 6.2 兼容性

- **向后兼容**: 所有新配置项提供合理默认值，现有配置无需修改即可使用
- **API 兼容**: MCP 工具接口保持不变，仅增加新的错误码
- **配置迁移**: 无需迁移，新增字段均为可选

### 6.3 安全考量

- 访问策略配置支持环境变量替换，敏感表/列名不暴露在日志中
- EXPLAIN 输出中的表名做脱敏处理后记录日志
- 追踪数据中不包含 SQL 参数值

---

## 7. 验收标准

### 7.1 功能验收

**P0 - 多数据库与安全控制**:
- [ ] 表级访问控制正确执行
- [ ] 列级访问控制正确执行
- [ ] EXPLAIN 策略正确执行
- [ ] 多数据库路由正确且隔离
- [ ] 审计日志完整记录

**P1 - 弹性与可观测性**:
- [ ] 速率限制在请求流程中生效
- [ ] 重试机制按配置执行
- [ ] Prometheus 指标可采集
- [ ] OpenTelemetry 追踪可导出（如启用）

**P2 - 代码质量**:
- [ ] 无冗余 `to_dict()` 方法
- [ ] 测试覆盖率达标
- [ ] 所有 CI 检查通过

### 7.2 性能验收

- [ ] 新增操作延迟符合预期
- [ ] 内存占用增加 < 50MB
- [ ] 无性能回退（与基线对比）

### 7.3 安全验收

- [ ] 访问控制绕过测试通过
- [ ] SQL 注入 fuzz 测试通过
- [ ] 敏感信息不泄露到日志/追踪

---

## 8. 实施建议

### 8.1 阶段划分

```
Phase A: 安全控制 (优先)
    │
    ├── A.1: AccessPolicyConfig 模型
    ├── A.2: DatabaseAccessPolicy 实现
    ├── A.3: QueryExecutor 重构
    └── A.4: 安全测试
    │
Phase B: 弹性机制
    │
    ├── B.1: RateLimiter 集成
    ├── B.2: RetryExecutor 实现
    └── B.3: 集成测试
    │
Phase C: 可观测性
    │
    ├── C.1: 指标暴露
    ├── C.2: 追踪集成
    └── C.3: 日志增强
    │
Phase D: 代码质量
    │
    ├── D.1: 代码清理
    ├── D.2: 测试补充
    └── D.3: 文档更新
```

### 8.2 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 访问策略配置复杂导致误配置 | 中 | 高 | 提供配置验证工具和示例 |
| 速率限制影响正常用户 | 低 | 中 | 默认值足够宽松，提供监控 |
| EXPLAIN 策略误判合法查询 | 中 | 中 | 可配置阈值，支持白名单 |
| 性能开销超预期 | 低 | 中 | 分阶段实施，持续监控 |

---

## 附录

### 附录 A: SQL 注入测试向量

```python
SQL_INJECTION_PAYLOADS = [
    # 基础注入
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "1; DELETE FROM orders",
    "1 UNION SELECT * FROM users",

    # 盲注
    "1 AND 1=1",
    "1 AND SLEEP(5)",
    "1 AND pg_sleep(5)",

    # 堆叠查询
    "1; INSERT INTO users VALUES (999, 'hacker')",
    "1); TRUNCATE orders; --",

    # 编码绕过
    "1%27%20OR%201%3D1",
    "1/**/OR/**/1=1",

    # PostgreSQL 特有
    "1; COPY users TO '/tmp/users.csv'",
    "1; SELECT lo_import('/etc/passwd')",
    "$$; DROP TABLE users; $$",
]
```

### 附录 B: 数据库最小权限配置指南

为配合访问策略实现双重防护，建议为 MCP Server 配置最小权限数据库用户：

```sql
-- 1. 创建只读用户
CREATE USER mcp_readonly WITH PASSWORD 'secure_password_here';

-- 2. 授予连接权限
GRANT CONNECT ON DATABASE mydb TO mcp_readonly;

-- 3. 授予 Schema 使用权限
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT USAGE ON SCHEMA analytics TO mcp_readonly;

-- 4. 授予表级 SELECT 权限 (仅需要访问的表)
GRANT SELECT ON public.orders TO mcp_readonly;
GRANT SELECT ON public.products TO mcp_readonly;
GRANT SELECT ON public.users TO mcp_readonly;
-- 或批量授予
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO mcp_readonly;

-- 5. 撤销敏感表访问
REVOKE SELECT ON public.user_credentials FROM mcp_readonly;
REVOKE SELECT ON public.payment_tokens FROM mcp_readonly;

-- 6. 设置默认权限 (新建表自动授予 SELECT)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO mcp_readonly;

-- 7. (可选) 列级权限 - PostgreSQL 支持列级 GRANT
-- 注意: 需要先 REVOKE 整表权限，再 GRANT 特定列
REVOKE SELECT ON public.users FROM mcp_readonly;
GRANT SELECT (id, email, name, created_at) ON public.users TO mcp_readonly;
-- 不授予 password_hash, ssn 等敏感列

-- 8. (可选) 限制连接数
ALTER USER mcp_readonly CONNECTION LIMIT 20;

-- 9. (可选) 设置语句超时 (数据库级防护)
ALTER USER mcp_readonly SET statement_timeout = '30s';
```

**验证权限配置**:
```sql
-- 以 mcp_readonly 用户连接后执行
SELECT current_user;  -- 应返回 mcp_readonly

-- 验证可访问的表
SELECT table_name FROM information_schema.table_privileges
WHERE grantee = 'mcp_readonly' AND privilege_type = 'SELECT';

-- 验证无法修改数据
INSERT INTO public.orders (id) VALUES (1);  -- 应失败: permission denied
```

> **最佳实践**: 数据库层权限控制是"纵深防御"的最后一道防线。即使应用层访问策略被绕过，数据库用户权限仍能阻止未授权访问。

### 附录 C: 配置示例

```yaml
# .env 配置示例
PG_MCP_DATABASE_NAME=analytics
PG_MCP_DATABASE_HOST=localhost
PG_MCP_DATABASE_PORT=5432
PG_MCP_DATABASE_USER=mcp_readonly
PG_MCP_DATABASE_PASSWORD=${DB_PASSWORD}

# 访问策略
PG_MCP_ACCESS_ALLOWED_SCHEMAS=["public", "analytics"]
PG_MCP_ACCESS_DENIED_TABLES=["user_credentials", "api_keys"]
PG_MCP_ACCESS_DENIED_COLUMN_PATTERNS=["*password*", "*secret*"]

# EXPLAIN 策略
PG_MCP_EXPLAIN_ENABLED=true
PG_MCP_EXPLAIN_MAX_ESTIMATED_ROWS=100000
PG_MCP_EXPLAIN_DENY_SEQ_SCAN=true

# 速率限制
PG_MCP_RATE_LIMIT_ENABLED=true
PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE=60

# 可观测性
PG_MCP_METRICS_ENABLED=true
PG_MCP_METRICS_PORT=9090
PG_MCP_TRACING_ENABLED=false
```

---

## 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-14 | 初始版本 | - |
| 1.1 | 2026-01-14 | 根据审查报告修订: (1) 明确 enable_result_validation 处理方案; (2) 补充审计日志存储格式定义; (3) 修正 per_client_per_minute 适用范围; (4) 完善列级访问控制策略和降级方案; (5) 添加 EXPLAIN 性能优化措施; (6) 统一测试覆盖率目标; (7) 补充错误码 HTTP 状态码映射; (8) 添加数据库最小权限配置指南 (附录 B); (9) 明确 QueryExecutor 与 QueryService 关系; (10) 添加配置冲突检测说明和验证命令 | - |
