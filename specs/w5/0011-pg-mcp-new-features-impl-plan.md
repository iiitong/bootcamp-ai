# PostgreSQL MCP Server 增强功能实施计划

**版本**: 1.0
**日期**: 2026-01-15
**状态**: 待评审
**关联文档**:
- [0009-pg-mcp-new-features-prd.md](./0009-pg-mcp-new-features-prd.md) - 需求文档
- [0010-pg-mcp-new-features-design.md](./0010-pg-mcp-new-features-design.md) - 设计文档

---

## 1. 实施概述

### 1.1 背景

本实施计划基于 PRD 和设计文档，详细规划 PostgreSQL MCP Server 增强功能的开发任务。增强功能涵盖四个主要领域：

| 领域 | 优先级 | 核心功能 |
|------|--------|----------|
| 安全控制 (Phase A) | P0 | 访问策略执行器、EXPLAIN 验证、审计日志 |
| 弹性机制 (Phase B) | P1 | 速率限制集成、智能重试与退避 |
| 可观测性 (Phase C) | P1 | Prometheus 指标、OpenTelemetry 追踪 |
| 代码质量 (Phase D) | P2 | 代码清理、测试覆盖增强 |

### 1.2 当前代码结构

```
w5/pg-mcp/
├── src/pg_mcp/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── models.py           # 配置模型
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库连接池
│   │   ├── openai_client.py    # OpenAI 客户端
│   │   ├── rate_limiter.py     # 速率限制器 (需重构)
│   │   ├── schema_cache.py     # Schema 缓存
│   │   └── sql_parser.py       # SQL 解析器 (需扩展)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── errors.py           # 错误模型 (需扩展)
│   │   ├── query.py            # 查询模型
│   │   └── schema.py           # Schema 模型
│   ├── services/
│   │   ├── __init__.py
│   │   └── query_service.py    # 查询服务 (需重构)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── env.py
│   │   └── logging.py          # 日志 (需移动)
│   ├── __init__.py
│   ├── __main__.py
│   └── server.py               # MCP 服务器
└── tests/
    └── ...
```

### 1.3 新增模块结构

```
w5/pg-mcp/
├── src/pg_mcp/
│   ├── security/               # [NEW] 安全控制模块
│   │   ├── __init__.py
│   │   ├── access_policy.py    # 访问策略执行器
│   │   ├── explain_validator.py # EXPLAIN 策略验证
│   │   └── audit_logger.py     # 审计日志
│   ├── resilience/             # [NEW] 弹性机制模块
│   │   ├── __init__.py
│   │   ├── rate_limiter.py     # 速率限制器 (重构移动)
│   │   ├── retry_executor.py   # 重试执行器
│   │   └── backoff.py          # 退避策略
│   ├── observability/          # [NEW] 可观测性模块
│   │   ├── __init__.py
│   │   ├── metrics.py          # Prometheus 指标
│   │   ├── tracing.py          # OpenTelemetry 追踪
│   │   └── logging.py          # 日志增强 (移动)
│   ├── services/
│   │   ├── query_executor.py   # [NEW] 查询执行器
│   │   └── query_executor_manager.py  # [NEW] 执行器管理器
│   └── config/
│       └── validators.py       # [NEW] 配置验证器
└── tests/
    ├── unit/
    │   ├── security/           # [NEW]
    │   └── resilience/         # [NEW]
    ├── integration/            # [NEW]
    └── security/               # [NEW] 安全测试
```

### 1.4 技术依赖新增

```toml
# pyproject.toml 新增依赖
[project.dependencies]
prometheus-client = "^0.20"
cachetools = "^5.3"

[project.optional-dependencies]
tracing = [
    "opentelemetry-api>=1.24",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-exporter-otlp>=1.24",
]
dev = [
    "testcontainers>=4.0",
]
```

---

## 2. 阶段划分与依赖关系

### 2.1 阶段依赖图

```
Phase A: 安全控制 (P0)
│
├── A.1 数据模型扩展 ─────────┬──> A.2 访问策略执行器
│                            │
│                            └──> A.3 EXPLAIN 验证器
│                                        │
│                                        ▼
├────────────────────────────────> A.4 查询执行器重构
│                                        │
│                                        ▼
└────────────────────────────────> A.5 审计日志
                                         │
                                         ▼
Phase B: 弹性机制 (P1) ──────────────────────────
│
├── B.1 速率限制重构与集成
│
├── B.2 退避策略实现
│
└── B.3 重试执行器
         │
         ▼
Phase C: 可观测性 (P1) ──────────────────────────
│
├── C.1 Prometheus 指标
│
├── C.2 OpenTelemetry 追踪
│
└── C.3 日志增强
         │
         ▼
Phase D: 代码质量 (P2) ──────────────────────────
│
├── D.1 代码清理
│
├── D.2 测试覆盖增强
│
└── D.3 配置验证工具
```

### 2.2 阶段复杂度与风险

| 阶段 | 复杂度 | 关键风险点 |
|------|--------|-----------|
| Phase A | 高 | 访问策略配置复杂度、SQL 解析器扩展 |
| Phase B | 中 | 速率限制与现有代码集成 |
| Phase C | 中 | OpenTelemetry 依赖可选安装 |
| Phase D | 低 | 达到目标测试覆盖率 |

---

## 3. Phase A: 安全控制

### 3.1 任务 A.1: 数据模型扩展

**目标**: 定义安全控制所需的配置模型和错误类型

**前置条件**: 无

**输出文件**:
- `src/pg_mcp/config/models.py` (扩展)
- `src/pg_mcp/models/errors.py` (扩展)

#### A.1.1 扩展配置模型

**文件**: `src/pg_mcp/config/models.py`

**新增内容**:

```python
# 1. 枚举类型
class OnDeniedAction(str, Enum):
    """敏感列访问时的处理策略"""
    REJECT = "reject"
    FILTER = "filter"

class SelectStarPolicy(str, Enum):
    """SELECT * 处理策略"""
    REJECT = "reject"
    EXPAND_SAFE = "expand_safe"

# 2. 访问控制配置
class TableAccessConfig(BaseModel):
    """表访问控制配置"""
    allowed: list[str] = Field(default_factory=list)
    denied: list[str] = Field(default_factory=list)

class ColumnAccessConfig(BaseModel):
    """列访问控制配置"""
    denied: list[str] = Field(default_factory=list)
    denied_patterns: list[str] = Field(default_factory=list)
    on_denied: OnDeniedAction = OnDeniedAction.REJECT
    select_star_policy: SelectStarPolicy = SelectStarPolicy.REJECT

class ExplainPolicyConfig(BaseModel):
    """EXPLAIN 策略配置"""
    enabled: bool = True
    max_estimated_rows: int = 100000
    max_estimated_cost: float = 10000.0
    deny_seq_scan_on_large_tables: bool = True
    large_table_threshold: int = 10000
    timeout_seconds: float = 5.0
    cache_ttl_seconds: int = 60
    cache_max_size: int = 1000

class AccessPolicyConfig(BaseModel):
    """数据库访问策略配置"""
    allowed_schemas: list[str] = Field(default=["public"])
    tables: TableAccessConfig = Field(default_factory=TableAccessConfig)
    columns: ColumnAccessConfig = Field(default_factory=ColumnAccessConfig)
    explain_policy: ExplainPolicyConfig = Field(default_factory=ExplainPolicyConfig)

    def validate_consistency(self) -> list[str]:
        """验证配置一致性，返回警告列表"""
        ...

# 3. 扩展 DatabaseConfig
class DatabaseConfig(BaseModel):
    # ... 现有字段 ...
    access_policy: AccessPolicyConfig = Field(default_factory=AccessPolicyConfig)

# 4. 审计配置
class AuditConfig(BaseModel):
    enabled: bool = True
    storage: str = "file"  # file, stdout, database
    file_path: str | None = None
    max_size_mb: int = 100
    max_files: int = 10
    redact_sql: bool = False

# 5. 可观测性配置 (为 Phase C 预留)
class MetricsConfig(BaseModel):
    enabled: bool = True
    exporter: str = "prometheus"
    port: int = 9090
    path: str = "/metrics"

class TracingConfig(BaseModel):
    enabled: bool = False
    exporter: str = "otlp"
    endpoint: str = "http://localhost:4317"
    sample_rate: float = 0.1
    service_name: str = "pg-mcp"

class LoggingConfig(BaseModel):
    include_trace_id: bool = True
    log_sql: bool = False
    slow_query_threshold: float = 5.0

class ObservabilityConfig(BaseModel):
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

# 6. 扩展 AppConfig
class AppConfig(BaseModel):
    # ... 现有字段 ...
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
```

#### A.1.2 扩展错误模型

**文件**: `src/pg_mcp/models/errors.py`

**新增内容**:

```python
class ErrorCode(str, Enum):
    # ... 现有错误码 ...

    # 访问控制相关
    ACCESS_DENIED = "ACCESS_DENIED"
    TABLE_ACCESS_DENIED = "TABLE_ACCESS_DENIED"
    COLUMN_ACCESS_DENIED = "COLUMN_ACCESS_DENIED"
    SCHEMA_ACCESS_DENIED = "SCHEMA_ACCESS_DENIED"

    # EXPLAIN 策略相关
    QUERY_TOO_EXPENSIVE = "QUERY_TOO_EXPENSIVE"
    SEQ_SCAN_DENIED = "SEQ_SCAN_DENIED"

    # 配置相关
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

# HTTP 状态码映射
ERROR_HTTP_STATUS_MAP = {
    ErrorCode.UNKNOWN_DATABASE: 404,
    ErrorCode.TABLE_ACCESS_DENIED: 403,
    ErrorCode.COLUMN_ACCESS_DENIED: 403,
    ErrorCode.SCHEMA_ACCESS_DENIED: 403,
    ErrorCode.QUERY_TOO_EXPENSIVE: 400,
    ErrorCode.SEQ_SCAN_DENIED: 400,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    # ... 其他映射
}
```

#### A.1.3 测试用例

**文件**: `tests/unit/config/test_access_policy_config.py`

```python
class TestAccessPolicyConfig:
    def test_default_values(self):
        """测试默认配置值"""

    def test_table_access_validation(self):
        """测试表访问配置验证"""

    def test_column_format_validation(self):
        """测试列格式必须为 table.column"""

    def test_consistency_validation_table_conflict(self):
        """测试表同时在 allowed 和 denied 中的冲突检测"""

    def test_consistency_validation_pattern_warning(self):
        """测试过于宽泛的列模式警告"""
```

**验收标准**:
- [ ] 所有新配置模型通过 Pydantic 验证
- [ ] `validate_consistency()` 正确检测配置冲突
- [ ] 列格式验证 (`table.column`) 正常工作
- [ ] 单元测试覆盖率 >= 95%

---

### 3.2 任务 A.2: 访问策略执行器

**目标**: 实现 Schema/表/列级访问控制

**前置条件**: A.1 完成

**输出文件**:
- `src/pg_mcp/security/__init__.py`
- `src/pg_mcp/security/access_policy.py`

#### A.2.1 创建安全模块

**文件**: `src/pg_mcp/security/__init__.py`

```python
from pg_mcp.security.access_policy import (
    DatabaseAccessPolicy,
    PolicyValidationResult,
    PolicyViolation,
    TableAccessDeniedError,
    ColumnAccessDeniedError,
    SchemaAccessDeniedError,
)

__all__ = [
    "DatabaseAccessPolicy",
    "PolicyValidationResult",
    "PolicyViolation",
    "TableAccessDeniedError",
    "ColumnAccessDeniedError",
    "SchemaAccessDeniedError",
]
```

#### A.2.2 实现访问策略执行器

**文件**: `src/pg_mcp/security/access_policy.py`

**核心类**:

```python
@dataclass
class PolicyViolation:
    """策略违规详情"""
    check_type: str  # "schema", "table", "column"
    resource: str
    reason: str

class PolicyValidationResult(NamedTuple):
    """策略验证结果"""
    passed: bool
    violations: list[PolicyViolation]
    warnings: list[str]
    rewritten_sql: str | None = None

class DatabaseAccessPolicy:
    """数据库访问策略执行器"""

    def __init__(self, config: AccessPolicyConfig):
        ...

    def validate_schema(self, schema: str) -> PolicyValidationResult:
        """验证 Schema 访问权限"""
        ...

    def validate_tables(self, tables: list[str]) -> PolicyValidationResult:
        """验证表访问权限（白名单优先于黑名单）"""
        ...

    def validate_columns(
        self,
        columns: list[tuple[str, str]],
        is_select_star: bool = False
    ) -> PolicyValidationResult:
        """验证列访问权限"""
        ...

    def get_safe_columns(
        self,
        table: str,
        all_columns: list[str]
    ) -> list[str]:
        """获取表的安全列列表（用于 SELECT * 展开）"""
        ...

    def validate_sql(
        self,
        parsed_result: ParsedSQLInfo
    ) -> PolicyValidationResult:
        """完整的 SQL 策略验证"""
        ...
```

**异常类**:

```python
class TableAccessDeniedError(PgMcpError):
    """表访问被拒绝"""
    def __init__(self, tables: list[str]):
        super().__init__(
            ErrorCode.TABLE_ACCESS_DENIED,
            f"Access denied to tables: {', '.join(tables)}",
            {"denied_tables": tables}
        )

class ColumnAccessDeniedError(PgMcpError):
    """列访问被拒绝"""
    def __init__(self, columns: list[str], is_select_star: bool = False):
        ...

class SchemaAccessDeniedError(PgMcpError):
    """Schema 访问被拒绝"""
    def __init__(self, schema: str, allowed: list[str]):
        ...
```

#### A.2.3 扩展 SQL 解析器

**文件**: `src/pg_mcp/infrastructure/sql_parser.py` (扩展)

**新增数据结构**:

```python
@dataclass
class ParsedSQLInfo:
    """SQL 解析结果（用于访问策略验证）"""
    sql: str
    schemas: list[str] = field(default_factory=lambda: ["public"])
    tables: list[str] = field(default_factory=list)
    columns: list[tuple[str, str]] = field(default_factory=list)
    has_select_star: bool = False
    select_star_tables: list[str] = field(default_factory=list)
    is_readonly: bool = True
    error_message: str | None = None

class SQLParser:
    """SQL 解析器（扩展）"""

    def parse(self, sql: str) -> ParsedSQLInfo:
        """解析 SQL 并提取结构化信息"""
        ...

    def _extract_tables(self, ast) -> list[str]:
        """从 AST 提取表名"""
        ...

    def _extract_columns(self, ast) -> list[tuple[str, str]]:
        """从 AST 提取列名（含表前缀）"""
        ...

    def _detect_select_star(self, ast) -> tuple[bool, list[str]]:
        """检测 SELECT * 及涉及的表"""
        ...
```

#### A.2.4 测试用例

**文件**: `tests/unit/security/test_access_policy.py`

```python
class TestDatabaseAccessPolicy:
    # Schema 验证测试
    def test_schema_allowed(self):
        """测试允许的 Schema 访问"""

    def test_schema_denied(self):
        """测试被拒绝的 Schema 访问"""

    # 表访问测试
    def test_table_whitelist_mode(self):
        """测试白名单模式：仅 allowed 中的表可访问"""

    def test_table_blacklist_mode(self):
        """测试黑名单模式：denied 中的表不可访问"""

    def test_table_whitelist_priority(self):
        """测试白名单优先级高于黑名单"""

    # 列访问测试
    def test_column_explicit_denied(self):
        """测试显式禁止列"""

    def test_column_pattern_match(self):
        """测试列名模式匹配（如 *._password*）"""

    def test_select_star_reject_policy(self):
        """测试 SELECT * 拒绝策略"""

    def test_select_star_expand_safe_policy(self):
        """测试 SELECT * 安全展开策略"""

    # 完整 SQL 验证
    def test_validate_sql_all_passed(self):
        """测试完全合规的 SQL"""

    def test_validate_sql_multiple_violations(self):
        """测试多个违规情况"""

class TestParsedSQLInfo:
    def test_extract_tables_simple(self):
        """测试简单 SELECT 的表提取"""

    def test_extract_tables_join(self):
        """测试 JOIN 查询的表提取"""

    def test_extract_columns(self):
        """测试列提取"""

    def test_detect_select_star(self):
        """测试 SELECT * 检测"""
```

**验收标准**:
- [ ] Schema 验证正确拒绝未授权 Schema
- [ ] 表白名单模式正确工作
- [ ] 表黑名单模式正确工作
- [ ] 列显式禁止列表正确工作
- [ ] 列模式匹配正确工作
- [ ] SELECT * 两种策略正确工作
- [ ] 单元测试覆盖率 >= 95%

---

### 3.3 任务 A.3: EXPLAIN 验证器

**目标**: 实现基于 EXPLAIN 的查询计划验证

**前置条件**: A.1 完成

**输出文件**:
- `src/pg_mcp/security/explain_validator.py`

#### A.3.1 实现 EXPLAIN 验证器

**文件**: `src/pg_mcp/security/explain_validator.py`

**核心类**:

```python
@dataclass
class ExplainResult:
    """EXPLAIN 分析结果"""
    total_cost: float
    estimated_rows: int
    plan_nodes: list[dict]
    has_seq_scan: bool
    seq_scan_tables: list[tuple[str, int]]
    raw_plan: dict

@dataclass
class ExplainValidationResult:
    """EXPLAIN 验证结果"""
    passed: bool
    result: ExplainResult | None
    error_message: str | None = None
    warnings: list[str] | None = None

class ExplainValidator:
    """EXPLAIN 策略验证器"""

    def __init__(
        self,
        config: ExplainPolicyConfig,
        table_row_counts: dict[str, int] | None = None
    ):
        self.config = config
        self.table_row_counts = table_row_counts or {}
        self._cache: TTLCache = TTLCache(
            maxsize=config.cache_max_size,
            ttl=config.cache_ttl_seconds
        )

    async def validate(
        self,
        conn: Connection,
        sql: str
    ) -> ExplainValidationResult:
        """验证 SQL 的查询计划"""
        ...

    def _parse_explain(self, explain_json: list[dict]) -> ExplainResult:
        """解析 EXPLAIN JSON 输出"""
        ...

    def _validate_result(self, result: ExplainResult) -> ExplainValidationResult:
        """根据策略验证 EXPLAIN 结果"""
        ...

    def update_table_row_counts(self, counts: dict[str, int]) -> None:
        """更新表行数估算"""
        ...

class QueryTooExpensiveError(PgMcpError):
    """查询代价过高"""
    ...

class SeqScanDeniedError(PgMcpError):
    """全表扫描被拒绝"""
    ...
```

**关键实现细节**:

1. **缓存策略**: 使用 `cachetools.TTLCache` 缓存 EXPLAIN 结果
   - 缓存键: SQL 的 SHA256 哈希前 16 位
   - TTL: 配置项 `cache_ttl_seconds` (默认 60 秒)
   - 最大条目: 配置项 `cache_max_size` (默认 1000)

2. **超时保护**: EXPLAIN 执行有独立超时 (默认 5 秒)

3. **大表判断**: 优先使用 Schema 缓存的 `pg_class.reltuples`，避免额外查询

4. **失败降级**: EXPLAIN 执行失败时记录警告但不阻止查询

#### A.3.2 测试用例

**文件**: `tests/unit/security/test_explain_validator.py`

```python
class TestExplainValidator:
    def test_cache_hit(self):
        """测试缓存命中"""

    def test_cache_miss(self):
        """测试缓存未命中"""

    def test_estimated_rows_exceed_limit(self):
        """测试估算行数超限拒绝"""

    def test_estimated_cost_warning(self):
        """测试估算成本超限警告（不拒绝）"""

    def test_seq_scan_on_large_table_denied(self):
        """测试大表全表扫描拒绝"""

    def test_seq_scan_on_small_table_allowed(self):
        """测试小表全表扫描允许"""

    def test_explain_timeout(self):
        """测试 EXPLAIN 超时处理"""

    def test_explain_failure_graceful(self):
        """测试 EXPLAIN 失败时优雅降级"""

    def test_disabled_policy(self):
        """测试禁用 EXPLAIN 策略"""
```

**验收标准**:
- [ ] 缓存机制正确工作
- [ ] 超时保护正确工作
- [ ] 估算行数超限正确拒绝
- [ ] 估算成本超限正确警告
- [ ] 大表全表扫描正确拒绝
- [ ] 小表全表扫描正确允许
- [ ] 单元测试覆盖率 >= 90%

---

### 3.4 任务 A.4: 查询执行器重构

**目标**: 实现 QueryExecutor 和 QueryExecutorManager，将访问策略集成到查询执行流程

**前置条件**: A.2, A.3 完成

**输出文件**:
- `src/pg_mcp/services/query_executor.py`
- `src/pg_mcp/services/query_executor_manager.py`
- `src/pg_mcp/services/query_service.py` (修改)

#### A.4.1 实现查询执行器

**文件**: `src/pg_mcp/services/query_executor.py`

```python
@dataclass
class ExecutionContext:
    """执行上下文"""
    request_id: str
    client_ip: str | None
    session_id: str | None

class QueryExecutor:
    """
    单数据库查询执行器

    职责:
    - 持有数据库连接池和访问策略
    - 在 SQL 执行前强制应用访问策略
    - 记录审计日志
    """

    def __init__(
        self,
        database_name: str,
        pool: DatabasePool,
        access_policy: DatabaseAccessPolicy,
        explain_validator: ExplainValidator,
        audit_logger: AuditLogger,
        sql_parser: SQLParser
    ):
        ...

    async def execute(
        self,
        sql: str,
        limit: int,
        context: ExecutionContext,
        question: str = ""
    ) -> QueryResult:
        """执行查询（带策略检查）"""
        # 1. 解析 SQL
        # 2. 访问策略检查
        # 3. EXPLAIN 策略检查
        # 4. 执行查询
        # 5. 构建结果
        # 6. 记录审计日志
        ...
```

#### A.4.2 实现执行器管理器

**文件**: `src/pg_mcp/services/query_executor_manager.py`

```python
class AmbiguousDatabaseError(PgMcpError):
    """数据库选择不明确"""
    def __init__(self, available: list[str]):
        ...

class QueryExecutorManager:
    """
    查询执行器管理器

    职责:
    - 为每个数据库创建独立的 QueryExecutor
    - 根据请求路由到正确的执行器
    """

    def __init__(
        self,
        pool_manager: DatabasePoolManager,
        sql_parser: SQLParser,
        audit_logger: AuditLogger
    ):
        ...

    def register_database(
        self,
        config: DatabaseConfig,
        access_policy_config: AccessPolicyConfig | None = None
    ) -> None:
        """注册数据库并创建对应的执行器"""
        ...

    def get_executor(self, database: str | None = None) -> QueryExecutor:
        """获取指定数据库的执行器"""
        # 单库时自动选择
        # 多库未指定时抛出 AmbiguousDatabaseError
        ...

    def list_databases(self) -> list[str]:
        """列出所有已注册的数据库"""
        ...

    async def close_all(self) -> None:
        """关闭所有执行器"""
        ...
```

#### A.4.3 重构 QueryService

**文件**: `src/pg_mcp/services/query_service.py` (修改)

**主要变更**:

```python
class QueryService:
    """
    查询服务（重构）

    职责变更:
    - 保留: SQL 生成、重试逻辑、结果格式化
    - 委托: SQL 执行委托给 QueryExecutor
    - 移除: 直接持有 DatabasePool
    """

    def __init__(
        self,
        executor_manager: QueryExecutorManager,  # [NEW]
        openai_client: OpenAIClient,
        schema_cache: SchemaCacheManager,
        config: ServerConfig,
        rate_limiter: RateLimiter | None = None,  # [NEW]
        metrics: MetricsCollector | None = None,  # [NEW]
    ):
        ...

    async def query(
        self,
        request: QueryRequest,
        context: ExecutionContext  # [NEW]
    ) -> QueryResponse:
        """处理自然语言查询"""
        # 1. 速率限制检查（如启用）
        # 2. 获取目标数据库的执行器
        # 3. 生成 SQL（含重试）
        # 4. 委托执行器执行（策略检查在执行器内部）
        # 5. 结果验证（可选）
        # 6. 记录 Token 消耗
        ...

    async def _validate_empty_result(
        self,
        sql: str,
        question: str,
        database: str
    ) -> None:
        """验证空结果（enable_result_validation 功能）"""
        ...
```

#### A.4.4 测试用例

**文件**: `tests/unit/services/test_query_executor.py`

```python
class TestQueryExecutor:
    async def test_execute_success(self):
        """测试成功执行查询"""

    async def test_execute_table_access_denied(self):
        """测试表访问被拒绝"""

    async def test_execute_column_access_denied(self):
        """测试列访问被拒绝"""

    async def test_execute_explain_denied(self):
        """测试 EXPLAIN 策略拒绝"""

    async def test_audit_log_on_success(self):
        """测试成功时记录审计日志"""

    async def test_audit_log_on_failure(self):
        """测试失败时记录审计日志"""

class TestQueryExecutorManager:
    def test_register_database(self):
        """测试注册数据库"""

    def test_get_executor_single_db(self):
        """测试单数据库自动选择"""

    def test_get_executor_multi_db_specified(self):
        """测试多数据库指定选择"""

    def test_get_executor_multi_db_not_specified(self):
        """测试多数据库未指定时抛出异常"""

    def test_get_executor_unknown_db(self):
        """测试未知数据库"""
```

**文件**: `tests/integration/test_security_flow.py`

```python
class TestSecurityFlow:
    """安全流程集成测试"""

    @pytest.fixture
    async def real_database(self, postgres_container):
        """使用真实 PostgreSQL 容器"""
        ...

    async def test_full_query_flow_success(self, real_database):
        """测试完整查询流程成功"""

    async def test_full_query_flow_table_denied(self, real_database):
        """测试表访问拒绝流程"""

    async def test_full_query_flow_explain_denied(self, real_database):
        """测试 EXPLAIN 策略拒绝流程"""
```

**验收标准**:
- [ ] QueryExecutor 正确集成访问策略检查
- [ ] QueryExecutor 正确集成 EXPLAIN 策略检查
- [ ] QueryExecutorManager 正确管理多数据库
- [ ] 单库时自动选择执行器
- [ ] 多库未指定时返回明确错误
- [ ] QueryService 成功委托执行
- [ ] 审计日志正确记录
- [ ] 集成测试通过

---

### 3.5 任务 A.5: 审计日志

**目标**: 实现审计日志记录器

**前置条件**: A.1 完成

**输出文件**:
- `src/pg_mcp/security/audit_logger.py`

#### A.5.1 实现审计日志记录器

**文件**: `src/pg_mcp/security/audit_logger.py`

```python
class AuditEventType(str, Enum):
    """审计事件类型"""
    QUERY_EXECUTED = "query_executed"
    QUERY_DENIED = "query_denied"
    POLICY_VIOLATION = "policy_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

class AuditStorage(str, Enum):
    """审计日志存储方式"""
    FILE = "file"
    STDOUT = "stdout"
    DATABASE = "database"

@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: str
    event_type: AuditEventType
    request_id: str
    session_id: str | None
    database: str
    client_info: ClientInfo
    query: QueryInfo | None
    result: ResultInfo | None
    policy_checks: PolicyCheckInfo | None

    def to_dict(self) -> dict:
        ...

    def to_json(self) -> str:
        ...

class AuditLogger:
    """审计日志记录器"""

    def __init__(
        self,
        storage: AuditStorage = AuditStorage.STDOUT,
        file_path: str | None = None,
        max_size_mb: int = 100,
        max_files: int = 10,
        redact_sql: bool = False
    ):
        ...

    async def log(self, event: AuditEvent) -> None:
        """记录审计事件"""
        ...

    async def _write_to_file(self, line: str) -> None:
        """写入文件（带轮转，使用 asyncio.to_thread 避免阻塞）"""
        ...

    async def _rotate(self) -> None:
        """轮转日志文件"""
        ...

    @staticmethod
    def create_event(...) -> AuditEvent:
        """创建审计事件的便捷方法"""
        ...
```

#### A.5.2 测试用例

**文件**: `tests/unit/security/test_audit_logger.py`

```python
class TestAuditLogger:
    async def test_log_to_stdout(self):
        """测试输出到 stdout"""

    async def test_log_to_file(self, tmp_path):
        """测试输出到文件"""

    async def test_file_rotation(self, tmp_path):
        """测试文件轮转"""

    async def test_create_event(self):
        """测试创建审计事件"""

    def test_event_to_json(self):
        """测试事件 JSON 序列化"""
```

**验收标准**:
- [ ] stdout 输出正确
- [ ] 文件输出正确
- [ ] 文件轮转正确工作
- [ ] JSON 序列化正确
- [ ] 异步 IO 不阻塞事件循环

---

## 4. Phase B: 弹性机制

### 4.1 任务 B.1: 速率限制重构与集成

**目标**: 将速率限制器集成到请求处理流程

**前置条件**: Phase A 完成

**输出文件**:
- `src/pg_mcp/resilience/__init__.py`
- `src/pg_mcp/resilience/rate_limiter.py` (从 infrastructure 移动并重构)

#### B.1.1 创建弹性模块

**文件**: `src/pg_mcp/resilience/__init__.py`

```python
from pg_mcp.resilience.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RateLimitStrategy,
)
from pg_mcp.resilience.retry_executor import (
    RetryExecutor,
    RetryConfig,
    OpenAIRetryExecutor,
    DatabaseRetryExecutor,
)
from pg_mcp.resilience.backoff import (
    BackoffStrategy,
    ExponentialBackoff,
    FixedBackoff,
    FibonacciBackoff,
)

__all__ = [...]
```

#### B.1.2 重构速率限制器

**文件**: `src/pg_mcp/resilience/rate_limiter.py`

**主要增强**:

1. **客户端级限制**: 支持按 IP 或 session 限制
2. **Token 限制**: 支持 Token 消耗限制
3. **策略配置**: 支持 reject/queue/delay 策略
4. **响应头**: 支持标准速率限制响应头

```python
class RateLimiter:
    """速率限制器"""

    def __init__(self, config: RateLimitConfig):
        ...

    def check_request(
        self,
        client_ip: str | None = None,
        session_id: str | None = None
    ) -> RateLimitResult:
        """检查请求是否被允许"""
        ...

    def record_tokens(self, tokens_used: int) -> RateLimitResult:
        """记录 Token 消耗"""
        ...

    def get_headers(self) -> Dict[str, str]:
        """获取速率限制响应头"""
        ...

    def cleanup_stale_buckets(self, max_age: float = 3600.0) -> int:
        """清理过期的客户端桶"""
        ...
```

#### B.1.3 集成到 QueryService

**修改**: `src/pg_mcp/services/query_service.py`

在 `query()` 方法开头添加速率限制检查：

```python
async def query(self, request: QueryRequest, context: ExecutionContext) -> QueryResponse:
    # 1. 速率限制检查（前置）
    if self.rate_limiter:
        rate_result = self.rate_limiter.check_request(
            client_ip=context.client_ip,
            session_id=context.session_id
        )
        if not rate_result.allowed:
            raise RateLimitExceededError(retry_after=rate_result.retry_after)

    # ... 后续流程 ...

    # 6. 记录 Token 消耗（后置）
    if self.rate_limiter:
        self.rate_limiter.record_tokens(sql_result.tokens_used)
```

#### B.1.4 测试用例

**文件**: `tests/unit/resilience/test_rate_limiter.py`

```python
class TestRateLimiter:
    def test_global_minute_limit(self):
        """测试全局每分钟限制"""

    def test_global_hour_limit(self):
        """测试全局每小时限制"""

    def test_per_client_limit_by_ip(self):
        """测试按 IP 的客户端限制"""

    def test_per_client_limit_by_session(self):
        """测试按 session 的客户端限制"""

    def test_token_limit(self):
        """测试 Token 消耗限制"""

    def test_disabled_rate_limit(self):
        """测试禁用速率限制"""

    def test_get_headers(self):
        """测试响应头生成"""

    def test_cleanup_stale_buckets(self):
        """测试清理过期桶"""
```

**验收标准**:
- [ ] 全局限制正确工作
- [ ] 客户端限制正确工作
- [ ] Token 限制正确工作
- [ ] 响应头正确生成
- [ ] 集成到 QueryService 后端到端测试通过

---

### 4.2 任务 B.2: 退避策略实现

**目标**: 实现多种退避策略

**前置条件**: B.1 完成

**输出文件**:
- `src/pg_mcp/resilience/backoff.py`

#### B.2.1 实现退避策略

**文件**: `src/pg_mcp/resilience/backoff.py`

```python
class BackoffStrategyType(str, Enum):
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"

class BackoffStrategy(ABC):
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """计算第 N 次重试前的等待时间"""
        pass

@dataclass
class ExponentialBackoff(BackoffStrategy):
    """指数退避：delay = min(initial * multiplier^attempt + jitter, max)"""
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        ...

@dataclass
class FixedBackoff(BackoffStrategy):
    """固定间隔退避"""
    delay: float = 1.0

    def get_delay(self, attempt: int) -> float:
        return self.delay

@dataclass
class FibonacciBackoff(BackoffStrategy):
    """斐波那契退避：delay = fib(attempt) * base"""
    base_delay: float = 1.0
    max_delay: float = 30.0

    def get_delay(self, attempt: int) -> float:
        ...

def create_backoff_strategy(strategy_type: BackoffStrategyType, **kwargs) -> BackoffStrategy:
    """工厂方法"""
    ...
```

#### B.2.2 测试用例

**文件**: `tests/unit/resilience/test_backoff.py`

```python
class TestExponentialBackoff:
    def test_delay_progression(self):
        """测试延迟递增"""

    def test_max_delay_cap(self):
        """测试最大延迟上限"""

    def test_jitter(self):
        """测试抖动在合理范围内"""

class TestFixedBackoff:
    def test_constant_delay(self):
        """测试固定延迟"""

class TestFibonacciBackoff:
    def test_fibonacci_progression(self):
        """测试斐波那契数列递增"""

    def test_max_delay_cap(self):
        """测试最大延迟上限"""
```

---

### 4.3 任务 B.3: 重试执行器

**目标**: 实现带重试的执行器

**前置条件**: B.2 完成

**输出文件**:
- `src/pg_mcp/resilience/retry_executor.py`

#### B.3.1 实现重试执行器

**文件**: `src/pg_mcp/resilience/retry_executor.py`

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    retryable_errors: Set[str] = field(default_factory=...)

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

    def _is_default_retryable(self, error: Exception) -> bool:
        """默认的可重试判断"""
        ...

class OpenAIRetryExecutor(RetryExecutor):
    """OpenAI API 专用重试执行器"""

    def _is_default_retryable(self, error: Exception) -> bool:
        # RateLimitError, APITimeoutError, InternalServerError 可重试
        # AuthenticationError, InvalidRequestError 不可重试
        ...

class DatabaseRetryExecutor(RetryExecutor):
    """数据库操作专用重试执行器"""

    def _is_default_retryable(self, error: Exception) -> bool:
        # connection lost, timeout 可重试
        # syntax error 不可重试
        ...
```

#### B.3.2 集成到 QueryService

**修改**: `src/pg_mcp/services/query_service.py`

在 SQL 生成和数据库执行环节使用重试执行器：

```python
class QueryService:
    def __init__(
        self,
        ...,
        openai_retry: OpenAIRetryExecutor | None = None,
        db_retry: DatabaseRetryExecutor | None = None,
    ):
        ...

    async def _generate_sql_with_retry(self, question: str, database: str) -> SQLResult:
        if self.openai_retry:
            return await self.openai_retry.execute_with_retry(
                lambda: self._generate_sql(question, database),
                "sql_generation"
            )
        return await self._generate_sql(question, database)
```

#### B.3.3 测试用例

**文件**: `tests/unit/resilience/test_retry_executor.py`

```python
class TestRetryExecutor:
    async def test_success_no_retry(self):
        """测试成功时不重试"""

    async def test_retry_on_retryable_error(self):
        """测试可重试错误时重试"""

    async def test_no_retry_on_non_retryable_error(self):
        """测试不可重试错误时立即失败"""

    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""

    async def test_custom_retryable_function(self):
        """测试自定义可重试判断函数"""

class TestOpenAIRetryExecutor:
    async def test_retry_on_rate_limit(self):
        """测试 RateLimitError 重试"""

    async def test_no_retry_on_auth_error(self):
        """测试 AuthenticationError 不重试"""

class TestDatabaseRetryExecutor:
    async def test_retry_on_connection_lost(self):
        """测试连接丢失重试"""

    async def test_no_retry_on_syntax_error(self):
        """测试语法错误不重试"""
```

**验收标准**:
- [ ] 退避策略正确计算延迟
- [ ] 重试执行器按配置重试
- [ ] 非可重试错误立即失败
- [ ] 最大重试次数正确限制
- [ ] 日志记录每次重试尝试
- [ ] 单元测试覆盖率 >= 85%

---

## 5. Phase C: 可观测性

### 5.1 任务 C.1: Prometheus 指标

**目标**: 实现 Prometheus 指标收集和暴露

**前置条件**: Phase B 完成

**输出文件**:
- `src/pg_mcp/observability/__init__.py`
- `src/pg_mcp/observability/metrics.py`

#### C.1.1 创建可观测性模块

**文件**: `src/pg_mcp/observability/__init__.py`

```python
from pg_mcp.observability.metrics import MetricsCollector
from pg_mcp.observability.tracing import TracingManager, init_tracing
from pg_mcp.observability.logging import setup_logging, SlowQueryLogger

__all__ = [...]
```

#### C.1.2 实现指标收集器

**文件**: `src/pg_mcp/observability/metrics.py`

```python
class MetricsCollector:
    """Prometheus 指标收集器"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        # 请求指标
        self.requests_total = Counter(...)
        self.request_duration = Histogram(...)
        self.requests_in_flight = Gauge(...)

        # SQL 生成指标
        self.sql_generation_total = Counter(...)
        self.sql_generation_duration = Histogram(...)
        self.sql_retries_total = Counter(...)

        # 数据库指标
        self.db_pool_size = Gauge(...)
        self.db_pool_available = Gauge(...)
        self.db_query_duration = Histogram(...)

        # OpenAI 指标
        self.openai_tokens_total = Counter(...)
        self.openai_requests_total = Counter(...)
        self.openai_request_duration = Histogram(...)

        # 速率限制指标
        self.rate_limit_current = Gauge(...)
        self.rate_limit_exceeded_total = Counter(...)

        # 策略检查指标
        self.policy_check_total = Counter(...)

    # 便捷方法
    def record_request(self, database, status, duration, error_code=None): ...
    def record_sql_generation(self, database, status, duration): ...
    def record_db_query(self, database, duration): ...
    def record_openai_request(self, status, duration, prompt_tokens, completion_tokens): ...
    def record_policy_check(self, check_type, result): ...

    def generate_metrics(self) -> bytes:
        """生成 Prometheus 格式的指标数据"""
        return generate_latest(self.registry)
```

#### C.1.3 暴露 /metrics 端点

**修改**: `src/pg_mcp/server.py`

添加 `/metrics` 端点（如果使用 SSE 模式）或提供独立的 HTTP 服务器。

#### C.1.4 集成到各模块

在以下位置添加指标记录：
- `QueryService`: 记录请求、SQL 生成、OpenAI 调用
- `QueryExecutor`: 记录数据库查询、策略检查
- `RateLimiter`: 记录速率限制状态

#### C.1.5 测试用例

**文件**: `tests/unit/observability/test_metrics.py`

```python
class TestMetricsCollector:
    def test_record_request(self):
        """测试记录请求"""

    def test_record_sql_generation(self):
        """测试记录 SQL 生成"""

    def test_generate_metrics(self):
        """测试生成 Prometheus 格式"""

    def test_custom_registry(self):
        """测试自定义 Registry"""
```

---

### 5.2 任务 C.2: OpenTelemetry 追踪

**目标**: 实现 OpenTelemetry 追踪集成（可选功能）

**前置条件**: C.1 完成

**输出文件**:
- `src/pg_mcp/observability/tracing.py`

#### C.2.1 实现追踪管理器

**文件**: `src/pg_mcp/observability/tracing.py`

```python
class TracingManager:
    """OpenTelemetry 追踪管理器"""

    def __init__(self, config: TracingConfig):
        self.config = config
        self._tracer = None
        if config.enabled:
            self._setup_tracing()

    def _setup_tracing(self) -> None:
        """初始化追踪（处理依赖缺失）"""
        try:
            from opentelemetry import trace
            # ... 初始化逻辑
        except ImportError as e:
            logger.warning("tracing_disabled_missing_dependency", error=str(e))
            self.config.enabled = False

    @contextmanager
    def span(self, name: str, attributes: Optional[dict] = None):
        """创建追踪 span"""
        ...

    def get_current_trace_id(self) -> Optional[str]:
        """获取当前 trace ID"""
        ...
```

#### C.2.2 在关键路径添加 span

在以下位置添加追踪 span：
- `query.execute`: 完整查询流程
- `sql.generate`: SQL 生成
- `db.execute`: 数据库执行
- `policy.check`: 策略检查

---

### 5.3 任务 C.3: 日志增强

**目标**: 增强日志功能，支持 trace_id 和慢查询记录

**前置条件**: C.2 完成

**输出文件**:
- `src/pg_mcp/observability/logging.py` (从 utils 移动并增强)

#### C.3.1 实现日志增强

**文件**: `src/pg_mcp/observability/logging.py`

```python
def add_trace_id(logger, method_name, event_dict) -> dict:
    """添加 trace_id 到日志"""
    ...

def setup_logging(config: LoggingConfig) -> None:
    """配置结构化日志"""
    ...

class SlowQueryLogger:
    """慢查询日志记录器"""

    def __init__(self, threshold: float = 5.0, log_sql: bool = False):
        ...

    def log_if_slow(self, duration, database, sql, rows) -> None:
        """如果查询超过阈值则记录日志"""
        ...
```

**验收标准**:
- [ ] `/metrics` 端点返回 Prometheus 格式
- [ ] 关键操作有对应的追踪 span（如启用）
- [ ] 日志中包含 trace_id（如启用）
- [ ] 慢查询被特别记录
- [ ] OpenTelemetry 依赖缺失时优雅降级

---

## 6. Phase D: 代码质量

### 6.1 任务 D.1: 代码清理

**目标**: 移除冗余代码，统一工具函数

**前置条件**: Phase C 完成

#### D.1.1 移除冗余 to_dict() 方法

**审计范围**:
- `src/pg_mcp/models/*.py`
- `src/pg_mcp/config/models.py`

**清理规则**:
- 移除自定义 `to_dict()` 方法
- 统一使用 Pydantic `model_dump()` 或 `model_dump_json()`
- 若有特殊序列化需求，使用 `model_serializer` 装饰器

#### D.1.2 统一工具函数

**创建**: `src/pg_mcp/utils/serialization.py`

```python
def safe_model_dump(model: BaseModel, **kwargs) -> dict:
    """安全的模型序列化"""
    ...

def redact_sensitive_fields(data: dict, patterns: list[str]) -> dict:
    """脱敏敏感字段"""
    ...
```

#### D.1.3 清理未使用的配置字段

**审计**: `src/pg_mcp/config/models.py`

确保所有配置字段都有使用点，移除或实现 `enable_result_validation` 等字段。

---

### 6.2 任务 D.2: 测试覆盖增强

**目标**: 达到目标测试覆盖率

**前置条件**: D.1 完成

#### D.2.1 目标覆盖率

| 模块 | 目标覆盖率 |
|------|-----------|
| `security/access_policy.py` | >= 95% |
| `security/explain_validator.py` | >= 90% |
| `services/query_executor.py` | >= 90% |
| `resilience/rate_limiter.py` | >= 80% |
| `resilience/retry_executor.py` | >= 85% |
| `observability/metrics.py` | >= 80% |
| `infrastructure/sql_parser.py` | >= 95% |
| **总体** | >= 85% |

#### D.2.2 安全测试

**文件**: `tests/security/test_sql_injection.py`

```python
SQL_INJECTION_PAYLOADS = [
    # 基础注入
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "1; DELETE FROM orders",
    # ... 更多 payload
]

class TestSQLInjection:
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_injection_blocked(self, payload):
        """测试 SQL 注入被阻止"""
        ...
```

**文件**: `tests/security/test_access_bypass.py`

```python
class TestAccessBypass:
    def test_schema_bypass_attempt(self):
        """测试 Schema 绕过尝试"""

    def test_table_bypass_attempt(self):
        """测试表访问绕过尝试"""

    def test_column_bypass_via_alias(self):
        """测试通过别名绕过列限制"""
```

#### D.2.3 集成测试

**文件**: `tests/integration/test_full_flow.py`

使用 `testcontainers` 运行真实 PostgreSQL：

```python
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

class TestFullFlow:
    async def test_query_success(self, postgres_container):
        """测试完整查询流程"""

    async def test_query_with_rate_limit(self, postgres_container):
        """测试带速率限制的查询"""

    async def test_query_with_policy_denial(self, postgres_container):
        """测试策略拒绝"""
```

---

### 6.3 任务 D.3: 配置验证工具

**目标**: 实现配置验证命令

**前置条件**: D.2 完成

**输出文件**:
- `src/pg_mcp/config/validators.py`

#### D.3.1 实现配置验证器

**文件**: `src/pg_mcp/config/validators.py`

```python
class ConfigValidator:
    """配置验证器"""

    def validate_file(self, config_path: str) -> ValidationResult:
        """验证配置文件"""
        ...

    def _validate_databases(self, config: AppConfig) -> List[str]:
        """验证数据库配置"""
        ...

    def _validate_access_policy(self, db_name: str, policy: AccessPolicyConfig) -> List[str]:
        """验证访问策略配置"""
        ...

    def print_validation_result(self, result: ValidationResult) -> None:
        """打印验证结果"""
        ...

def validate_config_command(config_path: str) -> int:
    """配置验证命令入口"""
    ...
```

#### D.3.2 CLI 集成

**修改**: `src/pg_mcp/__main__.py`

添加 `config validate` 子命令：

```bash
pg-mcp config validate --config /path/to/config.yaml
```

**输出示例**:

```
✓ Configuration is valid
✓ Databases configured: 2
✓ Access policies: No conflicts detected

Warnings:
  ⚠ [production] Column pattern '*._password*' may match too broadly
```

---

## 7. 验收标准汇总

### 7.1 功能验收

#### P0 - 安全控制
- [ ] `pg-mcp config validate` 命令正确检测配置冲突
- [ ] 表级访问控制：白名单/黑名单模式正确工作
- [ ] 列级访问控制：显式列和 SELECT * 场景正确处理
- [ ] EXPLAIN 策略：超限拒绝，大表全表扫描拒绝
- [ ] 审计日志：完整记录查询上下文
- [ ] 多数据库路由正确且隔离

#### P1 - 弹性机制
- [ ] 速率限制在请求流程中生效
- [ ] Token 消耗被正确累计
- [ ] 重试执行器按配置重试
- [ ] 非可重试错误立即失败

#### P1 - 可观测性
- [ ] `/metrics` 返回 Prometheus 格式
- [ ] 追踪 span 正确创建（如启用）
- [ ] 慢查询被记录

#### P2 - 代码质量
- [ ] 无冗余 `to_dict()` 方法
- [ ] `ruff check .` 无警告
- [ ] 所有配置字段都有使用点

### 7.2 测试覆盖率验收

| 模块 | 目标 | 验收方式 |
|------|------|---------|
| 安全模块 | >= 95% | `pytest --cov` |
| 弹性模块 | >= 80% | `pytest --cov` |
| 可观测性模块 | >= 80% | `pytest --cov` |
| 总体 | >= 85% | `pytest --cov` |

### 7.3 性能验收

| 操作 | 预期延迟 | 验收方式 |
|------|---------|---------|
| 访问策略检查 | < 1ms | 基准测试 |
| EXPLAIN 验证（缓存命中）| < 1ms | 基准测试 |
| EXPLAIN 验证（缓存未命中）| < 50ms | 基准测试 |
| 速率限制检查 | < 1ms | 基准测试 |

### 7.4 安全验收

- [ ] SQL 注入 fuzz 测试通过
- [ ] 访问控制绕过测试通过
- [ ] 速率限制绕过测试通过
- [ ] 敏感信息不泄露到日志/追踪

---

## 8. 风险与缓解措施

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 访问策略配置复杂导致误配置 | 中 | 高 | 提供 `config validate` 命令和完整示例 |
| SQL 解析器扩展引入 bug | 中 | 高 | 增加 SQL 解析器单元测试到 >= 95% |
| EXPLAIN 策略误判合法查询 | 中 | 中 | 可配置阈值，失败时优雅降级 |
| 速率限制影响正常用户 | 低 | 中 | 默认值足够宽松，可配置禁用 |
| OpenTelemetry 依赖问题 | 低 | 低 | 可选安装，追踪默认禁用 |
| 测试覆盖率难以达标 | 中 | 中 | 预留充足测试时间，使用参数化测试 |

---

## 9. 检查清单

### 开发前检查
- [ ] 确认开发环境配置正确
- [ ] 确认 PostgreSQL 测试容器可用
- [ ] 确认依赖已添加到 `pyproject.toml`

### 每阶段完成检查
- [ ] 代码通过 `ruff check .`
- [ ] 单元测试通过
- [ ] 测试覆盖率达标
- [ ] 更新相关文档

### 最终交付检查
- [ ] 所有功能验收标准通过
- [ ] 所有测试覆盖率验收通过
- [ ] 所有性能验收通过
- [ ] 所有安全验收通过
- [ ] 完整配置示例可用
- [ ] CLI 命令可用

---

## 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-15 | 初始版本 | - |
