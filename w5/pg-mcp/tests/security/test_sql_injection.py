"""SQL injection security tests.

These tests verify that the SQL parser correctly identifies and blocks
various SQL injection attack patterns.

Note: Some payloads are fragments designed to be injected into existing queries.
For these fragments, we test that when combined with a SELECT statement, they
are properly blocked. Standalone fragments may fail to parse (which is correct
behavior - they're not valid SQL on their own).
"""

import pytest

from pg_mcp.infrastructure.sql_parser import SQLParser

# Standalone SQL injection payloads (complete, malicious SQL statements)
STANDALONE_INJECTION_PAYLOADS = [
    # Stacked queries (as complete statements)
    ("SELECT * FROM users; DROP TABLE users", "stacked queries"),
    ("SELECT 1; DELETE FROM orders", "stacked queries"),
    ("SELECT * FROM users; TRUNCATE TABLE users", "stacked queries"),
    # Time-based blind (with complete SELECT)
    ("SELECT 1; SELECT pg_sleep(5)", "stacked queries with pg_sleep"),
    # Dangerous functions
    ("SELECT pg_terminate_backend(123)", "dangerous function"),
    ("SELECT pg_cancel_backend(456)", "dangerous function"),
    ("SELECT pg_sleep(10)", "dangerous function"),
    ("SELECT pg_read_file('/etc/passwd')", "dangerous function"),
    ("SELECT lo_import('/etc/passwd')", "dangerous function"),
    # DDL attempts
    ("CREATE TABLE hacked (data TEXT)", "DDL statement"),
    ("DROP TABLE users", "DDL statement"),
    ("ALTER TABLE users ADD COLUMN hacked TEXT", "DDL statement"),
    ("TRUNCATE TABLE orders", "DDL statement"),
    # DML attempts
    ("INSERT INTO users VALUES ('hacker')", "DML statement"),
    ("UPDATE users SET password='hacked'", "DML statement"),
    ("DELETE FROM users WHERE 1=1", "DML statement"),
    # Privilege escalation
    ("SET ROLE postgres", "privilege escalation"),
    ("GRANT ALL ON users TO public", "privilege operation"),
    # File operations
    ("COPY users TO '/tmp/data.csv'", "file operation"),
    ("COPY users FROM '/tmp/data.csv'", "file operation"),
    # Locking
    ("SELECT * FROM users FOR UPDATE", "locking"),
    ("SELECT * FROM users FOR SHARE", "locking"),
]

# Union-based injection payloads (valid SQL that should be blocked or handled)
UNION_INJECTION_PAYLOADS = [
    "SELECT 1 UNION SELECT password FROM users",
    "SELECT id FROM users UNION ALL SELECT password FROM admin",
]


class TestSQLInjection:
    """SQL injection security tests."""

    @pytest.fixture
    def parser(self) -> SQLParser:
        return SQLParser()

    @pytest.mark.parametrize("payload,description", STANDALONE_INJECTION_PAYLOADS)
    def test_injection_blocked(self, parser: SQLParser, payload: str, description: str) -> None:
        """Test that standalone SQL injection payloads are blocked."""
        result = parser.validate(payload)
        # Either parsing fails (is_valid=False) or is_safe is False
        assert result.is_valid is False or result.is_safe is False, (
            f"Injection payload not blocked ({description}): {payload}"
        )

    def test_safe_select_allowed(self, parser: SQLParser) -> None:
        """Test that safe SELECT queries are allowed."""
        safe_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
        ]
        for query in safe_queries:
            result = parser.validate(query)
            assert result.is_safe is True, f"Safe query blocked: {query}"

    def test_stacked_queries_blocked(self, parser: SQLParser) -> None:
        """Test that stacked queries (multiple statements) are blocked."""
        payloads = [
            "SELECT * FROM users; DROP TABLE users",
            "SELECT 1; SELECT 2",
        ]
        for payload in payloads:
            result = parser.validate(payload)
            assert result.is_safe is False, f"Stacked query not blocked: {payload}"
            # Either detected as stacked queries or as a forbidden pattern
            assert (
                "multiple statements" in result.error_message.lower()
                or "forbidden" in result.error_message.lower()
            )

    def test_dangerous_functions_blocked(self, parser: SQLParser) -> None:
        """Test that dangerous PostgreSQL functions are blocked."""
        dangerous_queries = [
            "SELECT pg_sleep(10)",
            "SELECT pg_terminate_backend(1234)",
            "SELECT pg_cancel_backend(5678)",
            "SELECT pg_read_file('/etc/passwd')",
            "SELECT lo_import('/etc/passwd')",
            "SELECT dblink('host=evil.com', 'SELECT 1')",
        ]
        for query in dangerous_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"Dangerous function not blocked: {query}"

    def test_ddl_statements_blocked(self, parser: SQLParser) -> None:
        """Test that DDL statements are blocked."""
        ddl_queries = [
            "CREATE TABLE test (id INT)",
            "DROP TABLE users",
            "ALTER TABLE users ADD COLUMN hacked TEXT",
            "TRUNCATE TABLE orders",
        ]
        for query in ddl_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"DDL statement not blocked: {query}"

    def test_dml_statements_blocked(self, parser: SQLParser) -> None:
        """Test that DML statements (INSERT/UPDATE/DELETE) are blocked."""
        dml_queries = [
            "INSERT INTO users (name) VALUES ('hacker')",
            "UPDATE users SET password = 'hacked' WHERE 1=1",
            "DELETE FROM users WHERE id = 1",
        ]
        for query in dml_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"DML statement not blocked: {query}"

    def test_privilege_escalation_blocked(self, parser: SQLParser) -> None:
        """Test that privilege escalation attempts are blocked."""
        escalation_queries = [
            "SET ROLE postgres",
            "SET SESSION AUTHORIZATION 'admin'",
            "GRANT ALL ON users TO public",
            "REVOKE SELECT ON users FROM readonly",
        ]
        for query in escalation_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"Escalation not blocked: {query}"

    def test_file_operations_blocked(self, parser: SQLParser) -> None:
        """Test that file operations are blocked."""
        file_queries = [
            "COPY users TO '/tmp/data.csv'",
            "COPY users FROM '/tmp/data.csv'",
        ]
        for query in file_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"File operation not blocked: {query}"

    def test_locking_blocked(self, parser: SQLParser) -> None:
        """Test that locking clauses are blocked."""
        locking_queries = [
            "SELECT * FROM users FOR UPDATE",
            "SELECT * FROM users FOR SHARE",
            "SELECT * FROM users FOR NO KEY UPDATE",
        ]
        for query in locking_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"Locking clause not blocked: {query}"

    def test_cte_with_modification_blocked(self, parser: SQLParser) -> None:
        """Test that CTEs with data modification are blocked."""
        cte_queries = [
            ("WITH ins AS (INSERT INTO users VALUES (1) RETURNING *) SELECT * FROM ins"),
            ("WITH del AS (DELETE FROM users WHERE id = 1 RETURNING *) SELECT * FROM del"),
        ]
        for query in cte_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"CTE modification not blocked: {query}"

    def test_unicode_bypass_attempts(self, parser: SQLParser) -> None:
        """Test that unicode bypass attempts are handled."""
        # These should either be blocked or parsed correctly
        unicode_queries = [
            "SELECT * FROM users WHERE name = 'test\u0000'",
        ]
        for query in unicode_queries:
            result = parser.validate(query)
            # Should either be blocked or safely handled
            assert result.is_valid is True or result.is_safe is False

    def test_comment_injection(self, parser: SQLParser) -> None:
        """Test that comment-based injections are handled."""
        comment_queries = [
            "SELECT * FROM users WHERE id = 1 -- AND password = 'x'",
            "SELECT * FROM users WHERE id = 1 /* comment */ AND active = true",
        ]
        for query in comment_queries:
            result = parser.validate(query)
            # Comments in queries are valid and should be safe
            # as long as they don't introduce additional statements
            assert result.is_valid is True

    def test_union_queries_allowed_but_access_controlled(self, parser: SQLParser) -> None:
        """Test that UNION queries are syntactically valid.

        UNION queries are valid SQL and the parser should not block them.
        Access control (which tables/columns can be accessed) is handled
        by the access policy layer, not the SQL parser.
        """
        union_queries = [
            "SELECT id FROM users UNION SELECT id FROM orders",
            "SELECT name FROM users UNION ALL SELECT name FROM admins",
        ]
        for query in union_queries:
            result = parser.validate(query)
            # UNION is valid SQL syntax
            assert result.is_valid is True
            # And it's a read-only operation
            assert result.is_safe is True

    def test_injection_fragments_in_where_clause(self, parser: SQLParser) -> None:
        """Test SQL fragments commonly used in WHERE clause injection.

        These fragments, when injected into a WHERE clause, could be dangerous.
        We test that complete queries containing these patterns are handled properly.
        """
        # These are complete queries that contain injection-style patterns
        where_injection_queries = [
            # Tautology patterns (valid SQL, but suspicious)
            "SELECT * FROM users WHERE 1=1",
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            # UNION injection in WHERE (the UNION itself is valid SQL)
            "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM admin",
        ]
        for query in where_injection_queries:
            result = parser.validate(query)
            # These are syntactically valid queries
            assert result.is_valid is True
            # They are read-only, so technically "safe" from mutation perspective
            # Access control should handle restricting access to tables/columns

    def test_sql_injection_via_select_into(self, parser: SQLParser) -> None:
        """Test that SELECT INTO (table creation) is blocked."""
        queries = [
            "SELECT * INTO new_table FROM users",
            "SELECT id, name INTO backup FROM users",
        ]
        for query in queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"SELECT INTO not blocked: {query}"
            assert "select into" in result.error_message.lower()

    def test_dblink_injection(self, parser: SQLParser) -> None:
        """Test that dblink function (external connections) is blocked."""
        queries = [
            "SELECT * FROM dblink('host=evil.com', 'SELECT * FROM users') AS t(id int)",
            "SELECT dblink_exec('conn', 'DROP TABLE users')",
        ]
        for query in queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"dblink not blocked: {query}"

    def test_notification_functions_blocked(self, parser: SQLParser) -> None:
        """Test that LISTEN/NOTIFY operations are blocked."""
        notification_queries = [
            "LISTEN channel_name",
            "NOTIFY channel_name",
            "UNLISTEN channel_name",
        ]
        for query in notification_queries:
            result = parser.validate(query)
            assert result.is_safe is False, f"Notification op not blocked: {query}"
