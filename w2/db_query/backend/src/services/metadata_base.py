"""Shared metadata extraction utilities.

This module provides common functionality for organizing database metadata
across different database types (PostgreSQL, MySQL, etc.).
"""

from typing import Any

from src.models.database import ColumnInfo, TableInfo


def get_row_value(row: dict[str, Any], key: str) -> Any:
    """Get a value from a row dict, trying both lowercase and uppercase keys.

    MySQL information_schema returns UPPERCASE column names, while PostgreSQL
    uses lowercase. This helper normalizes the access.

    Args:
        row: Row dictionary from database cursor
        key: Column name (in lowercase)

    Returns:
        Value from the row, or None if not found
    """
    return row.get(key) or row.get(key.upper())


def build_table_hierarchy(
    table_rows: list[dict[str, Any]],
    column_rows: list[dict[str, Any]],
) -> tuple[list[TableInfo], list[TableInfo]]:
    """Build table hierarchy from raw database rows.

    Consolidates the shared logic between PostgreSQL and MySQL metadata extractors.
    Handles both lowercase (PostgreSQL) and UPPERCASE (MySQL) column names.

    Args:
        table_rows: Rows from information_schema.tables query
        column_rows: Rows from information_schema.columns query

    Returns:
        Tuple of (tables, views) with their column information
    """
    tables: list[TableInfo] = []
    views: list[TableInfo] = []
    table_map: dict[tuple[str, str], TableInfo] = {}

    # Create table/view entries
    for row in table_rows:
        schema = get_row_value(row, "table_schema")
        name = get_row_value(row, "table_name")
        ttype = get_row_value(row, "table_type")

        table_type: str = "VIEW" if ttype == "VIEW" else "TABLE"
        table_info = TableInfo(
            schema_name=schema,
            name=name,
            type=table_type,  # type: ignore[arg-type]
            columns=[],
        )
        key = (schema, name)
        table_map[key] = table_info

        if table_type == "VIEW":
            views.append(table_info)
        else:
            tables.append(table_info)

    # Add columns to tables/views
    for row in column_rows:
        schema = get_row_value(row, "table_schema")
        name = get_row_value(row, "table_name")
        key = (schema, name)

        if key in table_map:
            # Handle boolean values - PostgreSQL returns bool, MySQL returns 1/0
            is_pk = get_row_value(row, "is_primary_key")
            is_fk = get_row_value(row, "is_foreign_key")

            column = ColumnInfo(
                name=get_row_value(row, "column_name"),
                data_type=get_row_value(row, "data_type"),
                nullable=get_row_value(row, "is_nullable") == "YES",
                default_value=get_row_value(row, "column_default"),
                is_primary_key=bool(is_pk),
                is_foreign_key=bool(is_fk),
            )
            table_map[key].columns.append(column)

    return tables, views
