# src/pg_mcp/security/explain_validator.py

"""EXPLAIN 策略验证器

本模块提供基于 EXPLAIN 的查询计划分析和验证功能：
- 执行 EXPLAIN (FORMAT JSON) 获取查询计划
- 分析估算行数、成本、全表扫描
- 缓存相同 SQL 的 EXPLAIN 结果
"""

import hashlib
from dataclasses import dataclass, field

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
        limits: dict,
    ):
        super().__init__(
            ErrorCode.QUERY_TOO_EXPENSIVE,
            f"Query exceeds resource limits. "
            f"Estimated rows: {estimated_rows}, cost: {estimated_cost:.2f}",
            {"estimated_rows": estimated_rows, "estimated_cost": estimated_cost, **limits},
        )


class SeqScanDeniedError(PgMcpError):
    """全表扫描被拒绝"""

    def __init__(self, table: str, estimated_rows: int):
        super().__init__(
            ErrorCode.SEQ_SCAN_DENIED,
            f"Sequential scan on large table '{table}' denied. Estimated rows: {estimated_rows}",
            {"table": table, "estimated_rows": estimated_rows},
        )


@dataclass
class ExplainResult:
    """EXPLAIN 分析结果"""

    total_cost: float
    estimated_rows: int
    plan_nodes: list[dict]
    has_seq_scan: bool
    seq_scan_tables: list[tuple[str, int]]  # [(table, rows), ...]
    raw_plan: dict = field(default_factory=dict)


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
        table_row_counts: dict[str, int] | None = None,
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
            ttl=config.cache_ttl_seconds,
        )

    def _get_cache_key(self, sql: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(sql.encode()).hexdigest()[:16]

    async def validate(
        self,
        conn: Connection,
        sql: str,
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
                timeout=self.config.timeout_seconds,
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
                warnings=[f"EXPLAIN failed: {str(e)}"],
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
        nodes: list[dict] = []
        seq_scan_tables: list[tuple[str, int]] = []

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
            raw_plan=plan,
        )

    def _validate_result(self, result: ExplainResult) -> ExplainValidationResult:
        """
        根据策略验证 EXPLAIN 结果

        Args:
            result: EXPLAIN 分析结果

        Returns:
            ExplainValidationResult
        """
        warnings: list[str] = []

        # 检查估算行数
        if result.estimated_rows > self.config.max_estimated_rows:
            return ExplainValidationResult(
                passed=False,
                result=result,
                error_message=(
                    f"Estimated rows ({result.estimated_rows}) exceeds limit "
                    f"({self.config.max_estimated_rows})"
                ),
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
                            f"Sequential scan on large table '{table}' (~{actual_rows} rows) denied"
                        ),
                    )

        return ExplainValidationResult(
            passed=True,
            result=result,
            warnings=warnings if warnings else None,
        )

    def update_table_row_counts(self, counts: dict[str, int]) -> None:
        """更新表行数估算（从 Schema 缓存刷新时调用）"""
        self.table_row_counts = counts
