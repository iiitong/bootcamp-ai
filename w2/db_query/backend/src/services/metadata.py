"""PostgreSQL metadata extraction service."""

import psycopg
from psycopg.rows import dict_row

from src.models.database import ColumnInfo, TableInfo


# SQL queries for metadata extraction
TABLES_QUERY = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name
"""

COLUMNS_QUERY = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.ordinal_position,
    CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
    CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END as is_foreign_key
FROM information_schema.columns c
LEFT JOIN (
    SELECT kcu.table_schema, kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
) pk ON c.table_schema = pk.table_schema
    AND c.table_name = pk.table_name
    AND c.column_name = pk.column_name
LEFT JOIN (
    SELECT kcu.table_schema, kcu.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
) fk ON c.table_schema = fk.table_schema
    AND c.table_name = fk.table_name
    AND c.column_name = fk.column_name
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""


class MetadataExtractor:
    """Service for extracting metadata from PostgreSQL databases."""

    @staticmethod
    async def extract(connection_url: str) -> tuple[list[TableInfo], list[TableInfo]]:
        """Extract metadata from a PostgreSQL database.

        Args:
            connection_url: PostgreSQL connection URL

        Returns:
            Tuple of (tables, views) with their column information

        Raises:
            ConnectionError: If unable to connect to database
            Exception: For other database errors
        """
        try:
            async with await psycopg.AsyncConnection.connect(connection_url) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    # Get tables and views
                    await cur.execute(TABLES_QUERY)
                    table_rows = await cur.fetchall()

                    # Get columns
                    await cur.execute(COLUMNS_QUERY)
                    column_rows = await cur.fetchall()

        except psycopg.OperationalError as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e

        # Organize into hierarchical structure
        tables: list[TableInfo] = []
        views: list[TableInfo] = []
        table_map: dict[tuple[str, str], TableInfo] = {}

        # Create table/view entries
        for row in table_rows:
            table_type = "VIEW" if row["table_type"] == "VIEW" else "TABLE"
            table_info = TableInfo(
                schema_name=row["table_schema"],
                name=row["table_name"],
                type=table_type,
                columns=[],
            )
            key = (row["table_schema"], row["table_name"])
            table_map[key] = table_info

            if table_type == "VIEW":
                views.append(table_info)
            else:
                tables.append(table_info)

        # Add columns to tables/views
        for row in column_rows:
            key = (row["table_schema"], row["table_name"])
            if key in table_map:
                column = ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=row["is_nullable"] == "YES",
                    default_value=row["column_default"],
                    is_primary_key=row["is_primary_key"],
                    is_foreign_key=row["is_foreign_key"],
                )
                table_map[key].columns.append(column)

        return tables, views

    @staticmethod
    async def test_connection(connection_url: str) -> bool:
        """Test if connection to database is successful.

        Args:
            connection_url: PostgreSQL connection URL

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If unable to connect
        """
        try:
            async with await psycopg.AsyncConnection.connect(connection_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    return True
        except psycopg.OperationalError as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e
