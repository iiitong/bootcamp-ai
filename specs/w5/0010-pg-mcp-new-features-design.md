# PostgreSQL MCP Server 增强功能设计文档

**版本**: 1.1
**日期**: 2026-01-15
**状态**: 已审核
**关联 PRD**: [0009-pg-mcp-new-features-prd.md](./0009-pg-mcp-new-features-prd.md)
**前置设计**: [0002-pg-mcp-design.md](./0002-pg-mcp-design.md)

---

## 1. 设计概述

### 1.1 设计目标

基于 PRD 需求，本设计文档详细描述以下增强功能的实现方案：

- **安全控制**: 数据库访问策略执行器、表/列级访问控制、EXPLAIN 策略验证
- **弹性机制**: 速率限制集成、智能重试与退避策略
- **可观测性**: Prometheus 指标暴露、OpenTelemetry 追踪集成
- **代码质量**: 移除冗余代码、测试覆盖增强

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| 纵深防御 | 应用层策略 + 数据库权限双重保护 |
| 最小权限 | 默认拒绝，显式授权 |
| 可配置性 | 所有安全策略可通过配置调整 |
| 性能优先 | 策略检查延迟 < 1ms（内存操作） |
| 向后兼容 | 新配置均提供合理默认值 |

### 1.3 技术栈扩展

| 组件 | 版本 | 用途 |
|------|------|------|
| prometheus-client | ^0.20 | Prometheus 指标暴露 |
| opentelemetry-api | ^1.24 | 分布式追踪 API |
| opentelemetry-sdk | ^1.24 | 分布式追踪 SDK |
| opentelemetry-exporter-otlp | ^1.24 | OTLP 导出器 |
| cachetools | ^5.3 | EXPLAIN 结果缓存 |

---

## 2. 架构设计

### 2.1 增强后的分层架构

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
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
        ┌─────────────────┐ ┌───────────────┐ ┌──────────────┐
        │  RateLimiter    │ │ MetricsCollector│ │   Tracer     │
        │  (pre-check)    │ │ (record)        │ │  (span)      │
        └────────┬────────┘ └───────┬───────┘ └──────┬───────┘
                 │                  │                │
                 └──────────────────┼────────────────┘
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
│                  QueryExecutorManager [NEW]                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  get_executor(database) → QueryExecutor                     ││
│  └─────────────────────────────────────────────────────────────┘│
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│       ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│       │ Executor A │  │ Executor B │  │ Executor C │            │
│       │ (db: prod) │  │ (db: stage)│  │ (db: dev)  │            │
│       │ + Pool     │  │ + Pool     │  │ + Pool     │            │
│       │ + Policy   │  │ + Policy   │  │ + Policy   │            │
│       │ + Auditor  │  │ + Auditor  │  │ + Auditor  │            │
│       └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌───────────┐  ┌───────────┐  ┌───────────┐
             │ PostgreSQL│  │ PostgreSQL│  │  OpenAI   │
             │    DB 1   │  │    DB 2   │  │    API    │
             └───────────┘  └───────────┘  └───────────┘
```

### 2.2 新增模块结构

```
pg-mcp/
├── src/
│   └── pg_mcp/
│       ├── security/                 # [NEW] 安全控制模块
│       │   ├── __init__.py
│       │   ├── access_policy.py      # 访问策略执行器
│       │   ├── explain_validator.py  # EXPLAIN 策略验证
│       │   └── audit_logger.py       # 审计日志
│       │
│       ├── resilience/               # [NEW] 弹性机制模块
│       │   ├── __init__.py
│       │   ├── rate_limiter.py       # 速率限制器 (重构)
│       │   ├── retry_executor.py     # 重试执行器
│       │   └── backoff.py            # 退避策略
│       │
│       ├── observability/            # [NEW] 可观测性模块
│       │   ├── __init__.py
│       │   ├── metrics.py            # Prometheus 指标
│       │   ├── tracing.py            # OpenTelemetry 追踪
│       │   └── logging.py            # 日志增强 (移动)
│       │
│       ├── services/
│       │   ├── query_executor.py     # [NEW] 查询执行器
│       │   └── query_executor_manager.py  # [NEW] 执行器管理器
│       │
│       └── config/
│           ├── models.py             # [EXTEND] 新增配置模型
│           └── validators.py         # [NEW] 配置验证器
│
└── tests/
    ├── unit/
    │   ├── security/                 # [NEW] 安全模块测试
    │   │   ├── test_access_policy.py
    │   │   └── test_explain_validator.py
    │   └── resilience/               # [NEW] 弹性模块测试
    │       ├── test_rate_limiter.py
    │       └── test_retry_executor.py
    ├── integration/
    │   ├── test_security_flow.py     # [NEW] 安全流程集成测试
    │   └── test_observability.py     # [NEW] 可观测性集成测试
    └── security/                     # [NEW] 安全测试
        ├── test_sql_injection.py
        └── test_access_bypass.py
```

---

## 3. 安全控制设计

### 3.0 SQL 解析结果模型 (扩展现有 sql_parser)

访问策略验证需要从 SQL 中提取结构化信息。需扩展现有的 `SQLParser` 返回以下数据结构：

```python
# src/pg_mcp/infrastructure/sql_parser.py (扩展)

from dataclasses import dataclass, field


@dataclass
class ParsedSQLInfo:
    """
    SQL 解析结果 (用于访问策略验证)

    扩展现有 SQLParser，在验证 SQL 安全性的同时提取结构化信息。
    """
    # 原始 SQL
    sql: str

    # 访问的 Schema 列表 (默认 "public" 如果未指定)
    schemas: list[str] = field(default_factory=lambda: ["public"])

    # 访问的表列表 (不含 schema 前缀)
    tables: list[str] = field(default_factory=list)

    # 访问的列列表: [(table, column), ...]
    columns: list[tuple[str, str]] = field(default_factory=list)

    # 是否包含 SELECT *
    has_select_star: bool = False

    # SELECT * 涉及的表 (用于列展开)
    select_star_tables: list[str] = field(default_factory=list)

    # 是否为只读查询 (现有功能)
    is_readonly: bool = True

    # 验证错误信息 (现有功能)
    error_message: str | None = None


class SQLParser:
    """SQL 解析器 (扩展)"""

    def parse(self, sql: str) -> ParsedSQLInfo:
        """
        解析 SQL 并提取结构化信息

        1. 使用 sqlglot 解析 AST
        2. 提取 schemas、tables、columns
        3. 检测 SELECT *
        4. 验证只读性
        """
        # 实现详见 infrastructure/sql_parser.py
        ...

    def _extract_tables(self, ast) -> list[str]:
        """从 AST 提取表名"""
        ...

    def _extract_columns(self, ast) -> list[tuple[str, str]]:
        """从 AST 提取列名 (含表前缀)"""
        ...

    def _detect_select_star(self, ast) -> tuple[bool, list[str]]:
        """检测 SELECT * 及涉及的表"""
        ...
```

### 3.1 访问策略配置模型

```python
# src/pg_mcp/config/models.py (扩展)

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class OnDeniedAction(str, Enum):
    """敏感列访问时的处理策略"""
    REJECT = "reject"    # 拒绝查询
    FILTER = "filter"    # 自动过滤（需 SQL 重写）


class SelectStarPolicy(str, Enum):
    """SELECT * 处理策略"""
    REJECT = "reject"         # 包含敏感列时拒绝
    EXPAND_SAFE = "expand_safe"  # 展开为安全列


class TableAccessConfig(BaseModel):
    """表访问控制配置"""
    allowed: list[str] = Field(
        default_factory=list,
        description="允许访问的表白名单（优先级高于黑名单）"
    )
    denied: list[str] = Field(
        default_factory=list,
        description="禁止访问的表黑名单"
    )

    @field_validator('allowed', 'denied')
    @classmethod
    def normalize_table_names(cls, v: list[str]) -> list[str]:
        """标准化表名（小写）"""
        return [name.lower() for name in v]


class ColumnAccessConfig(BaseModel):
    """列访问控制配置"""
    denied: list[str] = Field(
        default_factory=list,
        description="禁止访问的列列表，格式: table.column"
    )
    denied_patterns: list[str] = Field(
        default_factory=list,
        description="禁止访问的列模式，如 *._password*"
    )
    on_denied: OnDeniedAction = Field(
        default=OnDeniedAction.REJECT,
        description="访问敏感列时的处理策略"
    )
    select_star_policy: SelectStarPolicy = Field(
        default=SelectStarPolicy.REJECT,
        description="SELECT * 处理策略"
    )

    @field_validator('denied')
    @classmethod
    def validate_column_format(cls, v: list[str]) -> list[str]:
        """验证列格式必须为 table.column"""
        for col in v:
            if '.' not in col:
                raise ValueError(
                    f"Column '{col}' must be in 'table.column' format"
                )
        return [c.lower() for c in v]


class ExplainPolicyConfig(BaseModel):
    """EXPLAIN 策略配置"""
    enabled: bool = Field(default=True, description="是否启用 EXPLAIN 检查")
    max_estimated_rows: int = Field(
        default=100000,
        ge=1000,
        description="最大估算行数"
    )
    max_estimated_cost: float = Field(
        default=10000.0,
        ge=100,
        description="最大估算成本"
    )
    deny_seq_scan_on_large_tables: bool = Field(
        default=True,
        description="是否禁止大表全表扫描"
    )
    large_table_threshold: int = Field(
        default=10000,
        ge=1000,
        description="大表行数阈值"
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="EXPLAIN 执行超时"
    )
    cache_ttl_seconds: int = Field(
        default=60,
        ge=10,
        description="EXPLAIN 结果缓存 TTL"
    )
    cache_max_size: int = Field(
        default=1000,
        ge=100,
        description="缓存最大条目数"
    )


class AccessPolicyConfig(BaseModel):
    """数据库访问策略配置"""
    allowed_schemas: list[str] = Field(
        default=["public"],
        description="允许访问的 Schema 列表"
    )
    tables: TableAccessConfig = Field(default_factory=TableAccessConfig)
    columns: ColumnAccessConfig = Field(default_factory=ColumnAccessConfig)
    explain_policy: ExplainPolicyConfig = Field(
        default_factory=ExplainPolicyConfig
    )

    def validate_consistency(self) -> list[str]:
        """
        验证配置一致性，返回警告列表

        Raises:
            ValueError: 存在配置冲突时
        """
        warnings = []

        # 检查表配置冲突
        table_conflicts = set(self.tables.allowed) & set(self.tables.denied)
        if table_conflicts:
            raise ValueError(
                f"Tables in both allowed and denied lists: {table_conflicts}"
            )

        # 检查过于宽泛的列模式
        for pattern in self.columns.denied_patterns:
            if pattern.count('*') > 2:
                warnings.append(
                    f"Column pattern '{pattern}' may match too broadly"
                )

        return warnings
```

### 3.2 访问策略执行器

```python
# src/pg_mcp/security/access_policy.py

import fnmatch
import re
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

import structlog

from pg_mcp.config.models import (
    AccessPolicyConfig, OnDeniedAction, SelectStarPolicy
)
from pg_mcp.models.errors import ErrorCode, PgMcpError


logger = structlog.get_logger()


class PolicyCheckResult(str, Enum):
    """策略检查结果"""
    PASSED = "passed"
    DENIED = "denied"
    WARNING = "warning"


@dataclass
class PolicyViolation:
    """策略违规详情"""
    check_type: str  # "schema", "table", "column", "explain"
    resource: str    # 被拒绝的资源
    reason: str      # 拒绝原因


class PolicyValidationResult(NamedTuple):
    """策略验证结果"""
    passed: bool
    violations: list[PolicyViolation]
    warnings: list[str]
    rewritten_sql: str | None = None  # 仅在 filter 模式下使用


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
        message = f"Access denied to columns: {', '.join(columns)}"
        if is_select_star:
            message += " (triggered by SELECT *)"
        super().__init__(
            ErrorCode.COLUMN_ACCESS_DENIED,
            message,
            {"denied_columns": columns, "is_select_star": is_select_star}
        )


class SchemaAccessDeniedError(PgMcpError):
    """Schema 访问被拒绝"""
    def __init__(self, schema: str, allowed: list[str]):
        super().__init__(
            ErrorCode.SCHEMA_ACCESS_DENIED,
            f"Access denied to schema '{schema}'. Allowed: {', '.join(allowed)}",
            {"denied_schema": schema, "allowed_schemas": allowed}
        )


class DatabaseAccessPolicy:
    """
    数据库访问策略执行器

    职责:
    - 验证 SQL 中访问的 Schema/表/列是否符合策略
    - 检测 SELECT * 并根据策略处理
    - 支持 SQL 重写（filter 模式）
    """

    def __init__(self, config: AccessPolicyConfig):
        self.config = config
        self._compiled_patterns: list[re.Pattern] = []
        self._compile_patterns()

        # 验证配置一致性
        warnings = config.validate_consistency()
        for warning in warnings:
            logger.warning("access_policy_config_warning", warning=warning)

    def _compile_patterns(self) -> None:
        """预编译列名匹配模式"""
        for pattern in self.config.columns.denied_patterns:
            # 将 glob 模式转换为正则表达式
            regex = fnmatch.translate(pattern.lower())
            self._compiled_patterns.append(re.compile(regex))

    def validate_schema(self, schema: str) -> PolicyValidationResult:
        """
        验证 Schema 访问权限

        Args:
            schema: Schema 名称

        Returns:
            PolicyValidationResult
        """
        schema_lower = schema.lower()
        if schema_lower not in [s.lower() for s in self.config.allowed_schemas]:
            return PolicyValidationResult(
                passed=False,
                violations=[PolicyViolation(
                    check_type="schema",
                    resource=schema,
                    reason=f"Schema not in allowed list: {self.config.allowed_schemas}"
                )],
                warnings=[]
            )
        return PolicyValidationResult(passed=True, violations=[], warnings=[])

    def validate_tables(self, tables: list[str]) -> PolicyValidationResult:
        """
        验证表访问权限

        优先级: allowed (白名单) > denied (黑名单)

        Args:
            tables: 表名列表

        Returns:
            PolicyValidationResult
        """
        violations = []
        tables_lower = [t.lower() for t in tables]

        allowed = [t.lower() for t in self.config.tables.allowed]
        denied = [t.lower() for t in self.config.tables.denied]

        for table in tables_lower:
            # 白名单模式
            if allowed and table not in allowed:
                violations.append(PolicyViolation(
                    check_type="table",
                    resource=table,
                    reason="Table not in allowed list"
                ))
            # 黑名单模式
            elif not allowed and table in denied:
                violations.append(PolicyViolation(
                    check_type="table",
                    resource=table,
                    reason="Table in denied list"
                ))

        return PolicyValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=[]
        )

    def validate_columns(
        self,
        columns: list[tuple[str, str]],  # [(table, column), ...]
        is_select_star: bool = False
    ) -> PolicyValidationResult:
        """
        验证列访问权限

        Args:
            columns: 列列表，每项为 (table, column) 元组
            is_select_star: 是否来自 SELECT * 展开

        Returns:
            PolicyValidationResult
        """
        violations = []
        denied_columns = []

        denied_explicit = [c.lower() for c in self.config.columns.denied]

        for table, column in columns:
            full_name = f"{table.lower()}.{column.lower()}"

            # 检查显式禁止列表
            if full_name in denied_explicit:
                violations.append(PolicyViolation(
                    check_type="column",
                    resource=full_name,
                    reason="Column in denied list"
                ))
                denied_columns.append(full_name)
                continue

            # 检查模式匹配
            for pattern in self._compiled_patterns:
                if pattern.match(full_name):
                    violations.append(PolicyViolation(
                        check_type="column",
                        resource=full_name,
                        reason=f"Column matches denied pattern"
                    ))
                    denied_columns.append(full_name)
                    break

        # SELECT * 特殊处理
        if is_select_star and violations:
            if self.config.columns.select_star_policy == SelectStarPolicy.REJECT:
                # 明确告知哪些敏感列被触发
                return PolicyValidationResult(
                    passed=False,
                    violations=violations,
                    warnings=[
                        f"SELECT * would access sensitive columns: {denied_columns}"
                    ]
                )

        return PolicyValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=[]
        )

    def get_safe_columns(
        self,
        table: str,
        all_columns: list[str]
    ) -> list[str]:
        """
        获取表的安全列列表（用于 SELECT * 展开）

        Args:
            table: 表名
            all_columns: 表的所有列

        Returns:
            安全列列表
        """
        safe_columns = []
        for col in all_columns:
            full_name = f"{table.lower()}.{col.lower()}"

            # 检查是否在禁止列表
            if full_name in [c.lower() for c in self.config.columns.denied]:
                continue

            # 检查是否匹配禁止模式
            is_denied = False
            for pattern in self._compiled_patterns:
                if pattern.match(full_name):
                    is_denied = True
                    break

            if not is_denied:
                safe_columns.append(col)

        return safe_columns

    def validate_sql(
        self,
        parsed_result: "ParsedSQLInfo"  # 来自 sql_parser
    ) -> PolicyValidationResult:
        """
        完整的 SQL 策略验证

        Args:
            parsed_result: SQL 解析结果

        Returns:
            PolicyValidationResult
        """
        all_violations = []
        all_warnings = []

        # 1. 验证 Schema
        for schema in parsed_result.schemas:
            result = self.validate_schema(schema)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)

        # 2. 验证表
        result = self.validate_tables(parsed_result.tables)
        all_violations.extend(result.violations)
        all_warnings.extend(result.warnings)

        # 3. 验证列
        result = self.validate_columns(
            parsed_result.columns,
            is_select_star=parsed_result.has_select_star
        )
        all_violations.extend(result.violations)
        all_warnings.extend(result.warnings)

        return PolicyValidationResult(
            passed=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings
        )
```

### 3.3 EXPLAIN 策略验证器

```python
# src/pg_mcp/security/explain_validator.py

import hashlib
from dataclasses import dataclass
from typing import Any

import structlog
from asyncpg import Connection
from cachetools import TTLCache

from pg_mcp.config.models import ExplainPolicyConfig
from pg_mcp.models.errors import ErrorCode, PgMcpError


logger = structlog.get_logger()


class QueryTooExpensiveError(PgMcpError):
    """查询代价过高"""
    def __init__(
        self,
        estimated_rows: int,
        estimated_cost: float,
        limits: dict
    ):
        super().__init__(
            ErrorCode.QUERY_TOO_EXPENSIVE,
            f"Query exceeds resource limits. "
            f"Estimated rows: {estimated_rows}, cost: {estimated_cost:.2f}",
            {"estimated_rows": estimated_rows, "estimated_cost": estimated_cost, **limits}
        )


class SeqScanDeniedError(PgMcpError):
    """全表扫描被拒绝"""
    def __init__(self, table: str, estimated_rows: int):
        super().__init__(
            ErrorCode.SEQ_SCAN_DENIED,
            f"Sequential scan on large table '{table}' denied. "
            f"Estimated rows: {estimated_rows}",
            {"table": table, "estimated_rows": estimated_rows}
        )


@dataclass
class ExplainResult:
    """EXPLAIN 分析结果"""
    total_cost: float
    estimated_rows: int
    plan_nodes: list[dict]
    has_seq_scan: bool
    seq_scan_tables: list[tuple[str, int]]  # [(table, rows), ...]
    raw_plan: dict


@dataclass
class ExplainValidationResult:
    """EXPLAIN 验证结果"""
    passed: bool
    result: ExplainResult | None
    error_message: str | None = None
    warnings: list[str] | None = None


class ExplainValidator:
    """
    EXPLAIN 策略验证器

    职责:
    - 执行 EXPLAIN (FORMAT JSON) 获取查询计划
    - 分析估算行数、成本、全表扫描
    - 缓存相同 SQL 的 EXPLAIN 结果
    """

    def __init__(
        self,
        config: ExplainPolicyConfig,
        table_row_counts: dict[str, int] | None = None
    ):
        """
        Args:
            config: EXPLAIN 策略配置
            table_row_counts: 表行数估算（来自 Schema 缓存的 pg_class.reltuples）
        """
        self.config = config
        self.table_row_counts = table_row_counts or {}

        # EXPLAIN 结果缓存
        self._cache: TTLCache = TTLCache(
            maxsize=config.cache_max_size,
            ttl=config.cache_ttl_seconds
        )

    def _get_cache_key(self, sql: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(sql.encode()).hexdigest()[:16]

    async def validate(
        self,
        conn: Connection,
        sql: str
    ) -> ExplainValidationResult:
        """
        验证 SQL 的查询计划

        Args:
            conn: 数据库连接
            sql: 待验证的 SQL

        Returns:
            ExplainValidationResult
        """
        if not self.config.enabled:
            return ExplainValidationResult(passed=True, result=None)

        # 检查缓存
        cache_key = self._get_cache_key(sql)
        if cache_key in self._cache:
            logger.debug("explain_cache_hit", cache_key=cache_key)
            cached_result = self._cache[cache_key]
            return self._validate_result(cached_result)

        try:
            # 执行 EXPLAIN
            explain_sql = f"EXPLAIN (FORMAT JSON, COSTS TRUE) {sql}"
            result = await conn.fetchval(
                explain_sql,
                timeout=self.config.timeout_seconds
            )

            # 解析结果
            explain_result = self._parse_explain(result)

            # 缓存结果
            self._cache[cache_key] = explain_result

            # 验证
            return self._validate_result(explain_result)

        except Exception as e:
            logger.warning("explain_failed", error=str(e), sql=sql[:100])
            # EXPLAIN 失败时不阻止查询，但记录警告
            return ExplainValidationResult(
                passed=True,
                result=None,
                warnings=[f"EXPLAIN failed: {str(e)}"]
            )

    def _parse_explain(self, explain_json: list[dict]) -> ExplainResult:
        """
        解析 EXPLAIN JSON 输出

        Args:
            explain_json: EXPLAIN (FORMAT JSON) 输出

        Returns:
            ExplainResult
        """
        plan = explain_json[0]["Plan"]

        total_cost = plan.get("Total Cost", 0)
        estimated_rows = plan.get("Plan Rows", 0)

        # 递归收集所有计划节点
        nodes = []
        seq_scan_tables = []

        def collect_nodes(node: dict) -> None:
            nodes.append(node)

            # 检测 Seq Scan
            node_type = node.get("Node Type", "")
            if node_type == "Seq Scan":
                table = node.get("Relation Name", "unknown")
                rows = node.get("Plan Rows", 0)
                seq_scan_tables.append((table, rows))

            # 递归子节点
            for child in node.get("Plans", []):
                collect_nodes(child)

        collect_nodes(plan)

        return ExplainResult(
            total_cost=total_cost,
            estimated_rows=estimated_rows,
            plan_nodes=nodes,
            has_seq_scan=len(seq_scan_tables) > 0,
            seq_scan_tables=seq_scan_tables,
            raw_plan=plan
        )

    def _validate_result(self, result: ExplainResult) -> ExplainValidationResult:
        """
        根据策略验证 EXPLAIN 结果

        Args:
            result: EXPLAIN 分析结果

        Returns:
            ExplainValidationResult
        """
        warnings = []

        # 检查估算行数
        if result.estimated_rows > self.config.max_estimated_rows:
            return ExplainValidationResult(
                passed=False,
                result=result,
                error_message=(
                    f"Estimated rows ({result.estimated_rows}) exceeds limit "
                    f"({self.config.max_estimated_rows})"
                )
            )

        # 检查估算成本（警告，不拒绝）
        if result.total_cost > self.config.max_estimated_cost:
            warnings.append(
                f"Query cost ({result.total_cost:.2f}) exceeds recommended "
                f"limit ({self.config.max_estimated_cost})"
            )

        # 检查大表全表扫描
        if self.config.deny_seq_scan_on_large_tables and result.has_seq_scan:
            for table, rows in result.seq_scan_tables:
                # 优先使用配置的表行数，否则使用 EXPLAIN 估算
                actual_rows = self.table_row_counts.get(table, rows)
                if actual_rows > self.config.large_table_threshold:
                    return ExplainValidationResult(
                        passed=False,
                        result=result,
                        error_message=(
                            f"Sequential scan on large table '{table}' "
                            f"(~{actual_rows} rows) denied"
                        )
                    )

        return ExplainValidationResult(
            passed=True,
            result=result,
            warnings=warnings if warnings else None
        )

    def update_table_row_counts(self, counts: dict[str, int]) -> None:
        """更新表行数估算（从 Schema 缓存刷新时调用）"""
        self.table_row_counts = counts
```

### 3.4 审计日志

```python
# src/pg_mcp/security/audit_logger.py

import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any

import structlog


logger = structlog.get_logger()


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
class ClientInfo:
    """客户端信息"""
    ip: str | None  # 仅 SSE 模式可用
    user_agent: str | None
    session_id: str | None


@dataclass
class QueryInfo:
    """查询信息"""
    question: str
    sql: str
    sql_hash: str  # SHA256 hash

    @classmethod
    def from_sql(cls, question: str, sql: str) -> "QueryInfo":
        sql_hash = f"sha256:{hashlib.sha256(sql.encode()).hexdigest()}"
        return cls(question=question, sql=sql, sql_hash=sql_hash)


@dataclass
class ResultInfo:
    """结果信息"""
    status: str  # success, error, denied
    rows_returned: int | None
    execution_time_ms: float
    truncated: bool
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class PolicyCheckInfo:
    """策略检查信息"""
    table_access: str  # passed, denied, skipped
    column_access: str
    explain_check: str


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
        """转换为字典（用于 JSON 序列化）"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    审计日志记录器

    职责:
    - 记录所有查询请求和结果
    - 支持多种存储方式
    - 日志轮转（文件模式）
    """

    def __init__(
        self,
        storage: AuditStorage = AuditStorage.STDOUT,
        file_path: str | None = None,
        max_size_mb: int = 100,
        max_files: int = 10,
        redact_sql: bool = False
    ):
        self.storage = storage
        self.file_path = Path(file_path) if file_path else None
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_files = max_files
        self.redact_sql = redact_sql

        self._file_handle = None
        self._current_size = 0

    async def log(self, event: AuditEvent) -> None:
        """
        记录审计事件

        Args:
            event: 审计事件
        """
        json_line = event.to_json()

        if self.storage == AuditStorage.STDOUT:
            logger.info("audit_event", **event.to_dict())
        elif self.storage == AuditStorage.FILE:
            await self._write_to_file(json_line)
        elif self.storage == AuditStorage.DATABASE:
            # 未来扩展：写入数据库
            pass

    async def _write_to_file(self, line: str) -> None:
        """
        写入文件（带轮转）

        注意: 使用 asyncio.to_thread 避免阻塞事件循环
        """
        import asyncio

        if self.file_path is None:
            return

        # 检查是否需要轮转
        if self._current_size > self.max_size_bytes:
            await self._rotate()

        # 在线程池中执行同步写入，避免阻塞
        def _sync_write():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        await asyncio.to_thread(_sync_write)
        self._current_size += len(line) + 1

    async def _rotate(self) -> None:
        """轮转日志文件"""
        if self.file_path is None or not self.file_path.exists():
            return

        # 重命名现有文件
        for i in range(self.max_files - 1, 0, -1):
            old_path = self.file_path.with_suffix(f".{i}.jsonl")
            new_path = self.file_path.with_suffix(f".{i+1}.jsonl")
            if old_path.exists():
                if i + 1 >= self.max_files:
                    old_path.unlink()
                else:
                    old_path.rename(new_path)

        # 当前文件变为 .1
        if self.file_path.exists():
            self.file_path.rename(
                self.file_path.with_suffix(".1.jsonl")
            )

        self._current_size = 0

    @staticmethod
    def create_event(
        event_type: AuditEventType,
        request_id: str,
        database: str,
        client_ip: str | None = None,
        session_id: str | None = None,
        question: str | None = None,
        sql: str | None = None,
        rows_returned: int | None = None,
        execution_time_ms: float = 0,
        truncated: bool = False,
        error_code: str | None = None,
        error_message: str | None = None,
        policy_checks: dict | None = None
    ) -> AuditEvent:
        """创建审计事件的便捷方法"""
        return AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            request_id=request_id,
            session_id=session_id,
            database=database,
            client_info=ClientInfo(
                ip=client_ip,
                user_agent=None,
                session_id=session_id
            ),
            query=QueryInfo.from_sql(question or "", sql or "") if sql else None,
            result=ResultInfo(
                status="success" if error_code is None else "error",
                rows_returned=rows_returned,
                execution_time_ms=execution_time_ms,
                truncated=truncated,
                error_code=error_code,
                error_message=error_message
            ) if sql else None,
            policy_checks=PolicyCheckInfo(
                table_access=policy_checks.get("table_access", "skipped"),
                column_access=policy_checks.get("column_access", "skipped"),
                explain_check=policy_checks.get("explain_check", "skipped")
            ) if policy_checks else None
        )
```

### 3.5 查询执行器

```python
# src/pg_mcp/services/query_executor.py

import time
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from asyncpg import Connection

from pg_mcp.config.models import AccessPolicyConfig
from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.sql_parser import SQLParser, ParsedSQLInfo
from pg_mcp.models.query import QueryResult
from pg_mcp.models.errors import PgMcpError
from pg_mcp.security.access_policy import (
    DatabaseAccessPolicy,
    PolicyValidationResult,
    TableAccessDeniedError,
    ColumnAccessDeniedError,
    SchemaAccessDeniedError
)
from pg_mcp.security.explain_validator import (
    ExplainValidator,
    ExplainValidationResult,
    QueryTooExpensiveError,
    SeqScanDeniedError
)
from pg_mcp.security.audit_logger import (
    AuditLogger,
    AuditEventType,
    AuditEvent
)


logger = structlog.get_logger()


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

    与 QueryService 的关系:
    - QueryService 负责业务流程编排（SQL 生成、重试逻辑）
    - QueryExecutor 负责单次 SQL 执行（策略检查、实际执行）
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
        self.database_name = database_name
        self.pool = pool
        self.access_policy = access_policy
        self.explain_validator = explain_validator
        self.audit_logger = audit_logger
        self.sql_parser = sql_parser

    async def execute(
        self,
        sql: str,
        limit: int,
        context: ExecutionContext,
        question: str = ""
    ) -> QueryResult:
        """
        执行查询（带策略检查）

        Args:
            sql: SQL 语句
            limit: 结果行数限制
            context: 执行上下文
            question: 原始自然语言问题

        Returns:
            QueryResult

        Raises:
            TableAccessDeniedError: 表访问被拒绝
            ColumnAccessDeniedError: 列访问被拒绝
            SchemaAccessDeniedError: Schema 访问被拒绝
            QueryTooExpensiveError: 查询代价过高
            SeqScanDeniedError: 全表扫描被拒绝
        """
        start_time = time.monotonic()
        policy_checks = {}

        try:
            # 1. 解析 SQL
            parsed = self.sql_parser.parse(sql)

            # 2. 访问策略检查
            policy_result = self.access_policy.validate_sql(parsed)
            policy_checks = {
                "table_access": "passed" if not any(
                    v.check_type == "table" for v in policy_result.violations
                ) else "denied",
                "column_access": "passed" if not any(
                    v.check_type == "column" for v in policy_result.violations
                ) else "denied",
                "explain_check": "pending"
            }

            if not policy_result.passed:
                # 按类型抛出对应异常
                self._raise_policy_error(policy_result)

            # 3. EXPLAIN 策略检查
            async with self.pool.acquire() as conn:
                explain_result = await self.explain_validator.validate(conn, sql)
                policy_checks["explain_check"] = (
                    "passed" if explain_result.passed else "denied"
                )

                if not explain_result.passed:
                    raise QueryTooExpensiveError(
                        estimated_rows=explain_result.result.estimated_rows if explain_result.result else 0,
                        estimated_cost=explain_result.result.total_cost if explain_result.result else 0,
                        limits={
                            "max_rows": self.explain_validator.config.max_estimated_rows,
                            "max_cost": self.explain_validator.config.max_estimated_cost
                        }
                    )

                # 4. 执行查询
                rows = await conn.fetch(sql, timeout=30.0)

                # 5. 构建结果
                result = self._build_result(rows, limit)

                # 6. 记录审计日志
                execution_time = (time.monotonic() - start_time) * 1000
                await self._log_success(
                    context, question, sql, result,
                    execution_time, policy_checks
                )

                return result

        except PgMcpError:
            # 已知错误，记录审计后重新抛出
            execution_time = (time.monotonic() - start_time) * 1000
            await self._log_error(
                context, question, sql, execution_time,
                policy_checks, error=None  # 异常会被上层捕获
            )
            raise
        except Exception as e:
            # 未知错误
            execution_time = (time.monotonic() - start_time) * 1000
            await self._log_error(
                context, question, sql, execution_time,
                policy_checks, error=e
            )
            raise

    def _raise_policy_error(self, result: PolicyValidationResult) -> None:
        """根据违规类型抛出对应异常"""
        for violation in result.violations:
            if violation.check_type == "schema":
                raise SchemaAccessDeniedError(
                    violation.resource,
                    self.access_policy.config.allowed_schemas
                )
            elif violation.check_type == "table":
                # 收集所有表违规
                denied_tables = [
                    v.resource for v in result.violations
                    if v.check_type == "table"
                ]
                raise TableAccessDeniedError(denied_tables)
            elif violation.check_type == "column":
                # 收集所有列违规
                denied_columns = [
                    v.resource for v in result.violations
                    if v.check_type == "column"
                ]
                is_select_star = any(
                    "SELECT *" in w for w in result.warnings
                )
                raise ColumnAccessDeniedError(denied_columns, is_select_star)

    def _build_result(
        self,
        rows: list,
        limit: int
    ) -> QueryResult:
        """构建查询结果"""
        if not rows:
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                truncated=False
            )

        columns = list(rows[0].keys())
        data = [list(row.values()) for row in rows]

        truncated = len(data) > limit
        if truncated:
            data = data[:limit]

        return QueryResult(
            columns=columns,
            rows=data,
            row_count=len(data),
            truncated=truncated
        )

    async def _log_success(
        self,
        context: ExecutionContext,
        question: str,
        sql: str,
        result: QueryResult,
        execution_time_ms: float,
        policy_checks: dict
    ) -> None:
        """记录成功的审计日志"""
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id=context.request_id,
            database=self.database_name,
            client_ip=context.client_ip,
            session_id=context.session_id,
            question=question,
            sql=sql,
            rows_returned=result.row_count,
            execution_time_ms=execution_time_ms,
            truncated=result.truncated,
            policy_checks=policy_checks
        )
        await self.audit_logger.log(event)

    async def _log_error(
        self,
        context: ExecutionContext,
        question: str,
        sql: str,
        execution_time_ms: float,
        policy_checks: dict,
        error: Exception | None
    ) -> None:
        """记录失败的审计日志"""
        error_code = None
        error_message = None

        if isinstance(error, PgMcpError):
            error_code = error.code.value
            error_message = error.message
        elif error:
            error_code = "INTERNAL_ERROR"
            error_message = str(error)

        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_DENIED,
            request_id=context.request_id,
            database=self.database_name,
            client_ip=context.client_ip,
            session_id=context.session_id,
            question=question,
            sql=sql,
            execution_time_ms=execution_time_ms,
            error_code=error_code,
            error_message=error_message,
            policy_checks=policy_checks
        )
        await self.audit_logger.log(event)
```

### 3.6 查询执行器管理器

```python
# src/pg_mcp/services/query_executor_manager.py

from typing import Dict

import structlog

from pg_mcp.config.models import DatabaseConfig, AccessPolicyConfig
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import UnknownDatabaseError, PgMcpError, ErrorCode
from pg_mcp.security.access_policy import DatabaseAccessPolicy
from pg_mcp.security.explain_validator import ExplainValidator
from pg_mcp.security.audit_logger import AuditLogger
from pg_mcp.services.query_executor import QueryExecutor


logger = structlog.get_logger()


class AmbiguousDatabaseError(PgMcpError):
    """数据库选择不明确"""
    def __init__(self, available: list[str]):
        super().__init__(
            ErrorCode.AMBIGUOUS_QUERY,
            f"Database not specified and multiple databases available. "
            f"Please specify one of: {', '.join(available)}",
            {"available_databases": available}
        )


class QueryExecutorManager:
    """
    查询执行器管理器

    职责:
    - 为每个数据库创建独立的 QueryExecutor
    - 根据请求路由到正确的执行器
    - 管理执行器生命周期
    """

    def __init__(
        self,
        pool_manager: DatabasePoolManager,
        sql_parser: SQLParser,
        audit_logger: AuditLogger
    ):
        self.pool_manager = pool_manager
        self.sql_parser = sql_parser
        self.audit_logger = audit_logger
        self._executors: Dict[str, QueryExecutor] = {}

    def register_database(
        self,
        config: DatabaseConfig,
        access_policy_config: AccessPolicyConfig | None = None
    ) -> None:
        """
        注册数据库并创建对应的执行器

        Args:
            config: 数据库配置
            access_policy_config: 访问策略配置（可选，默认使用空策略）
        """
        policy_config = access_policy_config or AccessPolicyConfig()

        # 创建访问策略
        access_policy = DatabaseAccessPolicy(policy_config)

        # 创建 EXPLAIN 验证器
        explain_validator = ExplainValidator(policy_config.explain_policy)

        # 获取连接池
        pool = self.pool_manager.get_pool(config.name)

        # 创建执行器
        executor = QueryExecutor(
            database_name=config.name,
            pool=pool,
            access_policy=access_policy,
            explain_validator=explain_validator,
            audit_logger=self.audit_logger,
            sql_parser=self.sql_parser
        )

        self._executors[config.name] = executor
        logger.info(
            "query_executor_registered",
            database=config.name,
            policy_enabled=policy_config.explain_policy.enabled
        )

    def get_executor(self, database: str | None = None) -> QueryExecutor:
        """
        获取指定数据库的执行器

        Args:
            database: 数据库名称（可选）

        Returns:
            QueryExecutor

        Raises:
            UnknownDatabaseError: 数据库不存在
            AmbiguousDatabaseError: 未指定数据库且存在多个库
        """
        available = list(self._executors.keys())

        if database is None:
            # 未指定数据库
            if len(available) == 1:
                # 只有一个库，自动选择
                return self._executors[available[0]]
            else:
                # 多个库，要求明确指定
                raise AmbiguousDatabaseError(available)

        if database not in self._executors:
            raise UnknownDatabaseError(database, available)

        return self._executors[database]

    def list_databases(self) -> list[str]:
        """列出所有已注册的数据库"""
        return list(self._executors.keys())

    async def close_all(self) -> None:
        """关闭所有执行器"""
        self._executors.clear()
        logger.info("all_query_executors_closed")
```

### 3.7 QueryService 集成设计

现有的 `QueryService` 需要重构以使用新的 `QueryExecutor` 架构。

**修改点**：

```python
# src/pg_mcp/services/query_service.py (修改)

class QueryService:
    """
    查询服务 (重构)

    职责变更:
    - 保留: SQL 生成、重试逻辑、结果格式化
    - 委托: SQL 执行委托给 QueryExecutor
    - 移除: 直接持有 DatabasePool
    """

    def __init__(
        self,
        executor_manager: QueryExecutorManager,  # [NEW] 替代 pool_manager
        openai_client: OpenAIClient,
        schema_cache: SchemaCacheManager,
        config: ServerConfig,
        rate_limiter: RateLimiter,               # [NEW] 速率限制集成
        metrics: MetricsCollector | None = None,  # [NEW] 指标收集
    ):
        self.executor_manager = executor_manager
        self.openai_client = openai_client
        self.schema_cache = schema_cache
        self.config = config
        self.rate_limiter = rate_limiter
        self.metrics = metrics

    async def query(
        self,
        request: QueryRequest,
        context: ExecutionContext
    ) -> QueryResponse:
        """
        处理自然语言查询

        流程:
        1. 速率限制检查 (前置)
        2. 获取目标数据库的执行器
        3. 生成 SQL (含重试)
        4. 委托执行器执行 (策略检查在执行器内部)
        5. 结果验证 (可选)
        6. 记录 Token 消耗
        """
        # 1. 速率限制检查
        rate_result = self.rate_limiter.check_request(
            client_ip=context.client_ip,
            session_id=context.session_id
        )
        if not rate_result.allowed:
            raise RateLimitExceededError(
                retry_after=rate_result.retry_after
            )

        # 2. 获取执行器
        executor = self.executor_manager.get_executor(request.database)

        # 3. 生成 SQL
        sql_result = await self._generate_sql_with_retry(
            request.question,
            executor.database_name
        )

        # 4. 执行查询 (策略检查在 executor 内部)
        limit = request.limit or self.config.max_result_rows
        result = await executor.execute(
            sql=sql_result.sql,
            limit=limit,
            context=context,
            question=request.question
        )

        # 5. 可选: 结果验证
        if self.config.enable_result_validation and result.row_count == 0:
            await self._validate_empty_result(
                sql_result.sql,
                request.question,
                executor.database_name
            )

        # 6. 记录 Token 消耗
        self.rate_limiter.record_tokens(sql_result.tokens_used)

        return QueryResponse(
            success=True,
            sql=sql_result.sql if request.return_type != ReturnType.RESULT else None,
            result=result if request.return_type != ReturnType.SQL else None,
            explanation=sql_result.explanation
        )
```

### 3.8 结果验证功能 (enable_result_validation)

PRD 要求实现结果验证功能，当查询返回空结果时验证是数据问题还是 SQL 问题。

```python
# src/pg_mcp/services/query_service.py (续)

class QueryService:
    # ... 其他方法 ...

    async def _validate_empty_result(
        self,
        sql: str,
        question: str,
        database: str
    ) -> None:
        """
        验证空结果

        触发条件:
        - config.enable_result_validation = True
        - 查询结果为空 (row_count = 0)

        验证逻辑:
        - 调用 OpenAI 分析 SQL 与问题的匹配度
        - 如果 SQL 有问题，记录警告日志
        - 不阻止返回结果（避免影响可用性）
        """
        try:
            validation_prompt = f'''
The following SQL query returned 0 rows. Please analyze if this is expected:

Question: {question}
SQL: {sql}

Respond with:
- "DATA_ISSUE": If the SQL is correct but data doesn't exist
- "SQL_ISSUE: <reason>": If the SQL might be incorrect
'''
            response = await self.openai_client.validate_result(
                prompt=validation_prompt
            )

            if response.startswith("SQL_ISSUE"):
                logger.warning(
                    "empty_result_sql_issue",
                    database=database,
                    question=question[:100],
                    sql=sql[:200],
                    reason=response
                )
        except Exception as e:
            # 验证失败不影响主流程
            logger.debug("result_validation_failed", error=str(e))
```

**配置**：

```python
# src/pg_mcp/config/models.py

class ServerSettings(BaseSettings):
    # ... 现有字段 ...

    # [NEW] 结果验证
    enable_result_validation: bool = Field(
        default=False,
        description="是否启用空结果验证"
    )
```

---

## 4. 弹性机制设计

### 4.1 速率限制集成

```python
# src/pg_mcp/resilience/rate_limiter.py

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple

import structlog


logger = structlog.get_logger()


class RateLimitStrategy(str, Enum):
    """速率限制策略"""
    REJECT = "reject"   # 直接拒绝
    QUEUE = "queue"     # 排队等待
    DELAY = "delay"     # 延迟响应


class ClientIdentifier(str, Enum):
    """客户端标识方式"""
    IP = "ip"           # 使用 IP（仅 SSE 模式）
    SESSION = "session" # 使用 session_id
    AUTO = "auto"       # 自动选择


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    enabled: bool = True

    # 全局限制
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # 单客户端限制
    per_client_per_minute: int = 20
    client_identifier: ClientIdentifier = ClientIdentifier.AUTO

    # Token 限制
    tokens_per_minute: int = 100000
    tokens_per_hour: int = 1000000

    # 策略
    strategy: RateLimitStrategy = RateLimitStrategy.REJECT
    max_queue_wait: float = 30.0
    include_headers: bool = True


@dataclass
class RateLimitResult:
    """速率限制检查结果"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # Unix timestamp
    retry_after: float | None = None  # 秒


@dataclass
class RateLimitBucket:
    """速率限制桶"""
    count: int = 0
    reset_at: float = 0.0

    def check_and_increment(
        self,
        limit: int,
        window_seconds: float
    ) -> Tuple[bool, int, float]:
        """
        检查并增加计数

        Returns:
            (是否允许, 剩余配额, 重置时间)
        """
        now = time.time()

        # 检查是否需要重置
        if now >= self.reset_at:
            self.count = 0
            self.reset_at = now + window_seconds

        # 检查是否超限
        if self.count >= limit:
            return False, 0, self.reset_at

        # 增加计数
        self.count += 1
        return True, limit - self.count, self.reset_at


class RateLimiter:
    """
    速率限制器

    职责:
    - 在请求处理前检查速率限制
    - 在请求处理后记录 Token 消耗
    - 支持全局和单客户端限制
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config

        # 全局桶
        self._global_minute_bucket = RateLimitBucket()
        self._global_hour_bucket = RateLimitBucket()

        # Token 桶
        self._token_minute_bucket = RateLimitBucket()
        self._token_hour_bucket = RateLimitBucket()

        # 客户端桶
        self._client_buckets: Dict[str, RateLimitBucket] = {}

    def _get_client_key(
        self,
        client_ip: str | None,
        session_id: str | None
    ) -> str:
        """获取客户端标识键"""
        if self.config.client_identifier == ClientIdentifier.IP:
            return f"ip:{client_ip or 'unknown'}"
        elif self.config.client_identifier == ClientIdentifier.SESSION:
            return f"session:{session_id or 'unknown'}"
        else:  # AUTO
            # SSE 模式优先使用 IP，否则使用 session
            if client_ip:
                return f"ip:{client_ip}"
            return f"session:{session_id or 'unknown'}"

    def check_request(
        self,
        client_ip: str | None = None,
        session_id: str | None = None
    ) -> RateLimitResult:
        """
        检查请求是否被允许

        Args:
            client_ip: 客户端 IP（SSE 模式）
            session_id: 会话 ID

        Returns:
            RateLimitResult
        """
        if not self.config.enabled:
            return RateLimitResult(
                allowed=True,
                limit=self.config.requests_per_minute,
                remaining=self.config.requests_per_minute,
                reset_at=time.time() + 60
            )

        # 检查全局限制（每分钟）
        allowed, remaining, reset_at = self._global_minute_bucket.check_and_increment(
            self.config.requests_per_minute,
            60.0
        )
        if not allowed:
            return RateLimitResult(
                allowed=False,
                limit=self.config.requests_per_minute,
                remaining=0,
                reset_at=reset_at,
                retry_after=reset_at - time.time()
            )

        # 检查全局限制（每小时）
        allowed, _, _ = self._global_hour_bucket.check_and_increment(
            self.config.requests_per_hour,
            3600.0
        )
        if not allowed:
            return RateLimitResult(
                allowed=False,
                limit=self.config.requests_per_hour,
                remaining=0,
                reset_at=self._global_hour_bucket.reset_at,
                retry_after=self._global_hour_bucket.reset_at - time.time()
            )

        # 检查单客户端限制
        client_key = self._get_client_key(client_ip, session_id)
        if client_key not in self._client_buckets:
            self._client_buckets[client_key] = RateLimitBucket()

        allowed, client_remaining, client_reset = self._client_buckets[client_key].check_and_increment(
            self.config.per_client_per_minute,
            60.0
        )
        if not allowed:
            return RateLimitResult(
                allowed=False,
                limit=self.config.per_client_per_minute,
                remaining=0,
                reset_at=client_reset,
                retry_after=client_reset - time.time()
            )

        return RateLimitResult(
            allowed=True,
            limit=self.config.requests_per_minute,
            remaining=remaining,
            reset_at=reset_at
        )

    def record_tokens(self, tokens_used: int) -> RateLimitResult:
        """
        记录 Token 消耗

        Args:
            tokens_used: 消耗的 Token 数量

        Returns:
            RateLimitResult
        """
        if not self.config.enabled:
            return RateLimitResult(
                allowed=True,
                limit=self.config.tokens_per_minute,
                remaining=self.config.tokens_per_minute,
                reset_at=time.time() + 60
            )

        # 更新 Token 计数（每分钟）
        now = time.time()
        if now >= self._token_minute_bucket.reset_at:
            self._token_minute_bucket.count = 0
            self._token_minute_bucket.reset_at = now + 60
        self._token_minute_bucket.count += tokens_used

        # 更新 Token 计数（每小时）
        if now >= self._token_hour_bucket.reset_at:
            self._token_hour_bucket.count = 0
            self._token_hour_bucket.reset_at = now + 3600
        self._token_hour_bucket.count += tokens_used

        # 检查是否超限
        minute_remaining = max(
            0,
            self.config.tokens_per_minute - self._token_minute_bucket.count
        )

        return RateLimitResult(
            allowed=minute_remaining > 0,
            limit=self.config.tokens_per_minute,
            remaining=minute_remaining,
            reset_at=self._token_minute_bucket.reset_at
        )

    def get_headers(self) -> Dict[str, str]:
        """获取速率限制响应头"""
        if not self.config.include_headers:
            return {}

        return {
            "X-RateLimit-Limit": str(self.config.requests_per_minute),
            "X-RateLimit-Remaining": str(
                max(0, self.config.requests_per_minute - self._global_minute_bucket.count)
            ),
            "X-RateLimit-Reset": str(int(self._global_minute_bucket.reset_at))
        }

    def cleanup_stale_buckets(self, max_age: float = 3600.0) -> int:
        """
        清理过期的客户端桶

        Args:
            max_age: 最大保留时间（秒）

        Returns:
            清理的桶数量
        """
        now = time.time()
        stale_keys = [
            key for key, bucket in self._client_buckets.items()
            if now - bucket.reset_at > max_age
        ]
        for key in stale_keys:
            del self._client_buckets[key]
        return len(stale_keys)
```

### 4.2 重试与退避策略

```python
# src/pg_mcp/resilience/backoff.py

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BackoffStrategyType(str, Enum):
    """退避策略类型"""
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class BackoffStrategy(ABC):
    """退避策略接口"""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        计算第 N 次重试前的等待时间

        Args:
            attempt: 重试次数（从 1 开始）

        Returns:
            等待时间（秒）
        """
        pass


@dataclass
class ExponentialBackoff(BackoffStrategy):
    """
    指数退避策略

    delay = min(initial_delay * (multiplier ^ attempt) + jitter, max_delay)
    """
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True  # 添加随机抖动

    def get_delay(self, attempt: int) -> float:
        delay = self.initial_delay * (self.multiplier ** attempt)

        if self.jitter:
            # 添加 ±25% 随机抖动
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return min(delay, self.max_delay)


@dataclass
class FixedBackoff(BackoffStrategy):
    """固定间隔退避策略"""
    delay: float = 1.0

    def get_delay(self, attempt: int) -> float:
        return self.delay


@dataclass
class FibonacciBackoff(BackoffStrategy):
    """
    斐波那契退避策略

    delay = fib(attempt) * base_delay
    """
    base_delay: float = 1.0
    max_delay: float = 30.0

    def get_delay(self, attempt: int) -> float:
        # 计算斐波那契数
        a, b = 1, 1
        for _ in range(attempt - 1):
            a, b = b, a + b

        delay = a * self.base_delay
        return min(delay, self.max_delay)


def create_backoff_strategy(
    strategy_type: BackoffStrategyType,
    **kwargs
) -> BackoffStrategy:
    """工厂方法：创建退避策略"""
    if strategy_type == BackoffStrategyType.EXPONENTIAL:
        return ExponentialBackoff(**kwargs)
    elif strategy_type == BackoffStrategyType.FIXED:
        return FixedBackoff(**kwargs)
    elif strategy_type == BackoffStrategyType.FIBONACCI:
        return FibonacciBackoff(**kwargs)
    else:
        raise ValueError(f"Unknown backoff strategy: {strategy_type}")
```

```python
# src/pg_mcp/resilience/retry_executor.py

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Awaitable, TypeVar, Set

import structlog

from pg_mcp.resilience.backoff import BackoffStrategy, BackoffStrategyType, create_backoff_strategy


logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "rate_limit",
        "timeout",
        "server_error",
        "connection_lost"
    })


@dataclass
class OpenAIRetryConfig(RetryConfig):
    """OpenAI API 重试配置"""
    max_retries: int = 3
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 30.0
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "rate_limit",
        "timeout",
        "server_error"
    })


@dataclass
class DatabaseRetryConfig(RetryConfig):
    """数据库操作重试配置"""
    max_retries: int = 2
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.FIXED
    initial_delay: float = 0.5
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "connection_lost",
        "timeout"
    })


class RetryExecutor:
    """
    带重试的执行器

    职责:
    - 执行操作，失败时按策略重试
    - 支持自定义可重试错误判断
    - 记录重试日志
    """

    def __init__(self, config: RetryConfig):
        self.config = config
        self.backoff = create_backoff_strategy(
            config.backoff_strategy,
            initial_delay=config.initial_delay,
            max_delay=config.max_delay,
            multiplier=config.multiplier
        )

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
        is_retryable: Callable[[Exception], bool] | None = None
    ) -> T:
        """
        执行操作，失败时按策略重试

        Args:
            operation: 要执行的异步操作
            operation_name: 操作名称（用于日志）
            is_retryable: 自定义的可重试判断函数

        Returns:
            操作结果

        Raises:
            最后一次失败的异常
        """
        last_exception = None

        for attempt in range(1, self.config.max_retries + 2):  # +1 for initial try
            try:
                return await operation()
            except Exception as e:
                last_exception = e

                # 判断是否可重试
                if is_retryable:
                    retryable = is_retryable(e)
                else:
                    retryable = self._is_default_retryable(e)

                if not retryable or attempt > self.config.max_retries:
                    logger.warning(
                        "operation_failed_not_retryable",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                        retryable=retryable
                    )
                    raise

                # 计算等待时间
                delay = self.backoff.get_delay(attempt)

                logger.info(
                    "operation_retry",
                    operation=operation_name,
                    attempt=attempt,
                    delay=delay,
                    error=str(e)
                )

                await asyncio.sleep(delay)

        # 不应该到达这里
        raise last_exception  # type: ignore

    def _is_default_retryable(self, error: Exception) -> bool:
        """默认的可重试判断"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        for retryable in self.config.retryable_errors:
            if retryable in error_str or retryable in error_type:
                return True

        return False


class OpenAIRetryExecutor(RetryExecutor):
    """OpenAI API 专用重试执行器"""

    def __init__(self, config: OpenAIRetryConfig | None = None):
        super().__init__(config or OpenAIRetryConfig())

    def _is_default_retryable(self, error: Exception) -> bool:
        """OpenAI 特定的可重试判断"""
        # 检查 OpenAI SDK 特定错误类型
        error_type = type(error).__name__

        # RateLimitError, APITimeoutError, InternalServerError 可重试
        if error_type in ("RateLimitError", "APITimeoutError", "InternalServerError"):
            return True

        # AuthenticationError, InvalidRequestError 不可重试
        if error_type in ("AuthenticationError", "InvalidRequestError"):
            return False

        return super()._is_default_retryable(error)


class DatabaseRetryExecutor(RetryExecutor):
    """数据库操作专用重试执行器"""

    def __init__(self, config: DatabaseRetryConfig | None = None):
        super().__init__(config or DatabaseRetryConfig())

    def _is_default_retryable(self, error: Exception) -> bool:
        """数据库特定的可重试判断"""
        error_type = type(error).__name__
        error_str = str(error).lower()

        # 连接丢失可重试
        if "connection" in error_str and ("lost" in error_str or "closed" in error_str):
            return True

        # 超时可重试
        if "timeout" in error_str or "TimeoutError" in error_type:
            return True

        # 语法错误不可重试
        if "syntax" in error_str or "SyntaxError" in error_type:
            return False

        return super()._is_default_retryable(error)
```

---

## 5. 可观测性设计

### 5.1 Prometheus 指标

```python
# src/pg_mcp/observability/metrics.py

from typing import Dict, Optional

from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
import structlog


logger = structlog.get_logger()


class MetricsCollector:
    """
    Prometheus 指标收集器

    职责:
    - 定义和暴露所有系统指标
    - 提供便捷的指标记录方法
    - 支持自定义 Registry（用于测试）
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """初始化所有指标"""

        # ============ 请求指标 ============
        self.requests_total = Counter(
            "pg_mcp_requests_total",
            "Total number of requests",
            ["database", "status", "error_code"],
            registry=self.registry
        )

        self.request_duration = Histogram(
            "pg_mcp_request_duration_seconds",
            "Request duration in seconds",
            ["database"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        self.requests_in_flight = Gauge(
            "pg_mcp_requests_in_flight",
            "Number of requests currently being processed",
            ["database"],
            registry=self.registry
        )

        # ============ SQL 生成指标 ============
        self.sql_generation_total = Counter(
            "pg_mcp_sql_generation_total",
            "Total number of SQL generation attempts",
            ["database", "status"],
            registry=self.registry
        )

        self.sql_generation_duration = Histogram(
            "pg_mcp_sql_generation_duration_seconds",
            "SQL generation duration in seconds",
            ["database"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )

        self.sql_retries_total = Counter(
            "pg_mcp_sql_retries_total",
            "Total number of SQL generation retries",
            ["database", "reason"],
            registry=self.registry
        )

        # ============ 数据库指标 ============
        self.db_pool_size = Gauge(
            "pg_mcp_db_pool_size",
            "Database connection pool size",
            ["database"],
            registry=self.registry
        )

        self.db_pool_available = Gauge(
            "pg_mcp_db_pool_available",
            "Available connections in pool",
            ["database"],
            registry=self.registry
        )

        self.db_query_duration = Histogram(
            "pg_mcp_db_query_duration_seconds",
            "Database query execution duration",
            ["database"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )

        # ============ OpenAI 指标 ============
        self.openai_tokens_total = Counter(
            "pg_mcp_openai_tokens_used_total",
            "Total OpenAI tokens used",
            ["type"],  # prompt, completion
            registry=self.registry
        )

        self.openai_requests_total = Counter(
            "pg_mcp_openai_requests_total",
            "Total OpenAI API requests",
            ["status"],
            registry=self.registry
        )

        self.openai_request_duration = Histogram(
            "pg_mcp_openai_request_duration_seconds",
            "OpenAI API request duration",
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )

        # ============ 速率限制指标 ============
        self.rate_limit_current = Gauge(
            "pg_mcp_rate_limit_current",
            "Current rate limit usage",
            ["limit_type"],  # requests_minute, requests_hour, tokens_minute
            registry=self.registry
        )

        self.rate_limit_exceeded_total = Counter(
            "pg_mcp_rate_limit_exceeded_total",
            "Total number of rate limit exceeded events",
            ["limit_type"],
            registry=self.registry
        )

        # ============ 策略检查指标 ============
        self.policy_check_total = Counter(
            "pg_mcp_policy_check_total",
            "Total number of policy checks",
            ["check_type", "result"],  # table/column/explain, passed/denied
            registry=self.registry
        )

        # ============ 服务信息 ============
        self.service_info = Info(
            "pg_mcp_service",
            "Service information",
            registry=self.registry
        )

    # ============ 便捷方法 ============

    def record_request(
        self,
        database: str,
        status: str,
        duration: float,
        error_code: Optional[str] = None
    ) -> None:
        """记录请求"""
        self.requests_total.labels(
            database=database,
            status=status,
            error_code=error_code or ""
        ).inc()
        self.request_duration.labels(database=database).observe(duration)

    def record_sql_generation(
        self,
        database: str,
        status: str,
        duration: float
    ) -> None:
        """记录 SQL 生成"""
        self.sql_generation_total.labels(
            database=database,
            status=status
        ).inc()
        self.sql_generation_duration.labels(database=database).observe(duration)

    def record_sql_retry(self, database: str, reason: str) -> None:
        """记录 SQL 重试"""
        self.sql_retries_total.labels(database=database, reason=reason).inc()

    def record_db_query(self, database: str, duration: float) -> None:
        """记录数据库查询"""
        self.db_query_duration.labels(database=database).observe(duration)

    def record_openai_request(
        self,
        status: str,
        duration: float,
        prompt_tokens: int,
        completion_tokens: int
    ) -> None:
        """记录 OpenAI 请求"""
        self.openai_requests_total.labels(status=status).inc()
        self.openai_request_duration.observe(duration)
        self.openai_tokens_total.labels(type="prompt").inc(prompt_tokens)
        self.openai_tokens_total.labels(type="completion").inc(completion_tokens)

    def record_rate_limit_exceeded(self, limit_type: str) -> None:
        """记录速率限制超限"""
        self.rate_limit_exceeded_total.labels(limit_type=limit_type).inc()

    def record_policy_check(self, check_type: str, result: str) -> None:
        """记录策略检查"""
        self.policy_check_total.labels(
            check_type=check_type,
            result=result
        ).inc()

    def update_pool_stats(self, database: str, size: int, available: int) -> None:
        """更新连接池统计"""
        self.db_pool_size.labels(database=database).set(size)
        self.db_pool_available.labels(database=database).set(available)

    def update_rate_limit_stats(
        self,
        requests_minute: int,
        requests_hour: int,
        tokens_minute: int
    ) -> None:
        """更新速率限制统计"""
        self.rate_limit_current.labels(limit_type="requests_minute").set(requests_minute)
        self.rate_limit_current.labels(limit_type="requests_hour").set(requests_hour)
        self.rate_limit_current.labels(limit_type="tokens_minute").set(tokens_minute)

    def set_service_info(self, version: str, **kwargs) -> None:
        """设置服务信息"""
        self.service_info.info({"version": version, **kwargs})

    def generate_metrics(self) -> bytes:
        """生成 Prometheus 格式的指标数据"""
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """获取指标数据的 Content-Type"""
        return CONTENT_TYPE_LATEST
```

### 5.2 OpenTelemetry 追踪

```python
# src/pg_mcp/observability/tracing.py

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Generator, Any

import structlog


logger = structlog.get_logger()


@dataclass
class TracingConfig:
    """追踪配置"""
    enabled: bool = False
    exporter: str = "otlp"  # otlp, jaeger, zipkin
    endpoint: str = "http://localhost:4317"
    sample_rate: float = 0.1
    service_name: str = "pg-mcp"


class TracingManager:
    """
    OpenTelemetry 追踪管理器

    职责:
    - 初始化 OpenTelemetry SDK
    - 提供便捷的 span 创建方法
    - 支持多种导出器
    """

    def __init__(self, config: TracingConfig):
        self.config = config
        self._tracer = None

        if config.enabled:
            self._setup_tracing()

    def _setup_tracing(self) -> None:
        """初始化追踪"""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
            from opentelemetry.sdk.resources import Resource

            # 创建资源
            resource = Resource.create({
                "service.name": self.config.service_name,
            })

            # 创建采样器
            sampler = TraceIdRatioBased(self.config.sample_rate)

            # 创建 TracerProvider
            provider = TracerProvider(
                resource=resource,
                sampler=sampler
            )

            # 配置导出器
            self._setup_exporter(provider)

            # 设置全局 TracerProvider
            trace.set_tracer_provider(provider)

            # 获取 tracer
            self._tracer = trace.get_tracer(__name__)

            logger.info(
                "tracing_initialized",
                exporter=self.config.exporter,
                sample_rate=self.config.sample_rate
            )

        except ImportError as e:
            logger.warning(
                "tracing_disabled_missing_dependency",
                error=str(e)
            )
            self.config.enabled = False

    def _setup_exporter(self, provider) -> None:
        """配置导出器"""
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        if self.config.exporter == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter
            )
            exporter = OTLPSpanExporter(endpoint=self.config.endpoint)

        elif self.config.exporter == "jaeger":
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            exporter = JaegerExporter(
                agent_host_name=self.config.endpoint.split(":")[0],
                agent_port=int(self.config.endpoint.split(":")[1])
            )

        elif self.config.exporter == "zipkin":
            from opentelemetry.exporter.zipkin.json import ZipkinExporter
            exporter = ZipkinExporter(endpoint=self.config.endpoint)

        else:
            raise ValueError(f"Unknown exporter: {self.config.exporter}")

        provider.add_span_processor(BatchSpanProcessor(exporter))

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[dict] = None
    ) -> Generator[Any, None, None]:
        """
        创建追踪 span

        Args:
            name: span 名称
            attributes: span 属性

        Yields:
            span 对象（如果追踪启用）
        """
        if not self.config.enabled or self._tracer is None:
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    def get_current_trace_id(self) -> Optional[str]:
        """获取当前 trace ID"""
        if not self.config.enabled:
            return None

        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span:
                return format(span.get_span_context().trace_id, '032x')
        except Exception:
            pass

        return None


# 全局 TracingManager 实例
_tracing_manager: Optional[TracingManager] = None


def init_tracing(config: TracingConfig) -> TracingManager:
    """初始化全局追踪管理器"""
    global _tracing_manager
    _tracing_manager = TracingManager(config)
    return _tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """获取全局追踪管理器"""
    return _tracing_manager
```

### 5.3 日志增强

```python
# src/pg_mcp/observability/logging.py

import sys
from dataclasses import dataclass
from typing import Any

import structlog


@dataclass
class LoggingConfig:
    """日志配置"""
    include_trace_id: bool = True
    log_sql: bool = False  # 可能包含敏感数据
    slow_query_threshold: float = 5.0  # 秒
    level: str = "INFO"
    format: str = "json"  # json, console


def add_trace_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict
) -> dict:
    """添加 trace_id 到日志"""
    from pg_mcp.observability.tracing import get_tracing_manager

    manager = get_tracing_manager()
    if manager:
        trace_id = manager.get_current_trace_id()
        if trace_id:
            event_dict["trace_id"] = trace_id

    return event_dict


def setup_logging(config: LoggingConfig) -> None:
    """配置结构化日志"""

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # 添加 trace_id
    if config.include_trace_id:
        processors.append(add_trace_id)

    # 选择输出格式
    if config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib, config.level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class SlowQueryLogger:
    """慢查询日志记录器"""

    def __init__(self, threshold: float = 5.0, log_sql: bool = False):
        self.threshold = threshold
        self.log_sql = log_sql
        self.logger = structlog.get_logger()

    def log_if_slow(
        self,
        duration: float,
        database: str,
        sql: str,
        rows: int
    ) -> None:
        """如果查询超过阈值则记录日志"""
        if duration < self.threshold:
            return

        log_data: dict[str, Any] = {
            "database": database,
            "duration_seconds": round(duration, 3),
            "rows_returned": rows,
        }

        if self.log_sql:
            log_data["sql"] = sql[:500]  # 截断
        else:
            log_data["sql_length"] = len(sql)

        self.logger.warning("slow_query_detected", **log_data)
```

---

## 6. 配置验证设计

### 6.1 配置验证器

```python
# src/pg_mcp/config/validators.py

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import structlog
import yaml

from pg_mcp.config.models import AppConfig, AccessPolicyConfig


logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    errors: List[str]
    warnings: List[str]


class ConfigValidator:
    """
    配置验证器

    职责:
    - 验证配置文件语法
    - 检查配置一致性
    - 检测潜在问题并发出警告
    """

    def validate_file(self, config_path: str) -> ValidationResult:
        """
        验证配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        path = Path(config_path)

        # 检查文件存在
        if not path.exists():
            return ValidationResult(
                success=False,
                errors=[f"Config file not found: {config_path}"],
                warnings=[]
            )

        # 解析 YAML
        try:
            with open(path) as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return ValidationResult(
                success=False,
                errors=[f"YAML syntax error: {e}"],
                warnings=[]
            )

        # 验证 Pydantic 模型
        try:
            config = AppConfig(**config_dict)
        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[f"Configuration validation error: {e}"],
                warnings=[]
            )

        # 验证数据库配置
        db_warnings = self._validate_databases(config)
        warnings.extend(db_warnings)

        # 验证访问策略
        for db in config.databases:
            if hasattr(db, 'access_policy') and db.access_policy:
                policy_warnings = self._validate_access_policy(
                    db.name,
                    db.access_policy
                )
                warnings.extend(policy_warnings)

        return ValidationResult(
            success=True,
            errors=[],
            warnings=warnings
        )

    def _validate_databases(self, config: AppConfig) -> List[str]:
        """验证数据库配置"""
        warnings = []

        # 检查数据库名称唯一性
        names = [db.name for db in config.databases]
        if len(names) != len(set(names)):
            warnings.append("Duplicate database names detected")

        return warnings

    def _validate_access_policy(
        self,
        db_name: str,
        policy: AccessPolicyConfig
    ) -> List[str]:
        """验证访问策略配置"""
        warnings = []

        # 检查配置一致性
        try:
            policy_warnings = policy.validate_consistency()
            warnings.extend([f"[{db_name}] {w}" for w in policy_warnings])
        except ValueError as e:
            warnings.append(f"[{db_name}] Policy conflict: {e}")

        # 检查过于宽松的配置
        if not policy.tables.allowed and not policy.tables.denied:
            warnings.append(
                f"[{db_name}] No table access restrictions configured"
            )

        if not policy.columns.denied and not policy.columns.denied_patterns:
            warnings.append(
                f"[{db_name}] No column access restrictions configured"
            )

        return warnings

    def print_validation_result(self, result: ValidationResult) -> None:
        """打印验证结果"""
        if result.success:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has errors:")
            for error in result.errors:
                print(f"  ERROR: {error}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")


def validate_config_command(config_path: str) -> int:
    """
    配置验证命令入口

    用法:
        pg-mcp config validate --config /path/to/config.yaml

    Returns:
        退出码 (0=成功, 1=失败)
    """
    validator = ConfigValidator()
    result = validator.validate_file(config_path)
    validator.print_validation_result(result)

    # 统计信息
    if result.success:
        print(f"\n✓ Databases configured: {len(result.errors) == 0}")
        print(f"✓ Access policies: No conflicts detected")

    return 0 if result.success else 1
```

---

## 7. 数据模型扩展

### 7.1 新增错误码

```python
# src/pg_mcp/models/errors.py (扩展)

class ErrorCode(str, Enum):
    """错误码"""
    # ... 现有错误码 ...
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

    # [NEW] 访问控制相关
    ACCESS_DENIED = "ACCESS_DENIED"
    TABLE_ACCESS_DENIED = "TABLE_ACCESS_DENIED"
    COLUMN_ACCESS_DENIED = "COLUMN_ACCESS_DENIED"
    SCHEMA_ACCESS_DENIED = "SCHEMA_ACCESS_DENIED"

    # [NEW] EXPLAIN 策略相关
    QUERY_TOO_EXPENSIVE = "QUERY_TOO_EXPENSIVE"
    SEQ_SCAN_DENIED = "SEQ_SCAN_DENIED"

    # [NEW] 配置相关
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


# HTTP 状态码映射
ERROR_HTTP_STATUS_MAP = {
    ErrorCode.UNKNOWN_DATABASE: 404,
    ErrorCode.AMBIGUOUS_QUERY: 400,
    ErrorCode.UNSAFE_SQL: 400,
    ErrorCode.SYNTAX_ERROR: 400,
    ErrorCode.TABLE_ACCESS_DENIED: 403,
    ErrorCode.COLUMN_ACCESS_DENIED: 403,
    ErrorCode.SCHEMA_ACCESS_DENIED: 403,
    ErrorCode.QUERY_TOO_EXPENSIVE: 400,
    ErrorCode.SEQ_SCAN_DENIED: 400,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.EXECUTION_TIMEOUT: 504,
    ErrorCode.CONNECTION_ERROR: 503,
    ErrorCode.OPENAI_ERROR: 502,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}
```

### 7.2 配置模型扩展

```python
# src/pg_mcp/config/models.py (扩展)

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MetricsConfig(BaseModel):
    """指标配置"""
    enabled: bool = True
    exporter: str = "prometheus"  # prometheus, otlp
    port: int = Field(default=9090, ge=1024, le=65535)
    path: str = "/metrics"


class TracingConfig(BaseModel):
    """追踪配置"""
    enabled: bool = False
    exporter: str = "otlp"  # otlp, jaeger, zipkin
    endpoint: str = "http://localhost:4317"
    sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    service_name: str = "pg-mcp"


class LoggingConfig(BaseModel):
    """日志配置"""
    include_trace_id: bool = True
    log_sql: bool = False
    slow_query_threshold: float = Field(default=5.0, ge=0.1)


class ObservabilityConfig(BaseModel):
    """可观测性配置"""
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class AuditConfig(BaseModel):
    """审计日志配置"""
    enabled: bool = True
    storage: str = "file"  # file, stdout, database
    file_path: str | None = None
    max_size_mb: int = Field(default=100, ge=10)
    max_files: int = Field(default=10, ge=1)
    redact_sql: bool = False


class DatabaseConfig(BaseModel):
    """数据库配置 (扩展)"""
    # ... 现有字段 ...
    name: str = "main"
    host: str | None = None
    port: int = 5432
    # ...

    # [NEW] 访问策略
    access_policy: AccessPolicyConfig = Field(
        default_factory=AccessPolicyConfig
    )


class AppConfig(BaseModel):
    """应用总配置 (扩展)"""
    databases: list[DatabaseConfig]
    openai: "OpenAISettings"
    server: "ServerSettings" = Field(default_factory=lambda: ServerSettings())
    rate_limit: "RateLimitSettings" = Field(default_factory=lambda: RateLimitSettings())

    # [NEW] 可观测性
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig
    )

    # [NEW] 重试配置
    retry: "RetrySettings" = Field(
        default_factory=lambda: RetrySettings()
    )

    # [NEW] 审计配置
    audit: AuditConfig = Field(default_factory=AuditConfig)
```

---

## 8. 实施计划

### 8.1 阶段划分

```
Phase A: 安全控制 (估算: 3-4 天)
├── A.1: 数据模型
│   ├── AccessPolicyConfig 及子模型
│   ├── 新增错误码和异常类
│   └── 单元测试
├── A.2: 访问策略执行器
│   ├── DatabaseAccessPolicy 实现
│   ├── Schema/表/列验证逻辑
│   └── 单元测试 (覆盖率 >= 95%)
├── A.3: EXPLAIN 验证器
│   ├── ExplainValidator 实现
│   ├── 缓存和超时机制
│   └── 单元测试
├── A.4: 查询执行器重构
│   ├── QueryExecutor 实现
│   ├── QueryExecutorManager 实现
│   └── 集成测试
└── A.5: 审计日志
    ├── AuditLogger 实现
    └── 集成测试

Phase B: 弹性机制 (估算: 2-3 天)
├── B.1: 速率限制集成
│   ├── RateLimiter 重构
│   ├── 集成到请求处理流程
│   └── 单元测试
├── B.2: 重试执行器
│   ├── BackoffStrategy 实现
│   ├── RetryExecutor 实现
│   └── 单元测试
└── B.3: 集成测试
    └── 完整流程测试

Phase C: 可观测性 (估算: 2 天)
├── C.1: 指标暴露
│   ├── MetricsCollector 实现
│   ├── /metrics 端点
│   └── 单元测试
├── C.2: 追踪集成
│   ├── TracingManager 实现
│   ├── Span 埋点
│   └── 集成测试
└── C.3: 日志增强
    ├── 结构化日志配置
    └── 慢查询日志

Phase D: 代码质量 (估算: 2 天)
├── D.1: 代码清理
│   ├── 移除冗余 to_dict() 方法
│   ├── 统一工具函数
│   └── 清理未使用配置
├── D.2: 测试补充
│   ├── 安全测试 (SQL 注入 fuzz)
│   ├── 访问控制绕过测试
│   └── 达到目标覆盖率
└── D.3: 配置验证工具
    └── validate 命令实现
```

### 8.2 依赖关系

```
A.1 ──┬──> A.2 ──> A.4
      │
      └──> A.3 ──> A.4
                    │
                    └──> A.5
                          │
B.1 ──────────────────────┼──> B.3
                          │
B.2 ──────────────────────┘
                          │
C.1 ──────────────────────┼──> C.3
                          │
C.2 ──────────────────────┘
                          │
D.1 ──> D.2 ──> D.3 ──────┘
```

### 8.3 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| 访问策略配置复杂 | 提供 `pg-mcp config validate` 命令和示例配置 |
| EXPLAIN 验证性能 | 5 秒超时 + 结果缓存 (60s TTL) |
| 速率限制误伤 | 默认值足够宽松，可配置禁用 |
| OpenTelemetry 依赖 | 可选安装，追踪默认禁用 |

---

## 9. 验收标准

### 9.1 功能验收

**P0 - 安全控制**:
- [ ] `pg-mcp config validate` 命令正确检测配置冲突
- [ ] 表级访问控制：白名单/黑名单模式正确工作
- [ ] 列级访问控制：显式列和 SELECT * 场景正确处理
- [ ] EXPLAIN 策略：超限拒绝，大表全表扫描拒绝
- [ ] 审计日志：完整记录查询上下文

**P1 - 弹性机制**:
- [ ] 速率限制在 MCP 层生效
- [ ] Token 消耗被正确累计
- [ ] 重试执行器按配置重试
- [ ] 非可重试错误立即失败

**P2 - 可观测性**:
- [ ] `/metrics` 返回 Prometheus 格式
- [ ] 追踪 span 正确创建（如启用）
- [ ] 慢查询被记录

### 9.2 测试覆盖率

| 模块 | 目标覆盖率 |
|------|-----------|
| `security/access_policy.py` | >= 95% |
| `security/explain_validator.py` | >= 90% |
| `resilience/rate_limiter.py` | >= 80% |
| `resilience/retry_executor.py` | >= 85% |
| `observability/metrics.py` | >= 80% |
| **总体** | >= 85% |

---

## 10. 附录

### 附录 A: 完整配置示例

```yaml
# config.yaml

databases:
  - name: "production"
    host: "localhost"
    port: 5432
    dbname: "mydb"
    user: "mcp_readonly"
    password: "${DB_PASSWORD}"
    ssl_mode: "prefer"
    min_pool_size: 2
    max_pool_size: 10

    access_policy:
      allowed_schemas:
        - "public"
        - "analytics"
      tables:
        allowed:
          - "orders"
          - "products"
          - "users"
        denied:
          - "user_credentials"
      columns:
        denied:
          - "users.password_hash"
          - "users.ssn"
        denied_patterns:
          - "*._password*"
          - "*._secret*"
        on_denied: "reject"
        select_star_policy: "reject"
      explain_policy:
        enabled: true
        max_estimated_rows: 100000
        max_estimated_cost: 10000
        deny_seq_scan_on_large_tables: true
        large_table_threshold: 10000

openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o-mini"

server:
  max_result_rows: 1000
  query_timeout: 30.0

rate_limit:
  enabled: true
  requests_per_minute: 60
  tokens_per_minute: 100000

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: false
  logging:
    slow_query_threshold: 5.0

audit:
  enabled: true
  storage: "file"
  file_path: "/var/log/pg-mcp/audit.jsonl"
```

---

## 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-15 | 初始版本 | - |
| 1.1 | 2026-01-15 | Review 修订: (1) 补充 ParsedSQLInfo 数据结构定义; (2) 添加 QueryService 集成设计; (3) 添加 enable_result_validation 功能设计; (4) 修复 AuditLogger 异步 IO 问题; (5) 补充 SQL Parser 扩展说明 | - |
