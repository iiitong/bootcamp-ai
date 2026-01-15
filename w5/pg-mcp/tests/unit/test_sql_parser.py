"""Unit tests for SQL parser and validation."""

import pytest

from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import SQLSyntaxError, UnsafeSQLError


class TestSQLParserValidation:
    """Tests for SQL validation."""

    def test_valid_select(self, sql_parser: SQLParser) -> None:
        """Test that valid SELECT queries pass validation."""
        queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT COUNT(*) FROM users",
            "SELECT name, COUNT(*) FROM users GROUP BY name HAVING COUNT(*) > 1",
            "SELECT * FROM users ORDER BY created_at DESC LIMIT 10",
            (
                "WITH active_users AS (SELECT * FROM users WHERE active = true) "
                "SELECT * FROM active_users"
            ),
        ]
        for query in queries:
            result = sql_parser.validate(query)
            assert result.is_valid, f"Query should be valid: {query}"
            assert result.is_safe, f"Query should be safe: {query}"

    def test_reject_insert(self, sql_parser: SQLParser) -> None:
        """Test that INSERT statements are rejected."""
        result = sql_parser.validate("INSERT INTO users (name) VALUES ('test')")
        assert result.is_valid
        assert not result.is_safe
        assert "not allowed" in result.error_message.lower()

    def test_reject_update(self, sql_parser: SQLParser) -> None:
        """Test that UPDATE statements are rejected."""
        result = sql_parser.validate("UPDATE users SET name = 'test' WHERE id = 1")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_delete(self, sql_parser: SQLParser) -> None:
        """Test that DELETE statements are rejected."""
        result = sql_parser.validate("DELETE FROM users WHERE id = 1")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_drop(self, sql_parser: SQLParser) -> None:
        """Test that DROP statements are rejected."""
        result = sql_parser.validate("DROP TABLE users")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_truncate(self, sql_parser: SQLParser) -> None:
        """Test that TRUNCATE statements are rejected."""
        result = sql_parser.validate("TRUNCATE TABLE users")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_create(self, sql_parser: SQLParser) -> None:
        """Test that CREATE statements are rejected."""
        result = sql_parser.validate("CREATE TABLE test (id INT)")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_alter(self, sql_parser: SQLParser) -> None:
        """Test that ALTER statements are rejected."""
        result = sql_parser.validate("ALTER TABLE users ADD COLUMN age INT")
        assert result.is_valid
        assert not result.is_safe

    def test_reject_stacked_queries(self, sql_parser: SQLParser) -> None:
        """Test that multiple statements (stacked queries) are rejected."""
        result = sql_parser.validate("SELECT * FROM users; DROP TABLE users")
        assert not result.is_safe
        assert "multiple statements" in result.error_message.lower()

    def test_reject_pg_sleep(self, sql_parser: SQLParser) -> None:
        """Test that pg_sleep function is rejected."""
        result = sql_parser.validate("SELECT pg_sleep(10)")
        assert not result.is_safe
        assert "pg_sleep" in result.error_message.lower()

    def test_reject_dblink(self, sql_parser: SQLParser) -> None:
        """Test that dblink function is rejected."""
        result = sql_parser.validate("SELECT * FROM dblink('host=other', 'SELECT 1')")
        assert not result.is_safe

    def test_reject_select_into(self, sql_parser: SQLParser) -> None:
        """Test that SELECT INTO is rejected."""
        result = sql_parser.validate("SELECT * INTO new_table FROM users")
        assert not result.is_safe
        assert "select into" in result.error_message.lower()

    def test_reject_for_update(self, sql_parser: SQLParser) -> None:
        """Test that FOR UPDATE is rejected."""
        result = sql_parser.validate("SELECT * FROM users FOR UPDATE")
        assert not result.is_safe
        assert "for update" in result.error_message.lower()

    def test_reject_for_share(self, sql_parser: SQLParser) -> None:
        """Test that FOR SHARE is rejected."""
        result = sql_parser.validate("SELECT * FROM users FOR SHARE")
        assert not result.is_safe
        assert "for share" in result.error_message.lower()

    def test_reject_set_role(self, sql_parser: SQLParser) -> None:
        """Test that SET ROLE is rejected."""
        result = sql_parser.validate("SET ROLE admin")
        assert not result.is_safe
        assert "set role" in result.error_message.lower()

    def test_reject_copy_to(self, sql_parser: SQLParser) -> None:
        """Test that COPY TO is rejected."""
        result = sql_parser.validate("COPY users TO '/tmp/users.csv'")
        assert not result.is_safe
        assert "copy to" in result.error_message.lower()

    def test_reject_listen(self, sql_parser: SQLParser) -> None:
        """Test that LISTEN is rejected."""
        result = sql_parser.validate("LISTEN channel")
        assert not result.is_safe
        assert "listen" in result.error_message.lower()

    def test_reject_notify(self, sql_parser: SQLParser) -> None:
        """Test that NOTIFY is rejected."""
        result = sql_parser.validate("NOTIFY channel")
        assert not result.is_safe
        assert "notify" in result.error_message.lower()

    def test_reject_cte_with_insert(self, sql_parser: SQLParser) -> None:
        """Test that CTE with INSERT is rejected."""
        query = """
        WITH new_user AS (
            INSERT INTO users (name) VALUES ('test') RETURNING id
        )
        SELECT * FROM new_user
        """
        result = sql_parser.validate(query)
        assert not result.is_safe

    def test_syntax_error(self, sql_parser: SQLParser) -> None:
        """Test that syntax errors are detected."""
        # "SELECT FROM" without table name is a true syntax error
        result = sql_parser.validate("SELECT FROM")
        assert not result.is_valid


class TestSQLParserValidateAndRaise:
    """Tests for validate_and_raise method."""

    def test_valid_query_passes(self, sql_parser: SQLParser) -> None:
        """Test that valid queries don't raise."""
        sql_parser.validate_and_raise("SELECT * FROM users")

    def test_unsafe_query_raises(self, sql_parser: SQLParser) -> None:
        """Test that unsafe queries raise UnsafeSQLError."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("DELETE FROM users")

    def test_invalid_query_raises(self, sql_parser: SQLParser) -> None:
        """Test that invalid queries raise SQLSyntaxError."""
        # "SELECT FROM" without table name is a true syntax error
        with pytest.raises(SQLSyntaxError):
            sql_parser.validate_and_raise("SELECT FROM")


class TestSQLParserAddLimit:
    """Tests for add_limit method."""

    def test_add_limit_to_select(self, sql_parser: SQLParser) -> None:
        """Test adding LIMIT to SELECT without limit."""
        result = sql_parser.add_limit("SELECT * FROM users", 100)
        assert "LIMIT" in result.upper()
        assert "100" in result

    def test_preserve_smaller_limit(self, sql_parser: SQLParser) -> None:
        """Test that smaller existing LIMIT is preserved."""
        result = sql_parser.add_limit("SELECT * FROM users LIMIT 10", 100)
        assert "10" in result

    def test_replace_larger_limit(self, sql_parser: SQLParser) -> None:
        """Test that larger existing LIMIT is replaced."""
        result = sql_parser.add_limit("SELECT * FROM users LIMIT 1000", 100)
        assert "100" in result


class TestSQLParserExtractTables:
    """Tests for extract_tables method."""

    def test_single_table(self, sql_parser: SQLParser) -> None:
        """Test extracting single table."""
        tables = sql_parser.extract_tables("SELECT * FROM users")
        assert "users" in tables

    def test_multiple_tables(self, sql_parser: SQLParser) -> None:
        """Test extracting multiple tables from JOIN."""
        tables = sql_parser.extract_tables(
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert "users" in tables
        assert "orders" in tables

    def test_schema_qualified_table(self, sql_parser: SQLParser) -> None:
        """Test extracting schema-qualified table name."""
        tables = sql_parser.extract_tables("SELECT * FROM public.users")
        assert "public.users" in tables


class TestSQLParserNormalize:
    """Tests for normalize method."""

    def test_normalize_query(self, sql_parser: SQLParser) -> None:
        """Test SQL normalization."""
        result = sql_parser.normalize("select   *   from   users   where   id=1")
        assert "SELECT" in result
        assert "FROM" in result


class TestSQLParserParseForPolicy:
    """Tests for parse_for_policy method (access policy validation)."""

    def test_basic_select_with_columns(self, sql_parser: SQLParser) -> None:
        """Test basic SELECT with explicit columns."""
        result = sql_parser.parse_for_policy(
            "SELECT u.id, u.name FROM users u WHERE u.id = 1"
        )
        assert result.is_readonly
        assert result.error_message is None
        assert "users" in result.tables
        assert ("users", "id") in result.columns
        assert ("users", "name") in result.columns
        assert not result.has_select_star
        assert result.schemas == ["public"]

    def test_select_star_single_table(self, sql_parser: SQLParser) -> None:
        """Test SELECT * from single table."""
        result = sql_parser.parse_for_policy("SELECT * FROM orders")
        assert result.has_select_star
        assert "orders" in result.select_star_tables
        assert "orders" in result.tables

    def test_select_star_with_join(self, sql_parser: SQLParser) -> None:
        """Test SELECT * from joined tables."""
        result = sql_parser.parse_for_policy(
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result.has_select_star
        assert "users" in result.select_star_tables
        assert "orders" in result.select_star_tables

    def test_table_star_syntax(self, sql_parser: SQLParser) -> None:
        """Test table.* syntax (e.g., u.*)."""
        result = sql_parser.parse_for_policy(
            "SELECT u.*, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert result.has_select_star
        assert "users" in result.select_star_tables
        # orders should NOT be in select_star_tables since we used o.total, not o.*
        assert "orders" not in result.select_star_tables

    def test_schema_prefix(self, sql_parser: SQLParser) -> None:
        """Test SELECT with schema prefix."""
        result = sql_parser.parse_for_policy(
            "SELECT id, amount FROM sales.orders WHERE status = 'completed'"
        )
        assert "sales" in result.schemas
        assert "orders" in result.tables

    def test_multi_schema_query(self, sql_parser: SQLParser) -> None:
        """Test query with multiple schemas."""
        result = sql_parser.parse_for_policy(
            "SELECT a.id, b.name FROM public.users a "
            "JOIN analytics.events b ON a.id = b.user_id"
        )
        assert "public" in result.schemas
        assert "analytics" in result.schemas
        assert "users" in result.tables
        assert "events" in result.tables

    def test_default_schema_public(self, sql_parser: SQLParser) -> None:
        """Test that default schema is 'public' when not specified."""
        result = sql_parser.parse_for_policy("SELECT id FROM users")
        assert result.schemas == ["public"]

    def test_join_with_aliases(self, sql_parser: SQLParser) -> None:
        """Test JOIN with table aliases resolves correctly."""
        result = sql_parser.parse_for_policy(
            "SELECT u.id, u.name, o.total "
            "FROM users u "
            "JOIN orders o ON u.id = o.user_id"
        )
        assert "users" in result.tables
        assert "orders" in result.tables
        # Columns should reference actual table names, not aliases
        assert ("users", "id") in result.columns
        assert ("users", "name") in result.columns
        assert ("orders", "total") in result.columns

    def test_unsafe_sql_delete(self, sql_parser: SQLParser) -> None:
        """Test that DELETE is detected as non-readonly."""
        result = sql_parser.parse_for_policy("DELETE FROM users WHERE id = 1")
        assert not result.is_readonly
        assert result.error_message is not None
        assert "not allowed" in result.error_message.lower()

    def test_unsafe_sql_insert(self, sql_parser: SQLParser) -> None:
        """Test that INSERT is detected as non-readonly."""
        result = sql_parser.parse_for_policy(
            "INSERT INTO users (name) VALUES ('test')"
        )
        assert not result.is_readonly

    def test_unsafe_sql_update(self, sql_parser: SQLParser) -> None:
        """Test that UPDATE is detected as non-readonly."""
        result = sql_parser.parse_for_policy(
            "UPDATE users SET name = 'test' WHERE id = 1"
        )
        assert not result.is_readonly

    def test_syntax_error(self, sql_parser: SQLParser) -> None:
        """Test that syntax errors are captured."""
        result = sql_parser.parse_for_policy("SELECT FROM")
        assert not result.is_readonly
        assert result.error_message is not None

    def test_columns_without_table_prefix(self, sql_parser: SQLParser) -> None:
        """Test columns without explicit table prefix."""
        result = sql_parser.parse_for_policy(
            "SELECT id, name, email FROM users WHERE active = true"
        )
        # Columns without table prefix should have empty string for table
        assert ("", "id") in result.columns
        assert ("", "name") in result.columns
        assert ("", "email") in result.columns
        assert ("", "active") in result.columns

    def test_mixed_columns_with_and_without_prefix(
        self, sql_parser: SQLParser
    ) -> None:
        """Test mix of columns with and without table prefix."""
        result = sql_parser.parse_for_policy(
            "SELECT u.id, name FROM users u WHERE active = true"
        )
        assert ("users", "id") in result.columns
        assert ("", "name") in result.columns
        assert ("", "active") in result.columns

    def test_subquery(self, sql_parser: SQLParser) -> None:
        """Test subquery table extraction."""
        result = sql_parser.parse_for_policy(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        )
        assert "users" in result.tables
        assert "orders" in result.tables
        assert result.has_select_star

    def test_cte_query(self, sql_parser: SQLParser) -> None:
        """Test CTE (WITH clause) table extraction."""
        result = sql_parser.parse_for_policy(
            "WITH active_users AS (SELECT * FROM users WHERE active = true) "
            "SELECT * FROM active_users"
        )
        assert "users" in result.tables
        assert result.has_select_star

    def test_empty_result_for_no_statement(self, sql_parser: SQLParser) -> None:
        """Test handling of empty/whitespace SQL."""
        result = sql_parser.parse_for_policy("")
        assert not result.is_readonly
        assert result.error_message is not None

    def test_dangerous_function_detected(self, sql_parser: SQLParser) -> None:
        """Test that dangerous functions are detected."""
        result = sql_parser.parse_for_policy("SELECT pg_sleep(10)")
        assert not result.is_readonly
        assert "pg_sleep" in result.error_message.lower()

    def test_stacked_queries_detected(self, sql_parser: SQLParser) -> None:
        """Test that stacked queries are detected."""
        result = sql_parser.parse_for_policy(
            "SELECT * FROM users; DROP TABLE users"
        )
        assert not result.is_readonly
        assert "multiple statements" in result.error_message.lower()
