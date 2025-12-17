"""MySQL metadata extraction service."""

from urllib.parse import urlparse

import aiomysql

from src.models.database import ColumnInfo, TableInfo


# SQL queries for MySQL metadata extraction
MYSQL_TABLES_QUERY = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
ORDER BY table_schema, table_name
"""

MYSQL_COLUMNS_QUERY = """
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
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""


def _parse_mysql_url(url: str) -> dict:
    """Parse MySQL connection URL into connection parameters.

    Args:
        url: MySQL connection URL (e.g., 'mysql://user:pass@host:port/database')

    Returns:
        Dictionary with connection parameters for aiomysql
    """
    parsed = urlparse(url)

    # Handle mysql+aiomysql:// scheme
    scheme = parsed.scheme
    if scheme == "mysql+aiomysql":
        scheme = "mysql"

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "db": parsed.path.lstrip("/") if parsed.path else None,
    }


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
        params = _parse_mysql_url(connection_url)
        db_name = params.pop("db")

        try:
            conn = await aiomysql.connect(**params)
            try:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # If specific database requested, filter by it
                    if db_name:
                        tables_query = MYSQL_TABLES_QUERY.replace(
                            "ORDER BY", f"AND table_schema = '{db_name}' ORDER BY"
                        )
                        columns_query = MYSQL_COLUMNS_QUERY.replace(
                            "ORDER BY c.table_schema",
                            f"AND c.table_schema = '{db_name}' ORDER BY c.table_schema",
                        )
                    else:
                        tables_query = MYSQL_TABLES_QUERY
                        columns_query = MYSQL_COLUMNS_QUERY

                    # Get tables and views
                    await cur.execute(tables_query)
                    table_rows = await cur.fetchall()

                    # Get columns
                    await cur.execute(columns_query)
                    column_rows = await cur.fetchall()
            finally:
                conn.close()

        except aiomysql.Error as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e

        # Organize into hierarchical structure
        tables: list[TableInfo] = []
        views: list[TableInfo] = []
        table_map: dict[tuple[str, str], TableInfo] = {}

        # Create table/view entries
        # Note: MySQL information_schema returns uppercase column names
        for row in table_rows:
            table_type = "VIEW" if row["TABLE_TYPE"] == "VIEW" else "TABLE"
            table_info = TableInfo(
                schema_name=row["TABLE_SCHEMA"],
                name=row["TABLE_NAME"],
                type=table_type,
                columns=[],
            )
            key = (row["TABLE_SCHEMA"], row["TABLE_NAME"])
            table_map[key] = table_info

            if table_type == "VIEW":
                views.append(table_info)
            else:
                tables.append(table_info)

        # Add columns to tables/views
        for row in column_rows:
            key = (row["TABLE_SCHEMA"], row["TABLE_NAME"])
            if key in table_map:
                column = ColumnInfo(
                    name=row["COLUMN_NAME"],
                    data_type=row["DATA_TYPE"],
                    nullable=row["IS_NULLABLE"] == "YES",
                    default_value=row["COLUMN_DEFAULT"],
                    is_primary_key=bool(row["is_primary_key"]),
                    is_foreign_key=bool(row["is_foreign_key"]),
                )
                table_map[key].columns.append(column)

        return tables, views

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
        params = _parse_mysql_url(connection_url)
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
