"""Unit tests for ExplainValidator.

Tests cover:
- Cache hit/miss behavior
- Estimated rows/cost validation
- Sequential scan detection
- Error handling and graceful degradation
- Disabled policy handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.config.models import ExplainPolicyConfig
from pg_mcp.security.explain_validator import (
    ExplainResult,
    ExplainValidationResult,
    ExplainValidator,
    QueryTooExpensiveError,
    SeqScanDeniedError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def default_config() -> ExplainPolicyConfig:
    """Default EXPLAIN policy configuration."""
    return ExplainPolicyConfig(
        enabled=True,
        max_estimated_rows=100000,
        max_estimated_cost=10000.0,
        deny_seq_scan_on_large_tables=True,
        large_table_threshold=10000,
        timeout_seconds=5.0,
        cache_ttl_seconds=60,
        cache_max_size=1000,
    )


@pytest.fixture
def disabled_config() -> ExplainPolicyConfig:
    """Disabled EXPLAIN policy configuration."""
    return ExplainPolicyConfig(enabled=False)


@pytest.fixture
def strict_config() -> ExplainPolicyConfig:
    """Strict EXPLAIN policy configuration."""
    return ExplainPolicyConfig(
        enabled=True,
        max_estimated_rows=1000,
        max_estimated_cost=100.0,
        deny_seq_scan_on_large_tables=True,
        large_table_threshold=1000,  # Minimum allowed value
        timeout_seconds=2.0,
    )


@pytest.fixture
def mock_connection() -> MagicMock:
    """Mock database connection."""
    conn = MagicMock()
    conn.fetchval = AsyncMock()
    return conn


@pytest.fixture
def sample_explain_plan_simple() -> list[dict]:
    """Simple SELECT EXPLAIN output."""
    return [
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "users",
                "Plan Rows": 100,
                "Total Cost": 50.0,
                "Plans": [],
            }
        }
    ]


@pytest.fixture
def sample_explain_plan_index_scan() -> list[dict]:
    """Index scan EXPLAIN output."""
    return [
        {
            "Plan": {
                "Node Type": "Index Scan",
                "Index Name": "users_pkey",
                "Relation Name": "users",
                "Plan Rows": 1,
                "Total Cost": 8.5,
                "Plans": [],
            }
        }
    ]


@pytest.fixture
def sample_explain_plan_large_seq_scan() -> list[dict]:
    """Large table sequential scan EXPLAIN output."""
    return [
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "large_table",
                "Plan Rows": 50000,
                "Total Cost": 5000.0,
                "Plans": [],
            }
        }
    ]


@pytest.fixture
def sample_explain_plan_nested_loop() -> list[dict]:
    """Nested loop join EXPLAIN output."""
    return [
        {
            "Plan": {
                "Node Type": "Nested Loop",
                "Plan Rows": 10000,
                "Total Cost": 8000.0,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "users",
                        "Plan Rows": 100,
                        "Total Cost": 100.0,
                        "Plans": [],
                    },
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "orders",
                        "Plan Rows": 100,
                        "Total Cost": 500.0,
                        "Plans": [],
                    },
                ],
            }
        }
    ]


@pytest.fixture
def sample_explain_plan_expensive() -> list[dict]:
    """Expensive query EXPLAIN output (exceeds cost limit)."""
    return [
        {
            "Plan": {
                "Node Type": "Hash Join",
                "Plan Rows": 500000,
                "Total Cost": 50000.0,
                "Plans": [],
            }
        }
    ]


# ============================================================================
# Cache Tests
# ============================================================================


class TestExplainValidatorCache:
    """Tests for EXPLAIN result caching."""

    @pytest.mark.asyncio
    async def test_cache_hit(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_simple: list[dict],
    ) -> None:
        """Test that cached results are returned on cache hit."""
        validator = ExplainValidator(default_config)

        # First call - should execute EXPLAIN
        mock_connection.fetchval.return_value = sample_explain_plan_simple
        result1 = await validator.validate(mock_connection, "SELECT * FROM users")

        assert result1.passed is True
        assert mock_connection.fetchval.call_count == 1

        # Second call with same SQL - should use cache
        result2 = await validator.validate(mock_connection, "SELECT * FROM users")

        assert result2.passed is True
        # fetchval should not be called again
        assert mock_connection.fetchval.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_simple: list[dict],
    ) -> None:
        """Test that different queries result in cache misses."""
        validator = ExplainValidator(default_config)
        mock_connection.fetchval.return_value = sample_explain_plan_simple

        # First query
        await validator.validate(mock_connection, "SELECT * FROM users")
        assert mock_connection.fetchval.call_count == 1

        # Different query - should be cache miss
        await validator.validate(mock_connection, "SELECT * FROM orders")
        assert mock_connection.fetchval.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_key_generation(
        self, default_config: ExplainPolicyConfig
    ) -> None:
        """Test cache key generation uses SQL hash."""
        validator = ExplainValidator(default_config)

        key1 = validator._get_cache_key("SELECT * FROM users")
        key2 = validator._get_cache_key("SELECT * FROM orders")
        key3 = validator._get_cache_key("SELECT * FROM users")

        # Same SQL should produce same key
        assert key1 == key3
        # Different SQL should produce different key
        assert key1 != key2
        # Key should be 16 characters (SHA256 prefix)
        assert len(key1) == 16


# ============================================================================
# Policy Validation Tests
# ============================================================================


class TestExplainValidatorPolicy:
    """Tests for EXPLAIN policy validation."""

    @pytest.mark.asyncio
    async def test_estimated_rows_exceed_limit(
        self,
        strict_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_expensive: list[dict],
    ) -> None:
        """Test that queries exceeding row limit are rejected."""
        validator = ExplainValidator(strict_config)
        mock_connection.fetchval.return_value = sample_explain_plan_expensive

        result = await validator.validate(
            mock_connection, "SELECT * FROM huge_table"
        )

        assert result.passed is False
        assert result.error_message is not None
        assert "exceeds limit" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_estimated_cost_warning(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
    ) -> None:
        """Test that queries exceeding cost limit produce warning (not rejection)."""
        validator = ExplainValidator(default_config)

        # Create a plan that exceeds cost but not row limit
        expensive_plan = [
            {
                "Plan": {
                    "Node Type": "Index Scan",
                    "Relation Name": "users",
                    "Plan Rows": 1000,  # Under row limit
                    "Total Cost": 50000.0,  # Over cost limit
                    "Plans": [],
                }
            }
        ]
        mock_connection.fetchval.return_value = expensive_plan

        result = await validator.validate(mock_connection, "SELECT * FROM users")

        # Should pass but with warning
        assert result.passed is True
        assert result.warnings is not None
        assert len(result.warnings) > 0
        assert "cost" in result.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_seq_scan_on_large_table_denied(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_large_seq_scan: list[dict],
    ) -> None:
        """Test that sequential scan on large table is denied."""
        # Provide table row count that exceeds threshold
        validator = ExplainValidator(
            default_config,
            table_row_counts={"large_table": 50000},
        )
        mock_connection.fetchval.return_value = sample_explain_plan_large_seq_scan

        result = await validator.validate(
            mock_connection, "SELECT * FROM large_table"
        )

        assert result.passed is False
        assert result.error_message is not None
        assert "sequential scan" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_seq_scan_on_small_table_allowed(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_simple: list[dict],
    ) -> None:
        """Test that sequential scan on small table is allowed."""
        validator = ExplainValidator(
            default_config,
            table_row_counts={"users": 100},  # Small table
        )
        mock_connection.fetchval.return_value = sample_explain_plan_simple

        result = await validator.validate(mock_connection, "SELECT * FROM users")

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_seq_scan_uses_plan_rows_when_no_row_count(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_large_seq_scan: list[dict],
    ) -> None:
        """Test that EXPLAIN plan rows are used when no table row count provided."""
        # No table_row_counts provided, should use Plan Rows from EXPLAIN
        validator = ExplainValidator(default_config)
        mock_connection.fetchval.return_value = sample_explain_plan_large_seq_scan

        result = await validator.validate(
            mock_connection, "SELECT * FROM large_table"
        )

        # Plan Rows is 50000, which exceeds large_table_threshold of 10000
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_nested_seq_scan_detected(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_nested_loop: list[dict],
    ) -> None:
        """Test that nested sequential scans are detected."""
        validator = ExplainValidator(
            default_config,
            table_row_counts={"orders": 50000},  # Large table
        )
        mock_connection.fetchval.return_value = sample_explain_plan_nested_loop

        result = await validator.validate(
            mock_connection,
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        )

        # Should fail because of seq scan on large 'orders' table
        assert result.passed is False


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestExplainValidatorErrorHandling:
    """Tests for error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_explain_timeout(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
    ) -> None:
        """Test EXPLAIN timeout is handled gracefully."""
        import asyncio

        validator = ExplainValidator(default_config)
        mock_connection.fetchval.side_effect = asyncio.TimeoutError("EXPLAIN timeout")

        result = await validator.validate(mock_connection, "SELECT * FROM users")

        # Should pass with warning (graceful degradation)
        assert result.passed is True
        assert result.warnings is not None
        assert any("failed" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_explain_failure_graceful(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
    ) -> None:
        """Test EXPLAIN failure results in graceful degradation."""
        validator = ExplainValidator(default_config)
        mock_connection.fetchval.side_effect = Exception("Database error")

        result = await validator.validate(mock_connection, "SELECT * FROM users")

        # Should pass with warning (don't block query on EXPLAIN failure)
        assert result.passed is True
        assert result.result is None
        assert result.warnings is not None

    @pytest.mark.asyncio
    async def test_disabled_policy(
        self,
        disabled_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
    ) -> None:
        """Test that disabled policy skips EXPLAIN entirely."""
        validator = ExplainValidator(disabled_config)

        result = await validator.validate(
            mock_connection, "SELECT * FROM huge_table WHERE 1=1"
        )

        # Should pass without any EXPLAIN execution
        assert result.passed is True
        assert result.result is None
        # Connection should not be called
        mock_connection.fetchval.assert_not_called()


# ============================================================================
# ExplainResult Parsing Tests
# ============================================================================


class TestExplainResultParsing:
    """Tests for EXPLAIN result parsing."""

    def test_parse_simple_plan(
        self,
        default_config: ExplainPolicyConfig,
        sample_explain_plan_simple: list[dict],
    ) -> None:
        """Test parsing of simple EXPLAIN plan."""
        validator = ExplainValidator(default_config)

        result = validator._parse_explain(sample_explain_plan_simple)

        assert result.total_cost == 50.0
        assert result.estimated_rows == 100
        assert result.has_seq_scan is True
        assert len(result.seq_scan_tables) == 1
        assert result.seq_scan_tables[0] == ("users", 100)

    def test_parse_index_scan_plan(
        self,
        default_config: ExplainPolicyConfig,
        sample_explain_plan_index_scan: list[dict],
    ) -> None:
        """Test parsing of index scan EXPLAIN plan."""
        validator = ExplainValidator(default_config)

        result = validator._parse_explain(sample_explain_plan_index_scan)

        assert result.total_cost == 8.5
        assert result.estimated_rows == 1
        assert result.has_seq_scan is False
        assert len(result.seq_scan_tables) == 0

    def test_parse_nested_plan(
        self,
        default_config: ExplainPolicyConfig,
        sample_explain_plan_nested_loop: list[dict],
    ) -> None:
        """Test parsing of nested EXPLAIN plan with multiple nodes."""
        validator = ExplainValidator(default_config)

        result = validator._parse_explain(sample_explain_plan_nested_loop)

        # Should find the seq scan in nested plan
        assert result.has_seq_scan is True
        assert len(result.seq_scan_tables) == 1
        assert result.seq_scan_tables[0][0] == "orders"

        # Plan nodes should include all nodes
        assert len(result.plan_nodes) == 3  # Root + 2 children


# ============================================================================
# Table Row Count Update Tests
# ============================================================================


class TestTableRowCountUpdate:
    """Tests for table row count update functionality."""

    def test_update_table_row_counts(
        self, default_config: ExplainPolicyConfig
    ) -> None:
        """Test updating table row counts."""
        validator = ExplainValidator(default_config)

        # Initially empty
        assert validator.table_row_counts == {}

        # Update counts
        new_counts = {"users": 1000, "orders": 50000, "products": 5000}
        validator.update_table_row_counts(new_counts)

        assert validator.table_row_counts == new_counts

    def test_update_table_row_counts_replaces_existing(
        self, default_config: ExplainPolicyConfig
    ) -> None:
        """Test that update_table_row_counts replaces existing counts."""
        validator = ExplainValidator(
            default_config,
            table_row_counts={"users": 100},
        )

        validator.update_table_row_counts({"orders": 5000})

        # Should replace, not merge
        assert "users" not in validator.table_row_counts
        assert validator.table_row_counts["orders"] == 5000


# ============================================================================
# Exception Tests
# ============================================================================


class TestExplainValidatorExceptions:
    """Tests for exception classes."""

    def test_query_too_expensive_error(self) -> None:
        """Test QueryTooExpensiveError structure."""
        error = QueryTooExpensiveError(
            estimated_rows=500000,
            estimated_cost=50000.0,
            limits={"max_rows": 100000, "max_cost": 10000.0},
        )

        assert "exceeds resource limits" in str(error).lower()
        assert "500000" in str(error)
        assert error.code.value == "QUERY_TOO_EXPENSIVE"
        assert error.details["estimated_rows"] == 500000
        assert error.details["estimated_cost"] == 50000.0

    def test_seq_scan_denied_error(self) -> None:
        """Test SeqScanDeniedError structure."""
        error = SeqScanDeniedError(table="large_table", estimated_rows=100000)

        assert "sequential scan" in str(error).lower()
        assert "large_table" in str(error)
        assert error.code.value == "SEQ_SCAN_DENIED"
        assert error.details["table"] == "large_table"
        assert error.details["estimated_rows"] == 100000


# ============================================================================
# ExplainResult and ExplainValidationResult Tests
# ============================================================================


class TestExplainResultDataclasses:
    """Tests for ExplainResult and ExplainValidationResult dataclasses."""

    def test_explain_result_structure(self) -> None:
        """Test ExplainResult dataclass structure."""
        result = ExplainResult(
            total_cost=100.0,
            estimated_rows=1000,
            plan_nodes=[{"Node Type": "Seq Scan"}],
            has_seq_scan=True,
            seq_scan_tables=[("users", 1000)],
            raw_plan={"Node Type": "Seq Scan"},
        )

        assert result.total_cost == 100.0
        assert result.estimated_rows == 1000
        assert len(result.plan_nodes) == 1
        assert result.has_seq_scan is True
        assert result.seq_scan_tables == [("users", 1000)]

    def test_explain_validation_result_structure(self) -> None:
        """Test ExplainValidationResult dataclass structure."""
        explain_result = ExplainResult(
            total_cost=100.0,
            estimated_rows=1000,
            plan_nodes=[],
            has_seq_scan=False,
            seq_scan_tables=[],
        )

        validation_result = ExplainValidationResult(
            passed=True,
            result=explain_result,
            error_message=None,
            warnings=["Minor warning"],
        )

        assert validation_result.passed is True
        assert validation_result.result is not None
        assert validation_result.error_message is None
        assert validation_result.warnings == ["Minor warning"]

    def test_explain_validation_result_failed(self) -> None:
        """Test ExplainValidationResult for failed validation."""
        validation_result = ExplainValidationResult(
            passed=False,
            result=None,
            error_message="Query too expensive",
            warnings=None,
        )

        assert validation_result.passed is False
        assert validation_result.error_message == "Query too expensive"


# ============================================================================
# Integration-like Tests
# ============================================================================


class TestExplainValidatorIntegration:
    """Integration-like tests for ExplainValidator."""

    @pytest.mark.asyncio
    async def test_full_validation_flow_pass(
        self,
        default_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_index_scan: list[dict],
    ) -> None:
        """Test complete validation flow for a passing query."""
        validator = ExplainValidator(default_config)
        mock_connection.fetchval.return_value = sample_explain_plan_index_scan

        result = await validator.validate(
            mock_connection,
            "SELECT id, name FROM users WHERE id = 1"
        )

        assert result.passed is True
        assert result.result is not None
        assert result.result.has_seq_scan is False
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_full_validation_flow_reject(
        self,
        strict_config: ExplainPolicyConfig,
        mock_connection: MagicMock,
        sample_explain_plan_expensive: list[dict],
    ) -> None:
        """Test complete validation flow for a rejected query."""
        validator = ExplainValidator(strict_config)
        mock_connection.fetchval.return_value = sample_explain_plan_expensive

        result = await validator.validate(
            mock_connection,
            "SELECT * FROM huge_table CROSS JOIN another_huge_table"
        )

        assert result.passed is False
        assert result.error_message is not None
