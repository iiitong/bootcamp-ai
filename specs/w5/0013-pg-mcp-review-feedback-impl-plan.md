# PostgreSQL MCP Server 代码审查反馈实施计划

**版本**: 1.0
**创建日期**: 2026-01-15
**关联文档**:
- [0012-pg-mcp-new-features-code-review.md](./0012-pg-mcp-new-features-code-review.md) - 代码审查报告

---

## 1. 概述

本文档定义代码审查反馈的实施计划，包括：
- 完成待完成功能
- 加强边缘场景测试
- 提升测试覆盖率

### 1.1 任务依赖图

```
E.1 QueryService 集成
 │
 ├── E.2 /metrics HTTP 端点
 │
 └── E.3 enable_result_validation 实现
      │
      └── E.4 边缘场景测试增强
           │
           └── E.5 集成测试完善
```

### 1.2 工作量估算

| 任务 | 优先级 | 复杂度 |
|------|--------|--------|
| E.1 QueryService 集成 | P0 | 中 |
| E.2 /metrics HTTP 端点 | P1 | 低 |
| E.3 enable_result_validation | P2 | 中 |
| E.4 边缘场景测试 | P1 | 中 |
| E.5 集成测试完善 | P1 | 中 |

---

## 2. 任务 E.1: QueryService 集成

**目标**: 将 QueryExecutor 和 QueryExecutorManager 集成到 QueryService

**前置条件**: 无

### 2.1 修改 QueryService

**文件**: `src/pg_mcp/services/query_service.py`

```python
class QueryService:
    """Query service with integrated security and resilience."""

    def __init__(
        self,
        config: QueryServiceConfig,
        app_config: AppConfig,
        pool_manager: DatabasePoolManager,
        schema_cache: SchemaCache,
        openai_client: OpenAIClient,
        sql_parser: SQLParser,
        rate_limiter: RateLimiter | None = None,
        metrics_collector: MetricsCollector | None = None,  # 新增
        audit_logger: AuditLogger | None = None,  # 新增
    ):
        self._executor_manager = QueryExecutorManager()  # 新增
        self._metrics = metrics_collector
        self._audit_logger = audit_logger

        # 为每个数据库注册执行器
        for db_config in app_config.databases:
            self._register_database_executor(db_config)

    def _register_database_executor(self, db_config: DatabaseConfig) -> None:
        """Register executor for a database."""
        access_policy = DatabaseAccessPolicy(db_config.access_policy)
        explain_validator = ExplainValidator(db_config.access_policy.explain_policy)

        self._executor_manager.register_database(
            name=db_config.name,
            pool=self._pool_manager.get_pool(db_config.name),
            sql_parser=self._sql_parser,
            access_policy=access_policy,
            explain_validator=explain_validator,
            audit_logger=self._audit_logger,
        )

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute query with full security and observability."""
        context = ExecutionContext(
            request_id=str(uuid.uuid4()),
            client_ip=request.client_ip,
            session_id=request.session_id,
        )

        # 使用 metrics 追踪
        if self._metrics:
            with self._metrics.track_request(request.database or "default"):
                return await self._execute_with_executor(request, context)
        else:
            return await self._execute_with_executor(request, context)

    async def _execute_with_executor(
        self,
        request: QueryRequest,
        context: ExecutionContext
    ) -> QueryResponse:
        """Execute using QueryExecutor."""
        # 1. 获取执行器
        executor = self._executor_manager.get_executor(request.database)

        # 2. 生成 SQL
        sql = await self._generate_sql(request)

        # 3. 通过执行器执行（包含策略检查、EXPLAIN、审计）
        result = await executor.execute(
            sql=sql,
            limit=request.limit or self.config.max_result_rows,
            context=context,
            question=request.question,
        )

        return QueryResponse(
            success=True,
            sql=sql,
            result=result,
        )
```

### 2.2 更新 Server 初始化

**文件**: `src/pg_mcp/server.py`

```python
from pg_mcp.observability.metrics import MetricsCollector
from pg_mcp.security.audit_logger import AuditLogger

class PgMcpServer:
    def __init__(self, config: AppConfig) -> None:
        # ... 现有代码 ...

        # 新增：可观测性和审计
        self._metrics_collector = MetricsCollector() if config.observability.metrics.enabled else None
        self._audit_logger = self._create_audit_logger(config.audit) if config.audit.enabled else None

        # 更新 QueryService 初始化
        self._query_service = QueryService(
            config=query_config,
            app_config=config,
            pool_manager=self._pool_manager,
            schema_cache=self._schema_cache,
            openai_client=self._openai_client,
            sql_parser=self._sql_parser,
            rate_limiter=self._rate_limiter,
            metrics_collector=self._metrics_collector,  # 新增
            audit_logger=self._audit_logger,  # 新增
        )

    def _create_audit_logger(self, config: AuditConfig) -> AuditLogger:
        """Create audit logger from config."""
        from pg_mcp.security.audit_logger import AuditStorage
        return AuditLogger(
            storage=AuditStorage(config.storage),
            file_path=config.file_path,
            max_size_mb=config.max_size_mb,
            max_files=config.max_files,
            redact_sql=config.redact_sql,
        )
```

### 2.3 单元测试

**文件**: `tests/unit/test_query_service_integration.py`

```python
class TestQueryServiceWithExecutor:
    """Tests for QueryService with QueryExecutor integration."""

    async def test_execute_with_policy_check(self): ...
    async def test_execute_with_explain_validation(self): ...
    async def test_execute_with_audit_logging(self): ...
    async def test_execute_with_metrics(self): ...
    async def test_execute_denied_table(self): ...
    async def test_execute_denied_column(self): ...
```

---

## 3. 任务 E.2: /metrics HTTP 端点

**目标**: 暴露 Prometheus 指标端点

**前置条件**: E.1 完成

### 3.1 方案选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| A. 独立 HTTP 服务 | 隔离性好 | 需要额外端口 |
| B. FastMCP 扩展 | 无需额外端口 | 依赖框架支持 |
| C. 使用 prometheus_client 内置服务 | 简单 | 需要额外端口 |

**推荐**: 方案 C - 使用 prometheus_client 内置服务

### 3.2 实现

**文件**: `src/pg_mcp/observability/metrics_server.py`

```python
"""Prometheus metrics HTTP server."""

import threading
from prometheus_client import start_http_server, REGISTRY
import structlog

logger = structlog.get_logger()


class MetricsServer:
    """HTTP server for Prometheus metrics endpoint."""

    def __init__(self, port: int = 9090, path: str = "/metrics"):
        self.port = port
        self.path = path
        self._server_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        def _run_server():
            start_http_server(self.port)
            logger.info("metrics_server_started", port=self.port)

        self._server_thread = threading.Thread(target=_run_server, daemon=True)
        self._server_thread.start()

    def stop(self) -> None:
        """Stop the metrics server."""
        # prometheus_client 的 start_http_server 不支持优雅关闭
        # 由于使用 daemon=True，进程退出时会自动清理
        logger.info("metrics_server_stopped")


def start_metrics_server(config: "MetricsConfig") -> MetricsServer | None:
    """Start metrics server if enabled."""
    if not config.enabled:
        return None

    server = MetricsServer(port=config.port, path=config.path)
    server.start()
    return server
```

### 3.3 集成到 Server

**文件**: `src/pg_mcp/server.py` (修改)

```python
from pg_mcp.observability.metrics_server import start_metrics_server

class PgMcpServer:
    async def startup(self) -> None:
        # ... 现有代码 ...

        # 启动 metrics 服务器
        if self.config.observability.metrics.enabled:
            self._metrics_server = start_metrics_server(self.config.observability.metrics)
            self._logger.info(
                "Metrics server started",
                port=self.config.observability.metrics.port
            )
```

---

## 4. 任务 E.3: enable_result_validation 实现

**目标**: 实现 LLM 结果验证功能

**前置条件**: E.1 完成

### 4.1 功能说明

当查询返回空结果时，使用 LLM 验证是否合理：
- 检查 SQL 是否正确理解了用户意图
- 对于预期应有数据但返回空的情况给出警告

### 4.2 实现

**文件**: `src/pg_mcp/services/result_validator.py`

```python
"""LLM-based query result validation."""

from dataclasses import dataclass
import structlog

from pg_mcp.infrastructure.openai_client import OpenAIClient


logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """Result validation outcome."""
    is_valid: bool
    confidence: float  # 0.0 - 1.0
    explanation: str
    suggested_correction: str | None = None


class ResultValidator:
    """Validates query results using LLM."""

    VALIDATION_PROMPT = """
You are a SQL query result validator. Given:
- User's question: {question}
- Generated SQL: {sql}
- Result: {result_summary}

Determine if the result makes sense. If the result is empty, consider:
1. Is the query correctly understanding the user's intent?
2. Could there be a data issue (e.g., wrong table, wrong filter)?
3. Is empty result actually expected?

Respond in JSON format:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "explanation": "brief explanation",
    "suggested_correction": "SQL correction if needed, or null"
}}
"""

    def __init__(self, openai_client: OpenAIClient):
        self._client = openai_client

    async def validate(
        self,
        question: str,
        sql: str,
        row_count: int,
        sample_data: list[dict] | None = None,
    ) -> ValidationResult:
        """Validate query result."""
        # 只对空结果或可疑结果进行验证
        if row_count > 0 and row_count < 1000:
            return ValidationResult(
                is_valid=True,
                confidence=1.0,
                explanation="Result count is within expected range",
            )

        result_summary = self._summarize_result(row_count, sample_data)

        prompt = self.VALIDATION_PROMPT.format(
            question=question,
            sql=sql,
            result_summary=result_summary,
        )

        try:
            response = await self._client.generate_validation(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning("result_validation_failed", error=str(e))
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                explanation=f"Validation skipped: {e}",
            )

    def _summarize_result(
        self,
        row_count: int,
        sample_data: list[dict] | None
    ) -> str:
        """Create a summary of the result for LLM."""
        if row_count == 0:
            return "Empty result (0 rows)"

        summary = f"{row_count} rows returned"
        if sample_data:
            summary += f"\nSample columns: {list(sample_data[0].keys())}"

        return summary

    def _parse_response(self, response: str) -> ValidationResult:
        """Parse LLM response into ValidationResult."""
        import json
        try:
            data = json.loads(response)
            return ValidationResult(
                is_valid=data.get("is_valid", True),
                confidence=data.get("confidence", 0.5),
                explanation=data.get("explanation", ""),
                suggested_correction=data.get("suggested_correction"),
            )
        except json.JSONDecodeError:
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                explanation="Failed to parse validation response",
            )
```

### 4.3 集成到 QueryService

```python
# 在 QueryService._execute_with_executor 中添加
if self.config.enable_result_validation and result.row_count == 0:
    validation = await self._result_validator.validate(
        question=request.question,
        sql=sql,
        row_count=result.row_count,
    )
    if not validation.is_valid:
        logger.warning(
            "result_validation_warning",
            confidence=validation.confidence,
            explanation=validation.explanation,
        )
        # 可选：返回警告给用户
```

---

## 5. 任务 E.4: 边缘场景测试增强

**目标**: 增加边缘场景测试覆盖

**前置条件**: E.1 完成

### 5.1 SQL Parser 边缘场景

**文件**: `tests/unit/test_sql_parser_edge_cases.py`

```python
"""Edge case tests for SQL parser."""

import pytest
from pg_mcp.infrastructure.sql_parser import SQLParser


class TestSQLParserEdgeCases:
    """Edge case tests for SQL parser."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    # === 空值和特殊字符 ===

    def test_empty_string(self, parser: SQLParser) -> None:
        """Test empty SQL string."""
        result = parser.parse("")
        assert result.error_message is not None

    def test_whitespace_only(self, parser: SQLParser) -> None:
        """Test whitespace-only SQL."""
        result = parser.parse("   \n\t  ")
        assert result.error_message is not None

    def test_unicode_characters(self, parser: SQLParser) -> None:
        """Test SQL with unicode characters."""
        result = parser.parse("SELECT * FROM users WHERE name = '中文'")
        assert result.is_readonly is True

    def test_emoji_in_string(self, parser: SQLParser) -> None:
        """Test SQL with emoji in string literal."""
        result = parser.parse("SELECT * FROM posts WHERE content LIKE '%😀%'")
        assert result.is_readonly is True

    def test_null_byte(self, parser: SQLParser) -> None:
        """Test SQL with null byte."""
        result = parser.parse("SELECT * FROM users WHERE name = 'test\x00'")
        # Should either parse successfully or fail gracefully
        assert result.error_message is not None or result.is_readonly is True

    # === 极长输入 ===

    def test_very_long_query(self, parser: SQLParser) -> None:
        """Test very long SQL query."""
        columns = ", ".join([f"col{i}" for i in range(1000)])
        sql = f"SELECT {columns} FROM large_table"
        result = parser.parse(sql)
        assert result.is_readonly is True

    def test_deeply_nested_subquery(self, parser: SQLParser) -> None:
        """Test deeply nested subqueries."""
        sql = "SELECT * FROM t1"
        for i in range(20):
            sql = f"SELECT * FROM ({sql}) AS sub{i}"
        result = parser.parse(sql)
        assert result.is_readonly is True

    def test_many_joins(self, parser: SQLParser) -> None:
        """Test query with many JOINs."""
        sql = "SELECT * FROM t1"
        for i in range(50):
            sql += f" JOIN t{i+2} ON t{i+1}.id = t{i+2}.id"
        result = parser.parse(sql)
        assert result.is_readonly is True

    # === 复杂 CTE ===

    def test_recursive_cte(self, parser: SQLParser) -> None:
        """Test recursive CTE."""
        sql = """
        WITH RECURSIVE cte AS (
            SELECT 1 AS n
            UNION ALL
            SELECT n + 1 FROM cte WHERE n < 10
        )
        SELECT * FROM cte
        """
        result = parser.parse(sql)
        assert result.is_readonly is True

    def test_multiple_ctes(self, parser: SQLParser) -> None:
        """Test multiple CTEs."""
        sql = """
        WITH
            cte1 AS (SELECT 1 AS a),
            cte2 AS (SELECT 2 AS b),
            cte3 AS (SELECT * FROM cte1, cte2)
        SELECT * FROM cte3
        """
        result = parser.parse(sql)
        assert result.is_readonly is True

    # === 窗口函数 ===

    def test_window_functions(self, parser: SQLParser) -> None:
        """Test window functions."""
        sql = """
        SELECT
            id,
            ROW_NUMBER() OVER (ORDER BY id) AS rn,
            LAG(value) OVER (PARTITION BY category ORDER BY id) AS prev_value,
            SUM(value) OVER (ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
        FROM data
        """
        result = parser.parse(sql)
        assert result.is_readonly is True

    # === JSON 操作 ===

    def test_json_operators(self, parser: SQLParser) -> None:
        """Test PostgreSQL JSON operators."""
        sql = """
        SELECT
            data->>'name' AS name,
            data->'address'->>'city' AS city,
            data #>> '{nested,deep,value}' AS deep_value
        FROM json_table
        WHERE data @> '{"active": true}'
        """
        result = parser.parse(sql)
        assert result.is_readonly is True

    # === 数组操作 ===

    def test_array_operations(self, parser: SQLParser) -> None:
        """Test PostgreSQL array operations."""
        sql = """
        SELECT *
        FROM items
        WHERE tags && ARRAY['tag1', 'tag2']
        AND categories @> ARRAY['cat1']
        """
        result = parser.parse(sql)
        assert result.is_readonly is True

    # === 特殊表名 ===

    def test_reserved_word_table_name(self, parser: SQLParser) -> None:
        """Test table name that is a reserved word."""
        result = parser.parse('SELECT * FROM "order"')
        assert result.is_readonly is True

    def test_schema_qualified_name(self, parser: SQLParser) -> None:
        """Test schema-qualified table name."""
        result = parser.parse("SELECT * FROM public.users")
        assert result.is_readonly is True
        assert "public" in result.schemas

    def test_catalog_schema_table(self, parser: SQLParser) -> None:
        """Test catalog.schema.table format."""
        result = parser.parse("SELECT * FROM mydb.public.users")
        assert result.is_readonly is True
```

### 5.2 Access Policy 边缘场景

**文件**: `tests/unit/security/test_access_policy_edge_cases.py`

```python
"""Edge case tests for access policy."""

import pytest
from pg_mcp.config.models import (
    AccessPolicyConfig,
    TableAccessConfig,
    ColumnAccessConfig,
)
from pg_mcp.security.access_policy import DatabaseAccessPolicy
from pg_mcp.infrastructure.sql_parser import SQLParser, ParsedSQLInfo


class TestAccessPolicyEdgeCases:
    """Edge case tests for access policy."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    # === 空配置 ===

    def test_empty_config_allows_all(self, parser: SQLParser) -> None:
        """Test that empty config allows all access."""
        config = AccessPolicyConfig()
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("SELECT * FROM any_table")
        result = policy.validate_sql(parsed)
        assert result.passed is True

    # === 通配符模式 ===

    def test_wildcard_column_pattern(self, parser: SQLParser) -> None:
        """Test wildcard column patterns."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(
                denied_patterns=["*.*password*", "*.*secret*", "*.*token*"],
            ),
        )
        policy = DatabaseAccessPolicy(config)

        # Should block any password column
        parsed = ParsedSQLInfo(
            sql="SELECT user_password FROM users",
            schemas=["public"],
            tables=["users"],
            columns=[("users", "user_password")],
            has_select_star=False,
            select_star_tables=[],
            is_readonly=True,
        )
        result = policy.validate_sql(parsed)
        assert result.passed is False

    # === 大小写混合 ===

    def test_mixed_case_table_names(self, parser: SQLParser) -> None:
        """Test mixed case table names."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(denied=["users"]),
        )
        policy = DatabaseAccessPolicy(config)

        # Should block regardless of case
        for table_name in ["USERS", "Users", "uSeRs"]:
            parsed = ParsedSQLInfo(
                sql=f"SELECT * FROM {table_name}",
                schemas=["public"],
                tables=[table_name.lower()],  # Parser normalizes to lowercase
                columns=[],
                has_select_star=True,
                select_star_tables=[table_name.lower()],
                is_readonly=True,
            )
            result = policy.validate_sql(parsed)
            assert result.passed is False, f"Should block {table_name}"

    # === 多表 JOIN 场景 ===

    def test_join_with_one_denied_table(self, parser: SQLParser) -> None:
        """Test JOIN where one table is denied."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(denied=["secrets"]),
        )
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("""
            SELECT u.name, s.data
            FROM users u
            JOIN secrets s ON u.id = s.user_id
        """)
        result = policy.validate_sql(parsed)
        assert result.passed is False

    # === 子查询场景 ===

    def test_subquery_in_where(self, parser: SQLParser) -> None:
        """Test subquery in WHERE clause."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(denied=["admin_users"]),
        )
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("""
            SELECT * FROM users
            WHERE id IN (SELECT user_id FROM admin_users)
        """)
        result = policy.validate_sql(parsed)
        assert result.passed is False

    def test_subquery_in_from(self, parser: SQLParser) -> None:
        """Test subquery in FROM clause."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(denied=["secrets"]),
        )
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("""
            SELECT * FROM (SELECT * FROM secrets) AS sub
        """)
        result = policy.validate_sql(parsed)
        assert result.passed is False

    # === UNION 场景 ===

    def test_union_with_denied_table(self, parser: SQLParser) -> None:
        """Test UNION with one denied table."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(denied=["secrets"]),
        )
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("""
            SELECT name FROM users
            UNION
            SELECT data FROM secrets
        """)
        result = policy.validate_sql(parsed)
        assert result.passed is False

    # === 别名场景 ===

    def test_column_alias_does_not_bypass(self, parser: SQLParser) -> None:
        """Test that column alias doesn't bypass restrictions."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(denied=["users.password"]),
        )
        policy = DatabaseAccessPolicy(config)

        parsed = parser.parse("SELECT password AS pwd FROM users")
        result = policy.validate_sql(parsed)
        assert result.passed is False

    # === 函数包装场景 ===

    def test_function_wrapped_column(self, parser: SQLParser) -> None:
        """Test that function-wrapped columns are still checked."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(denied=["users.password"]),
        )
        policy = DatabaseAccessPolicy(config)

        # 函数包装的列也应该被检查
        parsed = parser.parse("SELECT UPPER(password) FROM users")
        result = policy.validate_sql(parsed)
        # 注意：这取决于 SQL parser 是否能解析函数参数中的列
        # 如果 parser 不支持，这个测试可能需要调整

    # === 冲突配置 ===

    def test_allowed_overrides_denied(self, parser: SQLParser) -> None:
        """Test that allowed list overrides denied list."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(
                allowed=["users"],
                denied=["users"],  # 同时出现在两个列表中
            ),
        )
        # 应该在配置验证时报错
        with pytest.raises(ValueError):
            config.validate_consistency()
```

### 5.3 Rate Limiter 边缘场景

**文件**: `tests/unit/resilience/test_rate_limiter_edge_cases.py`

```python
"""Edge case tests for rate limiter."""

import pytest
import asyncio
import time
from pg_mcp.resilience.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    # === 并发场景 ===

    async def test_concurrent_requests(self) -> None:
        """Test concurrent request handling."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
        )
        limiter = RateLimiter(config)

        # 并发发送 20 个请求
        async def make_request(i: int) -> bool:
            result = limiter.check_request(client_ip=f"192.168.1.{i % 10}")
            return result.allowed

        results = await asyncio.gather(*[make_request(i) for i in range(20)])

        # 应该有 10 个成功，10 个被限制
        assert sum(results) == 10

    # === 时间边界 ===

    def test_window_boundary_reset(self) -> None:
        """Test rate limit reset at window boundary."""
        config = RateLimitConfig(requests_per_minute=5)
        limiter = RateLimiter(config)

        # 用完配额
        for _ in range(5):
            result = limiter.check_request()
            assert result.allowed is True

        # 第 6 个应该被拒绝
        result = limiter.check_request()
        assert result.allowed is False

        # 重置后应该可以继续
        limiter.reset()
        result = limiter.check_request()
        assert result.allowed is True

    # === Token 消耗场景 ===

    def test_token_limit_exact_boundary(self) -> None:
        """Test token limit at exact boundary."""
        config = RateLimitConfig(
            requests_per_minute=100,
            openai_tokens_per_minute=1000,
        )
        limiter = RateLimiter(config)

        # 消耗恰好 1000 tokens
        limiter.record_tokens(1000)

        # 下一个请求应该被允许（刚好到边界）
        result = limiter.check_request()
        assert result.allowed is True

        # 再消耗 1 个 token 应该导致后续被限制
        limiter.record_tokens(1)
        # 检查 token 限制状态
        status = limiter.get_status()
        assert status["token_count"] > config.openai_tokens_per_minute

    # === 客户端隔离 ===

    def test_client_isolation(self) -> None:
        """Test that different clients are isolated."""
        config = RateLimitConfig(
            requests_per_minute=100,
            client_requests_per_minute=5,
        )
        limiter = RateLimiter(config)

        # Client A 用完配额
        for _ in range(5):
            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is True

        result = limiter.check_request(client_ip="192.168.1.1")
        assert result.allowed is False

        # Client B 应该不受影响
        result = limiter.check_request(client_ip="192.168.1.2")
        assert result.allowed is True

    # === 过期清理 ===

    def test_stale_bucket_cleanup(self) -> None:
        """Test cleanup of stale client buckets."""
        config = RateLimitConfig(
            client_requests_per_minute=5,
            bucket_expiry_seconds=1,  # 1 秒过期
        )
        limiter = RateLimiter(config)

        # 为多个客户端创建 bucket
        for i in range(100):
            limiter.check_request(client_ip=f"192.168.1.{i}")

        # 等待过期
        time.sleep(1.5)

        # 清理
        limiter.cleanup_stale_buckets()

        # 验证 bucket 已被清理
        status = limiter.get_status()
        assert status.get("active_clients", 0) == 0
```

### 5.4 Retry Executor 边缘场景

**文件**: `tests/unit/resilience/test_retry_executor_edge_cases.py`

```python
"""Edge case tests for retry executor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pg_mcp.resilience.retry_executor import (
    RetryExecutor,
    RetryConfig,
    OpenAIRetryExecutor,
    DatabaseRetryExecutor,
)
from pg_mcp.resilience.backoff import BackoffStrategyType


class TestRetryExecutorEdgeCases:
    """Edge case tests for retry executor."""

    # === 零重试 ===

    async def test_zero_retries(self) -> None:
        """Test with zero max retries."""
        config = RetryConfig(max_retries=0)
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=ValueError("error"))

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation)

        # 应该只调用一次
        assert operation.call_count == 1

    # === 立即成功 ===

    async def test_immediate_success(self) -> None:
        """Test operation that succeeds immediately."""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)

        operation = AsyncMock(return_value="success")

        result = await executor.execute_with_retry(operation)

        assert result == "success"
        assert operation.call_count == 1

    # === 最后一次重试成功 ===

    async def test_success_on_last_retry(self) -> None:
        """Test success on the last retry attempt."""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 4:  # 前 3 次失败
                raise ConnectionError("transient error")
            return "success"

        result = await executor.execute_with_retry(flaky_operation)

        assert result == "success"
        assert call_count == 4  # 1 初始 + 3 重试

    # === 不可重试错误 ===

    async def test_non_retryable_error_immediate_fail(self) -> None:
        """Test that non-retryable errors fail immediately."""
        config = RetryConfig(
            max_retries=3,
            retryable_errors=[ConnectionError],
        )
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=ValueError("not retryable"))

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation)

        # 不可重试的错误应该立即失败
        assert operation.call_count == 1

    # === 混合错误 ===

    async def test_mixed_errors(self) -> None:
        """Test handling of mixed retryable and non-retryable errors."""
        config = RetryConfig(
            max_retries=3,
            retryable_errors=[ConnectionError],
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("retryable")
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation)

        # 第一次 ConnectionError 后重试，第二次 ValueError 立即失败
        assert call_count == 2

    # === OpenAI 特定错误 ===

    async def test_openai_rate_limit_is_retryable(self) -> None:
        """Test that OpenAI RateLimitError is retryable."""
        executor = OpenAIRetryExecutor()

        # 模拟 RateLimitError
        class RateLimitError(Exception):
            pass

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("rate limited")
            return "success"

        # 需要 mock _is_default_retryable 方法
        result = await executor.execute_with_retry(operation)
        assert call_count >= 1

    # === 超时场景 ===

    async def test_operation_timeout(self) -> None:
        """Test operation that times out."""
        import asyncio

        config = RetryConfig(max_retries=2)
        executor = RetryExecutor(config)

        async def slow_operation():
            await asyncio.sleep(10)
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                executor.execute_with_retry(slow_operation),
                timeout=0.1
            )
```

---

## 6. 任务 E.5: 集成测试完善

**目标**: 使用 testcontainers 完善集成测试

**前置条件**: E.4 完成

### 6.1 Testcontainers 设置

**文件**: `tests/integration/conftest.py`

```python
"""Integration test fixtures with testcontainers."""

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for integration tests."""
    with PostgresContainer(
        image="postgres:16",
        username="test",
        password="test",
        dbname="testdb",
    ) as postgres:
        yield postgres


@pytest_asyncio.fixture
async def db_pool(postgres_container):
    """Create a database pool connected to the test container."""
    import asyncpg

    pool = await asyncpg.create_pool(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        user="test",
        password="test",
        database="testdb",
        min_size=1,
        max_size=5,
    )

    # 创建测试表
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100),
                password VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id),
                total DECIMAL(10,2),
                status VARCHAR(20)
            )
        """)
        # 插入测试数据
        await conn.execute("""
            INSERT INTO users (name, email, password) VALUES
            ('Alice', 'alice@example.com', 'secret1'),
            ('Bob', 'bob@example.com', 'secret2')
        """)

    yield pool

    await pool.close()
```

### 6.2 完整流程集成测试

**文件**: `tests/integration/test_full_flow.py`

```python
"""Full flow integration tests."""

import pytest
import pytest_asyncio
from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    OpenAISettings,
    AccessPolicyConfig,
    TableAccessConfig,
    ColumnAccessConfig,
)
from pg_mcp.services.query_executor import QueryExecutor, ExecutionContext
from pg_mcp.security.access_policy import DatabaseAccessPolicy
from pg_mcp.security.explain_validator import ExplainValidator
from pg_mcp.infrastructure.sql_parser import SQLParser


class TestFullFlow:
    """Full flow integration tests."""

    @pytest_asyncio.fixture
    async def executor(self, db_pool):
        """Create a QueryExecutor with real database."""
        config = AccessPolicyConfig(
            allowed_schemas=["public"],
            tables=TableAccessConfig(allowed=["users", "orders"]),
            columns=ColumnAccessConfig(denied=["users.password"]),
        )

        return QueryExecutor(
            pool=db_pool,
            sql_parser=SQLParser(),
            access_policy=DatabaseAccessPolicy(config),
            explain_validator=ExplainValidator(config.explain_policy),
            audit_logger=None,
        )

    async def test_query_success(self, executor) -> None:
        """Test successful query execution."""
        context = ExecutionContext(
            request_id="test-1",
            client_ip="127.0.0.1",
        )

        result = await executor.execute(
            sql="SELECT id, name, email FROM users",
            limit=100,
            context=context,
            question="List all users",
        )

        assert result.row_count == 2
        assert "Alice" in str(result.rows)

    async def test_query_with_password_denied(self, executor) -> None:
        """Test that password column is denied."""
        from pg_mcp.security.access_policy import ColumnAccessDeniedError

        context = ExecutionContext(request_id="test-2")

        with pytest.raises(ColumnAccessDeniedError):
            await executor.execute(
                sql="SELECT id, name, password FROM users",
                limit=100,
                context=context,
            )

    async def test_query_with_denied_table(self, executor) -> None:
        """Test that non-allowed table is denied."""
        from pg_mcp.security.access_policy import TableAccessDeniedError

        context = ExecutionContext(request_id="test-3")

        with pytest.raises(TableAccessDeniedError):
            await executor.execute(
                sql="SELECT * FROM admin_users",
                limit=100,
                context=context,
            )

    async def test_query_with_rate_limit(self, db_pool) -> None:
        """Test query with rate limiting."""
        from pg_mcp.resilience.rate_limiter import RateLimiter, RateLimitConfig

        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)

        # 前两个请求应该成功
        assert limiter.check_request().allowed is True
        assert limiter.check_request().allowed is True

        # 第三个应该被限制
        assert limiter.check_request().allowed is False
```

---

## 7. 验收标准

### 7.1 功能验收

| 任务 | 验收标准 |
|------|----------|
| E.1 | QueryService 正确使用 QueryExecutorManager |
| E.1 | 策略检查、EXPLAIN 验证、审计日志正常工作 |
| E.2 | `/metrics` 端点返回 Prometheus 格式指标 |
| E.3 | 空结果时 LLM 验证正常工作 |
| E.4 | 所有边缘场景测试通过 |
| E.5 | 集成测试在 testcontainers 中通过 |

### 7.2 测试覆盖目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| services/query_executor.py | 28% | >= 85% |
| observability/tracing.py | 84% | >= 85% |
| infrastructure/sql_parser.py | 93% | >= 95% |
| **总体** | 85% | >= 90% |

---

## 8. 执行计划

### 8.1 任务优先级

```
第一阶段（P0）:
├── E.1 QueryService 集成
└── E.4 边缘场景测试

第二阶段（P1）:
├── E.2 /metrics HTTP 端点
└── E.5 集成测试完善

第三阶段（P2）:
└── E.3 enable_result_validation
```

### 8.2 检查清单

- [ ] E.1 QueryService 集成完成
- [ ] E.2 /metrics 端点可访问
- [ ] E.3 结果验证功能实现
- [ ] E.4 边缘场景测试 > 50 个用例
- [ ] E.5 集成测试使用 testcontainers
- [ ] 总体测试覆盖率 >= 90%

---

## 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-15 | 初始版本 | Claude Code |
