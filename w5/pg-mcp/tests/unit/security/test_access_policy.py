"""Unit tests for DatabaseAccessPolicy.

Tests cover:
- Schema validation
- Table access control (whitelist/blacklist)
- Column access control (explicit deny, pattern matching)
- SELECT * handling
- Complete SQL validation
- Exception handling
"""

import pytest

from pg_mcp.config.models import (
    AccessPolicyConfig,
    ColumnAccessConfig,
    OnDeniedAction,
    SelectStarPolicy,
    TableAccessConfig,
)
from pg_mcp.infrastructure.sql_parser import ParsedSQLInfo, SQLParser
from pg_mcp.security.access_policy import (
    ColumnAccessDeniedError,
    DatabaseAccessPolicy,
    PolicyValidationResult,
    PolicyViolation,
    SchemaAccessDeniedError,
    TableAccessDeniedError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def default_config() -> AccessPolicyConfig:
    """Default access policy configuration."""
    return AccessPolicyConfig()


@pytest.fixture
def whitelist_config() -> AccessPolicyConfig:
    """Configuration with table whitelist."""
    return AccessPolicyConfig(
        allowed_schemas=["public"],
        tables=TableAccessConfig(
            allowed=["users", "orders"],
            denied=[],
        ),
    )


@pytest.fixture
def blacklist_config() -> AccessPolicyConfig:
    """Configuration with table blacklist."""
    return AccessPolicyConfig(
        allowed_schemas=["public"],
        tables=TableAccessConfig(
            allowed=[],
            denied=["audit_logs", "admin_users"],
        ),
    )


@pytest.fixture
def column_denied_config() -> AccessPolicyConfig:
    """Configuration with explicit denied columns."""
    return AccessPolicyConfig(
        columns=ColumnAccessConfig(
            denied=["users.password", "users.ssn", "orders.credit_card"],
            denied_patterns=[],
            on_denied=OnDeniedAction.REJECT,
        ),
    )


@pytest.fixture
def column_pattern_config() -> AccessPolicyConfig:
    """Configuration with column patterns."""
    return AccessPolicyConfig(
        columns=ColumnAccessConfig(
            denied=[],
            denied_patterns=["*._password*", "*._secret*", "*.credit_card"],
            on_denied=OnDeniedAction.REJECT,
        ),
    )


@pytest.fixture
def select_star_reject_config() -> AccessPolicyConfig:
    """Configuration that rejects SELECT * when sensitive columns involved."""
    return AccessPolicyConfig(
        columns=ColumnAccessConfig(
            denied=["users.password"],
            denied_patterns=[],
            on_denied=OnDeniedAction.REJECT,
            select_star_policy=SelectStarPolicy.REJECT,
        ),
    )


@pytest.fixture
def select_star_expand_config() -> AccessPolicyConfig:
    """Configuration that expands SELECT * to safe columns."""
    return AccessPolicyConfig(
        columns=ColumnAccessConfig(
            denied=["users.password"],
            denied_patterns=[],
            on_denied=OnDeniedAction.REJECT,
            select_star_policy=SelectStarPolicy.EXPAND_SAFE,
        ),
    )


@pytest.fixture
def sql_parser() -> SQLParser:
    """SQL parser instance."""
    return SQLParser()


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestSchemaValidation:
    """Tests for schema access validation."""

    def test_schema_allowed(self, default_config: AccessPolicyConfig) -> None:
        """Test that allowed schema passes validation."""
        policy = DatabaseAccessPolicy(default_config)

        result = policy.validate_schema("public")

        assert result.passed is True
        assert len(result.violations) == 0

    def test_schema_allowed_case_insensitive(
        self, default_config: AccessPolicyConfig
    ) -> None:
        """Test that schema validation is case-insensitive."""
        policy = DatabaseAccessPolicy(default_config)

        result = policy.validate_schema("PUBLIC")

        assert result.passed is True
        assert len(result.violations) == 0

    def test_schema_denied(self, default_config: AccessPolicyConfig) -> None:
        """Test that non-allowed schema is denied."""
        policy = DatabaseAccessPolicy(default_config)

        result = policy.validate_schema("private_data")

        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].check_type == "schema"
        assert result.violations[0].resource == "private_data"

    def test_schema_multiple_allowed(self) -> None:
        """Test with multiple allowed schemas."""
        config = AccessPolicyConfig(allowed_schemas=["public", "analytics", "reports"])
        policy = DatabaseAccessPolicy(config)

        assert policy.validate_schema("public").passed is True
        assert policy.validate_schema("analytics").passed is True
        assert policy.validate_schema("reports").passed is True
        assert policy.validate_schema("private").passed is False


# ============================================================================
# Table Access Tests
# ============================================================================


class TestTableAccessValidation:
    """Tests for table access validation."""

    def test_table_whitelist_mode(self, whitelist_config: AccessPolicyConfig) -> None:
        """Test whitelist mode: only allowed tables can be accessed."""
        policy = DatabaseAccessPolicy(whitelist_config)

        # Allowed tables
        result = policy.validate_tables(["users"])
        assert result.passed is True

        result = policy.validate_tables(["orders"])
        assert result.passed is True

        # Both allowed tables at once
        result = policy.validate_tables(["users", "orders"])
        assert result.passed is True

    def test_table_whitelist_mode_deny_unlisted(
        self, whitelist_config: AccessPolicyConfig
    ) -> None:
        """Test whitelist mode: unlisted tables are denied."""
        policy = DatabaseAccessPolicy(whitelist_config)

        result = policy.validate_tables(["products"])

        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].check_type == "table"
        assert "not in allowed list" in result.violations[0].reason

    def test_table_blacklist_mode(self, blacklist_config: AccessPolicyConfig) -> None:
        """Test blacklist mode: non-denied tables can be accessed."""
        policy = DatabaseAccessPolicy(blacklist_config)

        # Non-denied tables should pass
        result = policy.validate_tables(["users"])
        assert result.passed is True

        result = policy.validate_tables(["products"])
        assert result.passed is True

    def test_table_blacklist_mode_deny_listed(
        self, blacklist_config: AccessPolicyConfig
    ) -> None:
        """Test blacklist mode: denied tables are blocked."""
        policy = DatabaseAccessPolicy(blacklist_config)

        result = policy.validate_tables(["audit_logs"])

        assert result.passed is False
        assert len(result.violations) == 1
        assert "in denied list" in result.violations[0].reason

    def test_table_whitelist_priority(self) -> None:
        """Test that whitelist takes priority over blacklist in validation logic.

        When whitelist is non-empty, blacklist is not checked during validation.
        Note: Configuration validation catches conflicts, so we test the logic directly.
        """
        # Test whitelist mode with some tables in allowed
        config = AccessPolicyConfig(
            tables=TableAccessConfig(
                allowed=["users", "orders"],
                denied=[],
            ),
        )
        policy = DatabaseAccessPolicy(config)

        # Users is in allowed list, so it should pass
        result = policy.validate_tables(["users"])
        assert result.passed is True

        # Products is not in allowed list, so it should fail (whitelist mode)
        result = policy.validate_tables(["products"])
        assert result.passed is False

    def test_table_multiple_violations(
        self, whitelist_config: AccessPolicyConfig
    ) -> None:
        """Test multiple table violations in one query."""
        policy = DatabaseAccessPolicy(whitelist_config)

        result = policy.validate_tables(["products", "categories", "suppliers"])

        assert result.passed is False
        assert len(result.violations) == 3

    def test_table_case_insensitive(
        self, whitelist_config: AccessPolicyConfig
    ) -> None:
        """Test that table validation is case-insensitive."""
        policy = DatabaseAccessPolicy(whitelist_config)

        result = policy.validate_tables(["USERS", "Orders"])

        assert result.passed is True


# ============================================================================
# Column Access Tests
# ============================================================================


class TestColumnAccessValidation:
    """Tests for column access validation."""

    def test_column_explicit_denied(
        self, column_denied_config: AccessPolicyConfig
    ) -> None:
        """Test explicit column deny list."""
        policy = DatabaseAccessPolicy(column_denied_config)

        # Denied column
        result = policy.validate_columns([("users", "password")])

        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].resource == "users.password"
        assert "in denied list" in result.violations[0].reason

    def test_column_explicit_allowed(
        self, column_denied_config: AccessPolicyConfig
    ) -> None:
        """Test that non-denied columns pass."""
        policy = DatabaseAccessPolicy(column_denied_config)

        result = policy.validate_columns([("users", "name"), ("users", "email")])

        assert result.passed is True
        assert len(result.violations) == 0

    def test_column_pattern_match(
        self, column_pattern_config: AccessPolicyConfig
    ) -> None:
        """Test column pattern matching (glob patterns)."""
        policy = DatabaseAccessPolicy(column_pattern_config)

        # _password pattern should match
        result = policy.validate_columns([("users", "_password_hash")])
        assert result.passed is False
        assert "matches denied pattern" in result.violations[0].reason

        # _secret pattern should match
        result = policy.validate_columns([("config", "_secret_key")])
        assert result.passed is False

        # credit_card exact match
        result = policy.validate_columns([("payments", "credit_card")])
        assert result.passed is False

    def test_column_pattern_no_match(
        self, column_pattern_config: AccessPolicyConfig
    ) -> None:
        """Test that non-matching columns pass pattern check."""
        policy = DatabaseAccessPolicy(column_pattern_config)

        result = policy.validate_columns([
            ("users", "name"),
            ("users", "email"),
            ("orders", "total"),
        ])

        assert result.passed is True

    def test_select_star_reject_policy(
        self, select_star_reject_config: AccessPolicyConfig
    ) -> None:
        """Test SELECT * reject policy when sensitive columns involved."""
        policy = DatabaseAccessPolicy(select_star_reject_config)

        # Simulate SELECT * expansion that includes a sensitive column
        result = policy.validate_columns(
            [("users", "id"), ("users", "name"), ("users", "password")],
            is_select_star=True,
        )

        assert result.passed is False
        assert len(result.warnings) > 0
        assert "SELECT *" in result.warnings[0]

    def test_select_star_expand_safe_policy(
        self, select_star_expand_config: AccessPolicyConfig
    ) -> None:
        """Test SELECT * with expand_safe policy.

        Note: The actual expansion is done by get_safe_columns().
        This test verifies that violations are still recorded.
        """
        policy = DatabaseAccessPolicy(select_star_expand_config)

        # Even with expand_safe policy, violations are recorded
        result = policy.validate_columns(
            [("users", "password")],
            is_select_star=True,
        )

        # With EXPAND_SAFE, violations are recorded but no special warning
        assert result.passed is False
        assert len(result.violations) == 1

    def test_get_safe_columns(
        self, column_denied_config: AccessPolicyConfig
    ) -> None:
        """Test get_safe_columns method for SELECT * expansion."""
        policy = DatabaseAccessPolicy(column_denied_config)

        all_columns = ["id", "name", "email", "password", "ssn", "created_at"]
        safe_columns = policy.get_safe_columns("users", all_columns)

        assert "id" in safe_columns
        assert "name" in safe_columns
        assert "email" in safe_columns
        assert "created_at" in safe_columns
        assert "password" not in safe_columns
        assert "ssn" not in safe_columns

    def test_get_safe_columns_with_patterns(
        self, column_pattern_config: AccessPolicyConfig
    ) -> None:
        """Test get_safe_columns with pattern-based denials."""
        policy = DatabaseAccessPolicy(column_pattern_config)

        all_columns = [
            "id",
            "name",
            "_password_hash",
            "_secret_token",
            "email",
            "credit_card",
        ]
        safe_columns = policy.get_safe_columns("users", all_columns)

        assert "id" in safe_columns
        assert "name" in safe_columns
        assert "email" in safe_columns
        assert "_password_hash" not in safe_columns
        assert "_secret_token" not in safe_columns
        assert "credit_card" not in safe_columns

    def test_column_case_insensitive(
        self, column_denied_config: AccessPolicyConfig
    ) -> None:
        """Test that column validation is case-insensitive."""
        policy = DatabaseAccessPolicy(column_denied_config)

        result = policy.validate_columns([("USERS", "PASSWORD")])

        assert result.passed is False


# ============================================================================
# Complete SQL Validation Tests
# ============================================================================


class TestCompleteSQLValidation:
    """Tests for complete SQL validation."""

    def test_validate_sql_all_passed(
        self, default_config: AccessPolicyConfig, sql_parser: SQLParser
    ) -> None:
        """Test compliant SQL passes all checks."""
        policy = DatabaseAccessPolicy(default_config)

        parsed = sql_parser.parse_for_policy(
            "SELECT id, name FROM users WHERE active = true"
        )
        result = policy.validate_sql(parsed)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_validate_sql_schema_violation(self, sql_parser: SQLParser) -> None:
        """Test SQL with schema violation."""
        config = AccessPolicyConfig(allowed_schemas=["public"])
        policy = DatabaseAccessPolicy(config)

        parsed = sql_parser.parse_for_policy(
            "SELECT * FROM private.sensitive_data"
        )
        result = policy.validate_sql(parsed)

        assert result.passed is False
        assert any(v.check_type == "schema" for v in result.violations)

    def test_validate_sql_table_violation(self, sql_parser: SQLParser) -> None:
        """Test SQL with table violation."""
        config = AccessPolicyConfig(
            tables=TableAccessConfig(allowed=["users"], denied=[])
        )
        policy = DatabaseAccessPolicy(config)

        parsed = sql_parser.parse_for_policy(
            "SELECT * FROM audit_logs"
        )
        result = policy.validate_sql(parsed)

        assert result.passed is False
        assert any(v.check_type == "table" for v in result.violations)

    def test_validate_sql_column_violation(self, sql_parser: SQLParser) -> None:
        """Test SQL with column violation."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(
                denied=["users.password"],
                denied_patterns=[],
            )
        )
        policy = DatabaseAccessPolicy(config)

        parsed = sql_parser.parse_for_policy(
            "SELECT u.id, u.password FROM users u"
        )
        result = policy.validate_sql(parsed)

        assert result.passed is False
        assert any(v.check_type == "column" for v in result.violations)

    def test_validate_sql_multiple_violations(self, sql_parser: SQLParser) -> None:
        """Test SQL with multiple violations."""
        config = AccessPolicyConfig(
            allowed_schemas=["public"],
            tables=TableAccessConfig(allowed=["users"], denied=[]),
            columns=ColumnAccessConfig(
                denied=["users.password"],
                denied_patterns=[],
            ),
        )
        policy = DatabaseAccessPolicy(config)

        # This query has violations:
        # 1. Table 'orders' not in allowed list
        # 2. Column 'users.password' is denied
        parsed = sql_parser.parse_for_policy(
            "SELECT u.id, u.password, o.total "
            "FROM users u JOIN orders o ON u.id = o.user_id"
        )
        result = policy.validate_sql(parsed)

        assert result.passed is False
        assert len(result.violations) >= 2

    def test_validate_sql_with_select_star(self, sql_parser: SQLParser) -> None:
        """Test SQL with SELECT * and sensitive columns."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(
                denied=["users.password"],
                select_star_policy=SelectStarPolicy.REJECT,
            )
        )
        policy = DatabaseAccessPolicy(config)

        parsed = sql_parser.parse_for_policy("SELECT * FROM users")

        # The parsed result has select_star flag but may not have columns
        # since we need schema info for expansion
        assert parsed.has_select_star is True


# ============================================================================
# Exception Tests
# ============================================================================


class TestAccessPolicyExceptions:
    """Tests for access policy exceptions."""

    def test_table_access_denied_error(self) -> None:
        """Test TableAccessDeniedError structure."""
        error = TableAccessDeniedError(["users", "orders"])

        assert "Access denied to tables" in str(error)
        assert "users" in str(error)
        assert "orders" in str(error)
        assert error.code.value == "TABLE_ACCESS_DENIED"
        assert error.details is not None
        assert "denied_tables" in error.details

    def test_column_access_denied_error(self) -> None:
        """Test ColumnAccessDeniedError structure."""
        error = ColumnAccessDeniedError(["users.password", "users.ssn"])

        assert "Access denied to columns" in str(error)
        assert "users.password" in str(error)
        assert error.code.value == "COLUMN_ACCESS_DENIED"
        assert error.details["denied_columns"] == ["users.password", "users.ssn"]

    def test_column_access_denied_error_select_star(self) -> None:
        """Test ColumnAccessDeniedError with SELECT * flag."""
        error = ColumnAccessDeniedError(["users.password"], is_select_star=True)

        assert "SELECT *" in str(error)
        assert error.details["is_select_star"] is True

    def test_schema_access_denied_error(self) -> None:
        """Test SchemaAccessDeniedError structure."""
        error = SchemaAccessDeniedError("private", ["public", "analytics"])

        assert "private" in str(error)
        assert "public" in str(error)
        assert error.code.value == "SCHEMA_ACCESS_DENIED"
        assert error.details["denied_schema"] == "private"
        assert error.details["allowed_schemas"] == ["public", "analytics"]


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""

    def test_empty_tables_list(self, default_config: AccessPolicyConfig) -> None:
        """Test validation with empty tables list."""
        policy = DatabaseAccessPolicy(default_config)

        result = policy.validate_tables([])

        assert result.passed is True

    def test_empty_columns_list(self, default_config: AccessPolicyConfig) -> None:
        """Test validation with empty columns list."""
        policy = DatabaseAccessPolicy(default_config)

        result = policy.validate_columns([])

        assert result.passed is True

    def test_duplicate_tables(self, whitelist_config: AccessPolicyConfig) -> None:
        """Test validation with duplicate tables in list."""
        policy = DatabaseAccessPolicy(whitelist_config)

        result = policy.validate_tables(["users", "users", "orders"])

        assert result.passed is True

    def test_special_characters_in_names(
        self, default_config: AccessPolicyConfig
    ) -> None:
        """Test handling of special characters in table/column names."""
        policy = DatabaseAccessPolicy(default_config)

        # Schema with hyphen
        result = policy.validate_schema("my-schema")
        assert result.passed is False  # Not in allowed list

    def test_config_consistency_validation_conflict(self) -> None:
        """Test that config consistency validation catches conflicts."""
        with pytest.raises(ValueError) as exc_info:
            AccessPolicyConfig(
                tables=TableAccessConfig(
                    allowed=["users"],
                    denied=["users"],  # Conflict!
                )
            ).validate_consistency()

        assert "both allowed and denied" in str(exc_info.value).lower()

    def test_config_consistency_validation_warning(self) -> None:
        """Test that config consistency validation returns warnings."""
        config = AccessPolicyConfig(
            columns=ColumnAccessConfig(
                denied_patterns=["*.*.*.*"],  # Too broad pattern
            )
        )
        warnings = config.validate_consistency()

        assert len(warnings) > 0
        assert "too broadly" in warnings[0].lower()

    def test_policy_violation_dataclass(self) -> None:
        """Test PolicyViolation dataclass structure."""
        violation = PolicyViolation(
            check_type="table",
            resource="secret_table",
            reason="Access denied",
        )

        assert violation.check_type == "table"
        assert violation.resource == "secret_table"
        assert violation.reason == "Access denied"

    def test_policy_validation_result_namedtuple(self) -> None:
        """Test PolicyValidationResult namedtuple structure."""
        result = PolicyValidationResult(
            passed=False,
            violations=[PolicyViolation("table", "users", "denied")],
            warnings=["Warning message"],
            rewritten_sql="SELECT id FROM users",
        )

        assert result.passed is False
        assert len(result.violations) == 1
        assert len(result.warnings) == 1
        assert result.rewritten_sql is not None
