"""SQLite storage implementation for connections and metadata cache."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from src.models.database import ColumnInfo, DatabaseInfo, DatabaseMetadata, DbType, TableInfo
from src.utils.db_utils import detect_db_type, mask_password


class SQLiteStorage:
    """SQLite storage for database connections and metadata cache."""

    def __init__(self, db_path: Path) -> None:
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_tables()

    def _ensure_db_dir(self) -> None:
        """Ensure the parent directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    name TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    db_type TEXT NOT NULL DEFAULT 'postgresql',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata_cached_at TEXT
                )
            """)
            # Migration: add missing columns if they don't exist
            cursor = conn.execute("PRAGMA table_info(connections)")
            columns = [row[1] for row in cursor.fetchall()]
            if "metadata_cached_at" not in columns:
                conn.execute("ALTER TABLE connections ADD COLUMN metadata_cached_at TEXT")
            if "db_type" not in columns:
                conn.execute(
                    "ALTER TABLE connections ADD COLUMN db_type TEXT NOT NULL DEFAULT 'postgresql'"
                )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    connection_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    table_type TEXT NOT NULL CHECK (table_type IN ('TABLE', 'VIEW')),
                    columns_json TEXT NOT NULL,
                    cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (connection_name, schema_name, table_name),
                    FOREIGN KEY (connection_name) REFERENCES connections(name) ON DELETE CASCADE
                )
            """)

    # Connection CRUD operations

    def list_connections(self) -> list[DatabaseInfo]:
        """List all database connections."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, url, db_type, created_at, updated_at FROM connections ORDER BY name"
            )
            rows = cursor.fetchall()
            return [
                DatabaseInfo(
                    name=row["name"],
                    url=mask_password(row["url"]),
                    db_type=row["db_type"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    def get_connection(self, name: str) -> dict[str, Any] | None:
        """Get a connection by name (includes full URL with password)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, url, db_type, created_at, updated_at, metadata_cached_at FROM connections WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "name": row["name"],
                "url": row["url"],
                "db_type": row["db_type"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata_cached_at": row["metadata_cached_at"],
            }

    def upsert_connection(self, name: str, url: str, db_type: DbType | None = None) -> None:
        """Insert or update a database connection.

        Args:
            name: Connection name
            url: Database connection URL
            db_type: Database type (auto-detected from URL if not provided)
        """
        now = datetime.now(timezone.utc).isoformat()
        if db_type is None:
            db_type = detect_db_type(url)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO connections (name, url, db_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET url = ?, db_type = ?, updated_at = ?
                """,
                (name, url, db_type, now, now, url, db_type, now),
            )

    def delete_connection(self, name: str) -> bool:
        """Delete a connection and its cached metadata."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM connections WHERE name = ?", (name,))
            return cursor.rowcount > 0

    # Metadata cache operations

    def get_metadata(self, connection_name: str) -> DatabaseMetadata | None:
        """Get cached metadata for a connection.

        Returns None only if metadata has never been cached.
        Returns empty DatabaseMetadata if metadata was cached but database has no tables/views.
        """
        conn_data = self.get_connection(connection_name)
        if conn_data is None:
            return None

        # Check if metadata has ever been cached
        metadata_cached_at = conn_data.get("metadata_cached_at")
        if metadata_cached_at is None:
            return None

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT schema_name, table_name, table_type, columns_json, cached_at
                FROM metadata_cache
                WHERE connection_name = ?
                ORDER BY schema_name, table_name
                """,
                (connection_name,),
            )
            rows = cursor.fetchall()

        # If no tables/views but metadata was cached, return empty metadata
        if not rows:
            return DatabaseMetadata(
                name=connection_name,
                url=mask_password(conn_data["url"]),
                db_type=conn_data["db_type"],
                tables=[],
                views=[],
                cached_at=datetime.fromisoformat(metadata_cached_at),
            )

        tables: list[TableInfo] = []
        views: list[TableInfo] = []
        cached_at = None

        for row in rows:
            columns_data = json.loads(row["columns_json"])
            columns = [ColumnInfo(**col) for col in columns_data]

            table_info = TableInfo(
                schema_name=row["schema_name"],
                name=row["table_name"],
                type=row["table_type"],
                columns=columns,
            )

            if row["table_type"] == "VIEW":
                views.append(table_info)
            else:
                tables.append(table_info)

            if cached_at is None:
                cached_at = datetime.fromisoformat(row["cached_at"])

        return DatabaseMetadata(
            name=connection_name,
            url=mask_password(conn_data["url"]),
            db_type=conn_data["db_type"],
            tables=tables,
            views=views,
            cached_at=cached_at or datetime.now(timezone.utc),
        )

    def save_metadata(
        self, connection_name: str, tables: list[TableInfo], views: list[TableInfo]
    ) -> None:
        """Save metadata cache for a connection."""
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Clear existing metadata
            conn.execute(
                "DELETE FROM metadata_cache WHERE connection_name = ?", (connection_name,)
            )

            # Update the metadata_cached_at timestamp on the connection
            conn.execute(
                "UPDATE connections SET metadata_cached_at = ? WHERE name = ?",
                (now, connection_name),
            )

            # Insert new metadata
            for table in tables + views:
                columns_json = json.dumps(
                    [col.model_dump(by_alias=True) for col in table.columns]
                )
                conn.execute(
                    """
                    INSERT INTO metadata_cache
                    (connection_name, schema_name, table_name, table_type, columns_json, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        connection_name,
                        table.schema_name,
                        table.name,
                        table.type,
                        columns_json,
                        now,
                    ),
                )

    def clear_metadata(self, connection_name: str) -> None:
        """Clear cached metadata for a connection."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM metadata_cache WHERE connection_name = ?", (connection_name,)
            )
            # Reset the metadata_cached_at timestamp
            conn.execute(
                "UPDATE connections SET metadata_cached_at = NULL WHERE name = ?",
                (connection_name,),
            )

    # Backward compatibility: expose mask_password as static method
    # New code should import from src.utils.db_utils directly
    _mask_password = staticmethod(mask_password)
