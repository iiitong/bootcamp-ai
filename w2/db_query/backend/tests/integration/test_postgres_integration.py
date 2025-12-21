"""Integration tests for PostgreSQL database support.

These tests require a real PostgreSQL database. Set TEST_POSTGRES_URL environment
variable to run them. Tests are automatically skipped if not set.

Example:
    TEST_POSTGRES_URL=postgresql://user:pass@localhost:5432/testdb pytest tests/integration/
"""

import pytest

from src.services.metadata import MetadataExtractor
from src.services.query import QueryExecutor
from src.services.registry import DatabaseRegistry


class TestPostgresMetadataIntegration:
    """Integration tests for PostgreSQL metadata extraction."""

    @pytest.mark.asyncio
    async def test_extract_metadata(self, postgres_url: str) -> None:
        """Test extracting metadata from a real PostgreSQL database."""
        tables, views = await MetadataExtractor.extract(postgres_url)

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

    @pytest.mark.asyncio
    async def test_test_connection_success(self, postgres_url: str) -> None:
        """Test successful connection to PostgreSQL database."""
        result = await MetadataExtractor.test_connection(postgres_url)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self) -> None:
        """Test connection failure with invalid URL."""
        invalid_url = "postgresql://invalid:invalid@nonexistent:5432/db"

        with pytest.raises(ConnectionError):
            await MetadataExtractor.test_connection(invalid_url)


class TestPostgresQueryIntegration:
    """Integration tests for PostgreSQL query execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, postgres_url: str) -> None:
        """Test executing a simple SELECT query."""
        result = await QueryExecutor.execute(
            postgres_url,
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
    async def test_execute_query_with_limit(self, postgres_url: str) -> None:
        """Test executing a query with results (if tables exist)."""
        # This query should work on any PostgreSQL database
        result = await QueryExecutor.execute(
            postgres_url,
            "SELECT tablename FROM pg_tables LIMIT 5",
            timeout_seconds=30,
        )

        assert isinstance(result.columns, list)
        assert isinstance(result.rows, list)
        assert result.row_count <= 5


class TestRegistryPostgresIntegration:
    """Integration tests using the database registry for PostgreSQL."""

    @pytest.mark.asyncio
    async def test_registry_postgres_executor(self, postgres_url: str) -> None:
        """Test using registry to get PostgreSQL executor."""
        executor = DatabaseRegistry.get_executor("postgresql")

        result = await executor.execute(
            postgres_url,
            "SELECT version() as version",
            timeout_seconds=30,
        )

        assert result.row_count == 1
        assert "version" in result.columns
        assert isinstance(result.rows[0]["version"], str)

    @pytest.mark.asyncio
    async def test_registry_postgres_extractor(self, postgres_url: str) -> None:
        """Test using registry to get PostgreSQL extractor."""
        extractor = DatabaseRegistry.get_extractor("postgresql")

        tables, views = await extractor.extract(postgres_url)

        assert isinstance(tables, list)
        assert isinstance(views, list)
