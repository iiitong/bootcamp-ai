"""Tests for SQL processor service."""

import pytest

from src.services.query import SQLProcessor


class TestSQLProcessor:
    """Tests for SQLProcessor class."""

    def test_select_query_passes(self) -> None:
        """SELECT queries should pass validation."""
        sql = "SELECT * FROM users"
        result = SQLProcessor.process(sql)
        assert "SELECT" in result.upper()

    def test_select_adds_limit(self) -> None:
        """SELECT without LIMIT should have LIMIT 1000 added."""
        sql = "SELECT * FROM users"
        result = SQLProcessor.process(sql)
        assert "LIMIT 1000" in result

    def test_select_with_existing_limit_preserved(self) -> None:
        """SELECT with existing LIMIT should preserve original LIMIT."""
        sql = "SELECT * FROM users LIMIT 10"
        result = SQLProcessor.process(sql)
        assert "LIMIT 10" in result
        assert "LIMIT 1000" not in result

    def test_select_with_custom_max_limit(self) -> None:
        """Custom max_limit should be applied."""
        sql = "SELECT * FROM users"
        result = SQLProcessor.process(sql, max_limit=500)
        assert "LIMIT 500" in result

    def test_insert_rejected(self) -> None:
        """INSERT statements should be rejected."""
        sql = "INSERT INTO users (name) VALUES ('test')"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_update_rejected(self) -> None:
        """UPDATE statements should be rejected."""
        sql = "UPDATE users SET name = 'test' WHERE id = 1"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_delete_rejected(self) -> None:
        """DELETE statements should be rejected."""
        sql = "DELETE FROM users WHERE id = 1"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_drop_rejected(self) -> None:
        """DROP statements should be rejected."""
        sql = "DROP TABLE users"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_truncate_rejected(self) -> None:
        """TRUNCATE statements should be rejected."""
        sql = "TRUNCATE TABLE users"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_create_rejected(self) -> None:
        """CREATE statements should be rejected."""
        sql = "CREATE TABLE test (id INT)"
        with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
            SQLProcessor.process(sql)

    def test_empty_query_rejected(self) -> None:
        """Empty queries should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SQLProcessor.process("")

        with pytest.raises(ValueError, match="cannot be empty"):
            SQLProcessor.process("   ")

    def test_syntax_error_detected(self) -> None:
        """SQL syntax errors should be detected."""
        sql = "SELECT * FRMO users"  # typo: FRMO instead of FROM
        with pytest.raises(ValueError, match="syntax error"):
            SQLProcessor.process(sql)

    def test_complex_select_query(self) -> None:
        """Complex SELECT queries should work."""
        sql = """
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.status = 'active'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        """
        result = SQLProcessor.process(sql)
        assert "SELECT" in result.upper()
        assert "LIMIT 1000" in result

    def test_subquery_select(self) -> None:
        """SELECT with subquery should work."""
        sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        result = SQLProcessor.process(sql)
        assert "SELECT" in result.upper()
        assert "LIMIT 1000" in result

    def test_union_query(self) -> None:
        """UNION queries should be allowed."""
        sql = "SELECT id FROM users UNION SELECT id FROM admins"
        result = SQLProcessor.process(sql)
        assert "UNION" in result.upper()

    def test_validate_only(self) -> None:
        """validate_only should return True for valid queries."""
        assert SQLProcessor.validate_only("SELECT * FROM users") is True

    def test_validate_only_raises_on_invalid(self) -> None:
        """validate_only should raise on invalid queries."""
        with pytest.raises(ValueError):
            SQLProcessor.validate_only("DELETE FROM users")
