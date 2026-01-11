"""Integration tests using local PostgreSQL.

Run with: uv run pytest tests/integration/test_local_postgres.py -v

Requires a local PostgreSQL server at localhost:5432.
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator

import asyncpg
import pytest

from pg_mcp.config.models import DatabaseConfig
from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import UnsafeSQLError

# Configure for local PostgreSQL
LOCAL_PG_CONFIG = DatabaseConfig(
    name="local_test_db",
    host="localhost",
    port=5432,
    dbname="postgres",  # Use default database
    user="postgres",
    password=None,  # No password
    ssl_mode="disable",  # Local PostgreSQL typically doesn't use SSL
)


@pytest.fixture
async def local_pool() -> AsyncGenerator[DatabasePool]:
    """Create a connection pool to local PostgreSQL."""
    pool = DatabasePool(LOCAL_PG_CONFIG)
    try:
        await pool.connect()
        print(f"\n[OK] Connected to local PostgreSQL: {LOCAL_PG_CONFIG.host}")
        yield pool
    finally:
        await pool.disconnect()


@pytest.fixture
async def test_table(local_pool: DatabasePool) -> AsyncGenerator[str]:
    """Create a temporary test table."""
    table_name = "pg_mcp_test_table"

    # Clean up if exists
    await local_pool.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create test table
    await local_pool.execute(f"""
        CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            value INTEGER DEFAULT 0
        )
    """)

    # Insert test data
    await local_pool.execute(f"""
        INSERT INTO {table_name} (name, value) VALUES
        ('alice', 100),
        ('bob', 200),
        ('charlie', 300)
    """)

    yield table_name

    # Cleanup
    await local_pool.execute(f"DROP TABLE IF EXISTS {table_name}")


class TestLocalPostgresConnection:
    """Test basic PostgreSQL connectivity."""

    @pytest.mark.asyncio
    async def test_connection_successful(self, local_pool: DatabasePool):
        """Test that we can connect to local PostgreSQL."""
        assert local_pool.is_connected
        result = await local_pool.fetch("SELECT 1 as value")
        assert result[0]["value"] == 1
        print("[OK] Basic SELECT query works")

    @pytest.mark.asyncio
    async def test_version_check(self, local_pool: DatabasePool):
        """Check PostgreSQL version."""
        result = await local_pool.fetch("SELECT version()")
        version = result[0]["version"]
        print(f"[INFO] PostgreSQL version: {version}")
        assert "PostgreSQL" in version


class TestReadOnlyTransactionDefense:
    """Test read-only transaction enforcement (defense in depth)."""

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_insert(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Test that INSERT is blocked in read-only transaction."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(
                f"INSERT INTO {test_table} (name, value) VALUES ('hacker', 999) RETURNING *"
            )
        print("[OK] INSERT blocked by read-only transaction")

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_update(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Test that UPDATE is blocked in read-only transaction."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(
                f"UPDATE {test_table} SET value = 999 WHERE name = 'alice'"
            )
        print("[OK] UPDATE blocked by read-only transaction")

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_delete(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Test that DELETE is blocked in read-only transaction."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(f"DELETE FROM {test_table} WHERE name = 'alice'")
        print("[OK] DELETE blocked by read-only transaction")

    @pytest.mark.asyncio
    async def test_readonly_transaction_blocks_truncate(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Test that TRUNCATE is blocked in read-only transaction."""
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(f"TRUNCATE {test_table}")
        print("[OK] TRUNCATE blocked by read-only transaction")

    @pytest.mark.asyncio
    async def test_readonly_transaction_allows_select(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Test that SELECT works in read-only transaction."""
        result = await local_pool.fetch_readonly(f"SELECT * FROM {test_table}")
        assert len(result) == 3
        print(f"[OK] SELECT works in read-only transaction, got {len(result)} rows")


class TestSQLParserValidation:
    """Test SQL parser security validation."""

    @pytest.fixture
    def sql_parser(self) -> SQLParser:
        return SQLParser()

    def test_safe_select_passes(self, sql_parser: SQLParser):
        """Test that safe SELECT queries pass validation."""
        safe_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE id = 1",
            "SELECT COUNT(*) FROM orders GROUP BY status",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent",
        ]
        for query in safe_queries:
            result = sql_parser.validate(query)
            assert result.is_valid and result.is_safe, f"Query should be safe: {query}"
        print(f"[OK] {len(safe_queries)} safe SELECT queries passed validation")

    def test_insert_blocked(self, sql_parser: SQLParser):
        """Test that INSERT is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("INSERT INTO users (name) VALUES ('hacker')")
        print("[OK] INSERT blocked by SQL parser")

    def test_update_blocked(self, sql_parser: SQLParser):
        """Test that UPDATE is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("UPDATE users SET name = 'hacked' WHERE id = 1")
        print("[OK] UPDATE blocked by SQL parser")

    def test_delete_blocked(self, sql_parser: SQLParser):
        """Test that DELETE is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("DELETE FROM users WHERE id = 1")
        print("[OK] DELETE blocked by SQL parser")

    def test_drop_blocked(self, sql_parser: SQLParser):
        """Test that DROP is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("DROP TABLE users")
        print("[OK] DROP blocked by SQL parser")

    def test_stacked_queries_blocked(self, sql_parser: SQLParser):
        """Test that stacked queries (SQL injection) are blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("SELECT * FROM users; DROP TABLE users;")
        print("[OK] Stacked queries blocked by SQL parser")

    def test_pg_sleep_blocked(self, sql_parser: SQLParser):
        """Test that pg_sleep (DoS) is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("SELECT pg_sleep(10)")
        print("[OK] pg_sleep blocked by SQL parser")

    def test_select_into_blocked(self, sql_parser: SQLParser):
        """Test that SELECT INTO is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("SELECT * INTO new_table FROM users")
        print("[OK] SELECT INTO blocked by SQL parser")

    def test_for_update_blocked(self, sql_parser: SQLParser):
        """Test that FOR UPDATE is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("SELECT * FROM users FOR UPDATE")
        print("[OK] FOR UPDATE blocked by SQL parser")

    def test_cte_with_insert_blocked(self, sql_parser: SQLParser):
        """Test that CTE with INSERT is blocked."""
        with pytest.raises(UnsafeSQLError):
            sql_parser.validate_and_raise("""
                WITH ins AS (INSERT INTO logs (msg) VALUES ('test') RETURNING *)
                SELECT * FROM ins
            """)
        print("[OK] CTE with INSERT blocked by SQL parser")


class TestStatementTimeout:
    """Test statement timeout enforcement."""

    @pytest.mark.asyncio
    async def test_statement_timeout_works(self, local_pool: DatabasePool):
        """Test that statement timeout is enforced."""
        # This should timeout (pg_sleep for 5 seconds with 1 second timeout)
        with pytest.raises(asyncio.TimeoutError):
            await local_pool.fetch_readonly(
                "SELECT pg_sleep(5)",
                timeout=1.0,
            )
        print("[OK] Statement timeout enforced")

    @pytest.mark.asyncio
    async def test_fast_query_succeeds(self, local_pool: DatabasePool, test_table: str):
        """Test that fast queries succeed within timeout."""
        result = await local_pool.fetch_readonly(
            f"SELECT * FROM {test_table}",
            timeout=5.0,
        )
        assert len(result) == 3
        print("[OK] Fast query completed within timeout")


class TestDataIntegrity:
    """Test that data is not modified after attempted attacks."""

    @pytest.mark.asyncio
    async def test_data_unchanged_after_blocked_insert(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Verify data is unchanged after blocked INSERT attempt."""
        # Count before
        before = await local_pool.fetch(f"SELECT COUNT(*) as cnt FROM {test_table}")

        # Attempt blocked INSERT
        with contextlib.suppress(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(
                f"INSERT INTO {test_table} (name, value) VALUES ('attacker', 666)"
            )

        # Count after
        after = await local_pool.fetch(f"SELECT COUNT(*) as cnt FROM {test_table}")

        assert before[0]["cnt"] == after[0]["cnt"]
        print(f"[OK] Data unchanged: {before[0]['cnt']} rows before and after blocked INSERT")

    @pytest.mark.asyncio
    async def test_data_unchanged_after_blocked_update(
        self, local_pool: DatabasePool, test_table: str
    ):
        """Verify data is unchanged after blocked UPDATE attempt."""
        # Get value before
        before = await local_pool.fetch(
            f"SELECT value FROM {test_table} WHERE name = 'alice'"
        )

        # Attempt blocked UPDATE
        with contextlib.suppress(asyncpg.ReadOnlySQLTransactionError):
            await local_pool.fetch_readonly(
                f"UPDATE {test_table} SET value = 999999 WHERE name = 'alice'"
            )

        # Get value after
        after = await local_pool.fetch(
            f"SELECT value FROM {test_table} WHERE name = 'alice'"
        )

        assert before[0]["value"] == after[0]["value"]
        print(f"[OK] Data unchanged: alice's value is still {before[0]['value']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
