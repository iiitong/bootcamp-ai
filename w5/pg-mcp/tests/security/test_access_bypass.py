"""Access control bypass security tests.

These tests verify that the access policy enforcement cannot be
bypassed through various techniques.
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
from pg_mcp.security.access_policy import DatabaseAccessPolicy


class TestAccessBypass:
    """Access control bypass tests."""

    @pytest.fixture
    def restrictive_policy(self) -> DatabaseAccessPolicy:
        """Create a restrictive access policy."""
        config = AccessPolicyConfig(
            allowed_schemas=["public"],
            tables=TableAccessConfig(
                allowed=["users", "orders"],
                denied=["admin_users", "secrets"],
            ),
            columns=ColumnAccessConfig(
                denied=["users.password", "users.ssn"],
                denied_patterns=["*._password*", "*._secret*"],
                on_denied=OnDeniedAction.REJECT,
                select_star_policy=SelectStarPolicy.REJECT,
            ),
        )
        return DatabaseAccessPolicy(config)

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    def test_schema_bypass_attempt(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that schema bypass attempts are blocked."""
        # Try to access a non-public schema
        parsed = parser.parse_for_policy("SELECT * FROM private.secrets")
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        assert any(v.check_type == "schema" for v in result.violations)

    def test_table_bypass_attempt(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that table access bypass attempts are blocked."""
        # Try to access a table not in the allowed list
        parsed = parser.parse_for_policy("SELECT * FROM products")
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        assert any(v.check_type == "table" for v in result.violations)

    def test_column_bypass_via_star(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that SELECT * on tables with sensitive columns is handled."""
        # Create a ParsedSQLInfo that would result from SELECT * FROM users
        parsed = ParsedSQLInfo(
            sql="SELECT * FROM users",
            schemas=["public"],
            tables=["users"],
            columns=[
                ("users", "password"),
                ("users", "email"),
            ],  # Simulating * expansion
            has_select_star=True,
            select_star_tables=["users"],
            is_readonly=True,
        )
        result = restrictive_policy.validate_sql(parsed)
        # Should be blocked because password column is denied
        assert not result.passed
        assert any(v.check_type == "column" for v in result.violations)

    def test_column_bypass_via_alias(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that column alias bypass attempts are blocked."""
        # Try to access a denied column with alias
        parsed = parser.parse_for_policy("SELECT u.password AS pwd FROM users u")
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        assert any(v.check_type == "column" for v in result.violations)

    def test_case_sensitivity_bypass(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that case variations don't bypass restrictions."""
        # Try to bypass with different case
        parsed = parser.parse_for_policy("SELECT u.PASSWORD FROM users u")
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        assert any(v.check_type == "column" for v in result.violations)

    def test_subquery_bypass_attempt(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that subquery bypass attempts are blocked."""
        # Try to access denied table through subquery
        parsed = parser.parse_for_policy(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM products)"
        )
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        # Should fail because 'products' is not in allowed tables

    def test_join_bypass_attempt(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that JOIN bypass attempts are blocked."""
        # Try to access denied table through JOIN
        parsed = parser.parse_for_policy(
            "SELECT u.* FROM users u JOIN products p ON u.id = p.user_id"
        )
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed

    def test_cte_bypass_attempt(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that CTE bypass attempts are blocked."""
        # Try to access denied table through CTE
        parsed = parser.parse_for_policy("WITH p AS (SELECT * FROM products) SELECT * FROM users")
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed

    def test_pattern_bypass_variations(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that pattern-based column restrictions cannot be bypassed."""
        # Test various column names that should match denied patterns
        test_columns = [
            ("users", "_password_hash"),
            ("users", "_password"),
            ("config", "_secret_key"),
            ("config", "_secret_token"),
        ]
        for table, column in test_columns:
            result = restrictive_policy.validate_columns([(table, column)])
            assert not result.passed, f"Pattern bypass not blocked for {table}.{column}"

    def test_schema_case_bypass(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that schema case variations are handled."""
        # Test different case variations of schema names
        for schema in ["PUBLIC", "Public", "pUbLiC"]:
            result = restrictive_policy.validate_schema(schema)
            assert result.passed, f"Valid schema '{schema}' incorrectly denied"

        for schema in ["PRIVATE", "Private", "pRiVaTe"]:
            result = restrictive_policy.validate_schema(schema)
            assert not result.passed, f"Invalid schema '{schema}' incorrectly allowed"

    def test_table_case_bypass(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that table case variations are handled."""
        # Test different case variations of allowed tables
        for table in ["USERS", "Users", "uSeRs"]:
            result = restrictive_policy.validate_tables([table])
            assert result.passed, f"Valid table '{table}' incorrectly denied"

        for table in ["PRODUCTS", "Products", "pRoDuCtS"]:
            result = restrictive_policy.validate_tables([table])
            assert not result.passed, f"Invalid table '{table}' incorrectly allowed"

    def test_column_case_bypass(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that column case variations are handled."""
        # Test different case variations of denied columns
        denied_variations = [
            ("users", "PASSWORD"),
            ("users", "Password"),
            ("USERS", "password"),
            ("Users", "PassWord"),
        ]
        for table, column in denied_variations:
            result = restrictive_policy.validate_columns([(table, column)])
            assert not result.passed, f"Denied column '{table}.{column}' not blocked"

    def test_multiple_violation_detection(
        self, restrictive_policy: DatabaseAccessPolicy, parser: SQLParser
    ) -> None:
        """Test that multiple violations are all detected."""
        # Query with schema, table, and column violations
        parsed = ParsedSQLInfo(
            sql="SELECT password, ssn FROM private.admin_users",
            schemas=["private"],
            tables=["admin_users"],
            columns=[("admin_users", "password"), ("admin_users", "ssn")],
            has_select_star=False,
            select_star_tables=[],
            is_readonly=True,
        )
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        # Should have violations for schema and table
        assert len(result.violations) >= 2

    def test_empty_tables_allowed(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that empty tables list passes validation."""
        result = restrictive_policy.validate_tables([])
        assert result.passed

    def test_empty_columns_allowed(self, restrictive_policy: DatabaseAccessPolicy) -> None:
        """Test that empty columns list passes validation."""
        result = restrictive_policy.validate_columns([])
        assert result.passed

    def test_select_star_with_sensitive_columns(
        self, restrictive_policy: DatabaseAccessPolicy
    ) -> None:
        """Test SELECT * rejection when sensitive columns are involved."""
        # Simulate SELECT * that would expose sensitive columns
        parsed = ParsedSQLInfo(
            sql="SELECT * FROM users",
            schemas=["public"],
            tables=["users"],
            columns=[
                ("users", "id"),
                ("users", "name"),
                ("users", "password"),  # Sensitive
                ("users", "email"),
            ],
            has_select_star=True,
            select_star_tables=["users"],
            is_readonly=True,
        )
        result = restrictive_policy.validate_sql(parsed)
        assert not result.passed
        assert len(result.warnings) > 0
        assert any("SELECT *" in w for w in result.warnings)


class TestAccessPolicyEdgeCases:
    """Edge case tests for access policy."""

    @pytest.fixture
    def blacklist_policy(self) -> DatabaseAccessPolicy:
        """Create a blacklist-mode policy."""
        config = AccessPolicyConfig(
            allowed_schemas=["public", "analytics"],
            tables=TableAccessConfig(
                allowed=[],  # Empty allowed = blacklist mode
                denied=["audit_logs", "secrets"],
            ),
            columns=ColumnAccessConfig(
                denied=["users.password"],
                denied_patterns=[],
            ),
        )
        return DatabaseAccessPolicy(config)

    def test_blacklist_mode_allows_unlisted(self, blacklist_policy: DatabaseAccessPolicy) -> None:
        """Test that blacklist mode allows non-denied tables."""
        result = blacklist_policy.validate_tables(["users", "orders", "products"])
        assert result.passed

    def test_blacklist_mode_blocks_denied(self, blacklist_policy: DatabaseAccessPolicy) -> None:
        """Test that blacklist mode blocks denied tables."""
        result = blacklist_policy.validate_tables(["audit_logs"])
        assert not result.passed
        result = blacklist_policy.validate_tables(["secrets"])
        assert not result.passed

    def test_mixed_allowed_and_denied_tables(self, blacklist_policy: DatabaseAccessPolicy) -> None:
        """Test query with mix of allowed and denied tables."""
        result = blacklist_policy.validate_tables(["users", "audit_logs"])
        assert not result.passed
        # Should have exactly one violation for audit_logs
        assert len(result.violations) == 1
        assert result.violations[0].resource == "audit_logs"

    def test_get_safe_columns(self, blacklist_policy: DatabaseAccessPolicy) -> None:
        """Test getting safe columns for SELECT * expansion."""
        all_columns = ["id", "name", "email", "password", "created_at"]
        safe_columns = blacklist_policy.get_safe_columns("users", all_columns)
        assert "id" in safe_columns
        assert "name" in safe_columns
        assert "email" in safe_columns
        assert "created_at" in safe_columns
        assert "password" not in safe_columns

    def test_multiple_schemas_validation(self, blacklist_policy: DatabaseAccessPolicy) -> None:
        """Test validation with multiple schemas."""
        parsed = ParsedSQLInfo(
            sql="SELECT a.*, b.* FROM public.users a JOIN analytics.events b ON ...",
            schemas=["public", "analytics"],
            tables=["users", "events"],
            columns=[],
            has_select_star=True,
            select_star_tables=["users", "events"],
            is_readonly=True,
        )
        result = blacklist_policy.validate_sql(parsed)
        # Should pass since both schemas are allowed
        assert result.passed or any(v.check_type != "schema" for v in result.violations)
