"""MySQL metadata extraction service."""

import aiomysql

from src.models.database import TableInfo
from src.services.metadata_base import build_table_hierarchy
from src.utils.db_utils import parse_mysql_url


# SQL queries for MySQL metadata extraction
# Base query without db filter - filter is added via parameterized query
MYSQL_TABLES_QUERY_BASE = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
"""

MYSQL_TABLES_QUERY_WITH_DB = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
  AND table_schema = %s
ORDER BY table_schema, table_name
"""

MYSQL_TABLES_QUERY_ALL = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
ORDER BY table_schema, table_name
"""

MYSQL_COLUMNS_QUERY_BASE = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.ordinal_position,
    CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_primary_key,
    CASE WHEN fk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_foreign_key
FROM information_schema.columns c
LEFT JOIN (
    SELECT DISTINCT kcu.table_schema, kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
) pk ON c.table_schema = pk.table_schema
    AND c.table_name = pk.table_name
    AND c.column_name = pk.column_name
LEFT JOIN (
    SELECT DISTINCT kcu.table_schema, kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
) fk ON c.table_schema = fk.table_schema
    AND c.table_name = fk.table_name
    AND c.column_name = fk.column_name
WHERE c.table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
"""

MYSQL_COLUMNS_QUERY_WITH_DB = MYSQL_COLUMNS_QUERY_BASE + """
  AND c.table_schema = %s
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""

MYSQL_COLUMNS_QUERY_ALL = MYSQL_COLUMNS_QUERY_BASE + """
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""




class MySQLMetadataExtractor:
    """Service for extracting metadata from MySQL databases."""

    @staticmethod
    async def extract(connection_url: str) -> tuple[list[TableInfo], list[TableInfo]]:
        """Extract metadata from a MySQL database.

        Args:
            connection_url: MySQL connection URL

        Returns:
            Tuple of (tables, views) with their column information

        Raises:
            ConnectionError: If unable to connect to database
        """
        params = parse_mysql_url(connection_url)
        db_name = params.pop("db")

        try:
            conn = await aiomysql.connect(**params)
            try:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Use parameterized queries to prevent SQL injection
                    if db_name:
                        # Get tables and views with database filter
                        await cur.execute(MYSQL_TABLES_QUERY_WITH_DB, (db_name,))
                        table_rows = await cur.fetchall()

                        # Get columns with database filter
                        await cur.execute(MYSQL_COLUMNS_QUERY_WITH_DB, (db_name,))
                        column_rows = await cur.fetchall()
                    else:
                        # Get all tables and views
                        await cur.execute(MYSQL_TABLES_QUERY_ALL)
                        table_rows = await cur.fetchall()

                        # Get all columns
                        await cur.execute(MYSQL_COLUMNS_QUERY_ALL)
                        column_rows = await cur.fetchall()
            finally:
                conn.close()

        except aiomysql.Error as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e

        # Use shared helper to organize into hierarchical structure
        return build_table_hierarchy(table_rows, column_rows)

    @staticmethod
    async def test_connection(connection_url: str) -> bool:
        """Test if connection to MySQL database is successful.

        Args:
            connection_url: MySQL connection URL

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If unable to connect
        """
        params = parse_mysql_url(connection_url)
        params.pop("db", None)  # Remove db for connection test

        try:
            conn = await aiomysql.connect(**params)
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    return True
            finally:
                conn.close()
        except aiomysql.Error as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e
