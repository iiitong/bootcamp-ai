"""Integration tests for MySQL database support.

These tests require a real MySQL database. Set TEST_MYSQL_URL environment
variable to run them. Tests are automatically skipped if not set.

Example:
    TEST_MYSQL_URL=mysql://root@localhost:3306/testdb pytest tests/integration/
"""

import pytest

from src.services.metadata_mysql import MySQLMetadataExtractor
from src.services.query_mysql import MySQLQueryExecutor
from src.services.registry import DatabaseRegistry


class TestMySQLMetadataIntegration:
    """Integration tests for MySQL metadata extraction."""

    @pytest.mark.asyncio
    async def test_extract_metadata(self, mysql_url: str) -> None:
        """Test extracting metadata from a real MySQL database."""
        tables, views = await MySQLMetadataExtractor.extract(mysql_url)

        # Should return lists (may be empty for a fresh database)
        assert isinstance(tables, list)
        assert isinstance(views, list)

        # If there are tables, verify structure
        if tables:
            table = tables[0]
            assert hasattr(table, "schema_name")
            assert hasattr(table, "name")
            assert hasattr(table, "type")
            assert hasattr(table, "columns")
            assert table.type == "TABLE"

        # If there are views, verify structure
        if views:
            view = views[0]
            assert view.type == "VIEW"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mysql_url: str) -> None:
        """Test successful connection to MySQL database."""
        result = await MySQLMetadataExtractor.test_connection(mysql_url)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self) -> None:
        """Test connection failure with invalid URL."""
        invalid_url = "mysql://invalid:invalid@nonexistent:3306/db"

        with pytest.raises(ConnectionError):
            await MySQLMetadataExtractor.test_connection(invalid_url)


class TestMySQLQueryIntegration:
    """Integration tests for MySQL query execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, mysql_url: str) -> None:
        """Test executing a simple SELECT query."""
        result = await MySQLQueryExecutor.execute(
            mysql_url,
            "SELECT 1 as test_value, 'hello' as test_string",
            timeout_seconds=30,
        )

        assert result.row_count == 1
        assert "test_value" in result.columns
        assert "test_string" in result.columns
        assert result.rows[0]["test_value"] == 1
        assert result.rows[0]["test_string"] == "hello"
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_query_with_limit(self, mysql_url: str) -> None:
        """Test executing a query with results (if tables exist)."""
        # This query should work on any MySQL database
        result = await MySQLQueryExecutor.execute(
            mysql_url,
            "SELECT TABLE_NAME FROM information_schema.tables LIMIT 5",
            timeout_seconds=30,
        )

        assert isinstance(result.columns, list)
        assert isinstance(result.rows, list)
        assert result.row_count <= 5


class TestRegistryIntegration:
    """Integration tests using the database registry."""

    @pytest.mark.asyncio
    async def test_registry_mysql_executor(self, mysql_url: str) -> None:
        """Test using registry to get MySQL executor."""
        executor = DatabaseRegistry.get_executor("mysql")

        result = await executor.execute(
            mysql_url,
            "SELECT VERSION() as version",
            timeout_seconds=30,
        )

        assert result.row_count == 1
        assert "version" in result.columns
        assert isinstance(result.rows[0]["version"], str)

    @pytest.mark.asyncio
    async def test_registry_mysql_extractor(self, mysql_url: str) -> None:
        """Test using registry to get MySQL extractor."""
        extractor = DatabaseRegistry.get_extractor("mysql")

        tables, views = await extractor.extract(mysql_url)

        assert isinstance(tables, list)
        assert isinstance(views, list)

    def test_registry_dialect(self) -> None:
        """Test registry dialect lookup."""
        assert DatabaseRegistry.get_dialect("mysql") == "mysql"
        assert DatabaseRegistry.get_dialect("postgresql") == "postgres"
