"""Tests for MySQL service components."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.metadata_mysql import MySQLMetadataExtractor, _parse_mysql_url
from src.services.query_mysql import MySQLQueryExecutor
from src.services.query_mysql import _parse_mysql_url as query_parse_mysql_url


class TestMySQLUrlParsing:
    """Tests for MySQL URL parsing functions."""

    def test_parse_full_url(self) -> None:
        """Parse complete MySQL URL with all components."""
        url = "mysql://root:secret@localhost:3307/ecommerce"
        params = _parse_mysql_url(url)

        assert params["host"] == "localhost"
        assert params["port"] == 3307
        assert params["user"] == "root"
        assert params["password"] == "secret"
        assert params["db"] == "ecommerce"

    def test_parse_url_without_password(self) -> None:
        """Parse MySQL URL without password."""
        url = "mysql://root@localhost:3306/mydb"
        params = _parse_mysql_url(url)

        assert params["host"] == "localhost"
        assert params["port"] == 3306
        assert params["user"] == "root"
        assert params["password"] == ""
        assert params["db"] == "mydb"

    def test_parse_url_default_port(self) -> None:
        """Default port should be 3306."""
        url = "mysql://root@localhost/mydb"
        params = _parse_mysql_url(url)

        assert params["port"] == 3306

    def test_parse_url_default_host(self) -> None:
        """Default host should be localhost."""
        url = "mysql:///mydb"
        params = _parse_mysql_url(url)

        assert params["host"] == "localhost"

    def test_parse_url_default_user(self) -> None:
        """Default user should be root."""
        url = "mysql://localhost/mydb"
        params = _parse_mysql_url(url)

        assert params["user"] == "root"

    def test_parse_mysql_aiomysql_scheme(self) -> None:
        """mysql+aiomysql:// scheme should be handled."""
        url = "mysql+aiomysql://user:pass@host:3307/db"
        params = _parse_mysql_url(url)

        assert params["host"] == "host"
        assert params["port"] == 3307
        assert params["user"] == "user"
        assert params["password"] == "pass"
        assert params["db"] == "db"

    def test_parse_url_no_database(self) -> None:
        """URL without database should have None for db."""
        url = "mysql://root@localhost:3306"
        params = _parse_mysql_url(url)

        assert params["db"] is None

    def test_query_parse_matches_metadata_parse(self) -> None:
        """Both URL parsers should produce consistent results."""
        url = "mysql://user:pass@host:3307/testdb"

        metadata_params = _parse_mysql_url(url)
        query_params = query_parse_mysql_url(url)

        assert metadata_params["host"] == query_params["host"]
        assert metadata_params["port"] == query_params["port"]
        assert metadata_params["user"] == query_params["user"]
        assert metadata_params["password"] == query_params["password"]
        assert metadata_params["db"] == query_params["db"]


class TestMySQLMetadataExtractor:
    """Tests for MySQLMetadataExtractor class."""

    @pytest.mark.asyncio
    async def test_extract_returns_tables_and_views(self) -> None:
        """Extract should return tuple of (tables, views)."""
        mock_cursor = AsyncMock()
        # Mock table query results (uppercase keys as MySQL returns)
        mock_cursor.fetchall.side_effect = [
            # Tables query result
            [
                {"TABLE_SCHEMA": "testdb", "TABLE_NAME": "users", "TABLE_TYPE": "BASE TABLE"},
                {"TABLE_SCHEMA": "testdb", "TABLE_NAME": "user_view", "TABLE_TYPE": "VIEW"},
            ],
            # Columns query result
            [
                {
                    "TABLE_SCHEMA": "testdb",
                    "TABLE_NAME": "users",
                    "COLUMN_NAME": "id",
                    "DATA_TYPE": "int",
                    "IS_NULLABLE": "NO",
                    "COLUMN_DEFAULT": None,
                    "is_primary_key": 1,
                    "is_foreign_key": 0,
                },
                {
                    "TABLE_SCHEMA": "testdb",
                    "TABLE_NAME": "users",
                    "COLUMN_NAME": "email",
                    "DATA_TYPE": "varchar",
                    "IS_NULLABLE": "YES",
                    "COLUMN_DEFAULT": None,
                    "is_primary_key": 0,
                    "is_foreign_key": 0,
                },
                {
                    "TABLE_SCHEMA": "testdb",
                    "TABLE_NAME": "user_view",
                    "COLUMN_NAME": "id",
                    "DATA_TYPE": "int",
                    "IS_NULLABLE": "NO",
                    "COLUMN_DEFAULT": None,
                    "is_primary_key": 0,
                    "is_foreign_key": 0,
                },
            ],
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__aexit__ = AsyncMock()

        with patch("src.services.metadata_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn

            tables, views = await MySQLMetadataExtractor.extract("mysql://root@localhost/testdb")

            assert len(tables) == 1
            assert len(views) == 1
            assert tables[0].name == "users"
            assert views[0].name == "user_view"
            assert len(tables[0].columns) == 2

    @pytest.mark.asyncio
    async def test_extract_connection_error(self) -> None:
        """Extract should raise ConnectionError on connection failure."""
        import aiomysql

        with patch("src.services.metadata_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = aiomysql.Error("Connection refused")

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await MySQLMetadataExtractor.extract("mysql://root@localhost/testdb")

    @pytest.mark.asyncio
    async def test_test_connection_success(self) -> None:
        """test_connection should return True on successful connection."""
        mock_cursor = AsyncMock()
        mock_cursor.execute = AsyncMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__aexit__ = AsyncMock()

        with patch("src.services.metadata_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn

            result = await MySQLMetadataExtractor.test_connection("mysql://root@localhost/testdb")

            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self) -> None:
        """test_connection should raise ConnectionError on failure."""
        import aiomysql

        with patch("src.services.metadata_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = aiomysql.Error("Host not found")

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await MySQLMetadataExtractor.test_connection("mysql://root@localhost/testdb")


class TestMySQLQueryExecutor:
    """Tests for MySQLQueryExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Execute should return QueryResult with data."""
        mock_cursor = AsyncMock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        )
        mock_cursor.description = [("id",), ("name",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__aexit__ = AsyncMock()

        with patch("src.services.query_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn

            result = await MySQLQueryExecutor.execute(
                "mysql://root@localhost/testdb",
                "SELECT id, name FROM users",
            )

            assert result.columns == ["id", "name"]
            assert result.row_count == 2
            assert result.rows[0]["name"] == "Alice"
            assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_empty_result(self) -> None:
        """Execute should handle empty results."""
        mock_cursor = AsyncMock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_cursor.description = [("id",), ("name",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__aexit__ = AsyncMock()

        with patch("src.services.query_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn

            result = await MySQLQueryExecutor.execute(
                "mysql://root@localhost/testdb",
                "SELECT id, name FROM users WHERE 1=0",
            )

            assert result.columns == ["id", "name"]
            assert result.row_count == 0
            assert result.rows == []

    @pytest.mark.asyncio
    async def test_execute_timeout_error(self) -> None:
        """Execute should raise TimeoutError on query timeout."""
        # Import the OperationalError class from the same module that query_mysql uses
        from src.services import query_mysql
        import aiomysql as aiomysql_module

        # Create the exception using the actual module
        timeout_exc = aiomysql_module.OperationalError(3024, "Query execution was interrupted")

        with patch.object(query_mysql, "aiomysql") as mock_aiomysql:
            # Set up the mock to raise OperationalError on connect
            mock_aiomysql.OperationalError = aiomysql_module.OperationalError
            mock_aiomysql.ProgrammingError = aiomysql_module.ProgrammingError
            mock_aiomysql.Error = aiomysql_module.Error
            mock_aiomysql.DictCursor = aiomysql_module.DictCursor
            mock_aiomysql.connect = AsyncMock(side_effect=timeout_exc)

            with pytest.raises(TimeoutError, match="timed out"):
                await MySQLQueryExecutor.execute(
                    "mysql://root@localhost/testdb",
                    "SELECT * FROM big_table",
                    timeout_seconds=1,
                )

    @pytest.mark.asyncio
    async def test_execute_connection_error(self) -> None:
        """Execute should raise ConnectionError on connection failure."""
        import aiomysql

        with patch("src.services.query_mysql.aiomysql.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = aiomysql.OperationalError(2003, "Can't connect to MySQL server")

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await MySQLQueryExecutor.execute(
                    "mysql://root@localhost/testdb",
                    "SELECT 1",
                )

    @pytest.mark.asyncio
    async def test_execute_syntax_error(self) -> None:
        """Execute should raise ValueError on SQL syntax error."""
        from src.services import query_mysql
        import aiomysql as aiomysql_module

        # Create the exception using the actual module
        syntax_exc = aiomysql_module.ProgrammingError(1064, "You have an error in your SQL syntax")

        with patch.object(query_mysql, "aiomysql") as mock_aiomysql:
            # Set up the mock to raise ProgrammingError on connect
            mock_aiomysql.OperationalError = aiomysql_module.OperationalError
            mock_aiomysql.ProgrammingError = aiomysql_module.ProgrammingError
            mock_aiomysql.Error = aiomysql_module.Error
            mock_aiomysql.DictCursor = aiomysql_module.DictCursor
            mock_aiomysql.connect = AsyncMock(side_effect=syntax_exc)

            with pytest.raises(ValueError, match="query error"):
                await MySQLQueryExecutor.execute(
                    "mysql://root@localhost/testdb",
                    "SELCT * FROM users",  # typo
                )
