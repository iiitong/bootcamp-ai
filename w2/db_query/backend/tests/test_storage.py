"""Tests for SQLite storage layer."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models.database import ColumnInfo, TableInfo
from src.storage.sqlite import SQLiteStorage


@pytest.fixture
def storage() -> SQLiteStorage:
    """Create a temporary SQLite storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield SQLiteStorage(db_path)


class TestSQLiteStorage:
    """Tests for SQLiteStorage class."""

    def test_list_connections_empty(self, storage: SQLiteStorage) -> None:
        """List connections should return empty list initially."""
        connections = storage.list_connections()
        assert connections == []

    def test_upsert_and_get_connection(self, storage: SQLiteStorage) -> None:
        """Should be able to create and retrieve a connection."""
        storage.upsert_connection("testdb", "postgresql://user:pass@localhost:5432/db")

        conn = storage.get_connection("testdb")
        assert conn is not None
        assert conn["name"] == "testdb"
        assert conn["url"] == "postgresql://user:pass@localhost:5432/db"

    def test_list_connections_after_insert(self, storage: SQLiteStorage) -> None:
        """List connections should return inserted connections."""
        storage.upsert_connection("db1", "postgresql://localhost/db1")
        storage.upsert_connection("db2", "postgresql://localhost/db2")

        connections = storage.list_connections()
        assert len(connections) == 2
        names = [c.name for c in connections]
        assert "db1" in names
        assert "db2" in names

    def test_upsert_updates_existing(self, storage: SQLiteStorage) -> None:
        """Upsert should update existing connection."""
        storage.upsert_connection("testdb", "postgresql://localhost/old")
        storage.upsert_connection("testdb", "postgresql://localhost/new")

        conn = storage.get_connection("testdb")
        assert conn is not None
        assert conn["url"] == "postgresql://localhost/new"

        # Should still only have one connection
        connections = storage.list_connections()
        assert len(connections) == 1

    def test_delete_connection(self, storage: SQLiteStorage) -> None:
        """Should be able to delete a connection."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")

        result = storage.delete_connection("testdb")
        assert result is True

        conn = storage.get_connection("testdb")
        assert conn is None

    def test_delete_nonexistent_connection(self, storage: SQLiteStorage) -> None:
        """Deleting nonexistent connection should return False."""
        result = storage.delete_connection("nonexistent")
        assert result is False

    def test_get_nonexistent_connection(self, storage: SQLiteStorage) -> None:
        """Getting nonexistent connection should return None."""
        conn = storage.get_connection("nonexistent")
        assert conn is None

    def test_password_masking(self, storage: SQLiteStorage) -> None:
        """Passwords should be masked in list output."""
        storage.upsert_connection("testdb", "postgresql://user:secret@localhost:5432/db")

        connections = storage.list_connections()
        assert len(connections) == 1
        assert "***" in connections[0].url
        assert "secret" not in connections[0].url

    def test_password_masking_static(self) -> None:
        """Test static password masking method."""
        # With password
        url = "postgresql://user:password@localhost:5432/db"
        masked = SQLiteStorage._mask_password(url)
        assert masked == "postgresql://user:***@localhost:5432/db"

        # Without password
        url = "postgresql://localhost:5432/db"
        masked = SQLiteStorage._mask_password(url)
        assert masked == url

    def test_save_and_get_metadata(self, storage: SQLiteStorage) -> None:
        """Should be able to save and retrieve metadata."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")

        tables = [
            TableInfo(
                schema_name="public",
                name="users",
                type="TABLE",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="email",
                        data_type="varchar",
                        nullable=False,
                    ),
                ],
            )
        ]
        views = [
            TableInfo(
                schema_name="public",
                name="active_users",
                type="VIEW",
                columns=[
                    ColumnInfo(name="id", data_type="integer", nullable=False),
                ],
            )
        ]

        storage.save_metadata("testdb", tables, views)

        metadata = storage.get_metadata("testdb")
        assert metadata is not None
        assert metadata.name == "testdb"
        assert len(metadata.tables) == 1
        assert len(metadata.views) == 1
        assert metadata.tables[0].name == "users"
        assert metadata.views[0].name == "active_users"
        assert len(metadata.tables[0].columns) == 2

    def test_get_metadata_nonexistent(self, storage: SQLiteStorage) -> None:
        """Getting metadata for nonexistent connection should return None."""
        metadata = storage.get_metadata("nonexistent")
        assert metadata is None

    def test_clear_metadata(self, storage: SQLiteStorage) -> None:
        """Should be able to clear metadata."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")
        tables = [
            TableInfo(
                schema_name="public",
                name="users",
                type="TABLE",
                columns=[],
            )
        ]
        storage.save_metadata("testdb", tables, [])

        storage.clear_metadata("testdb")

        metadata = storage.get_metadata("testdb")
        assert metadata is None

    def test_delete_connection_cascades_metadata(self, storage: SQLiteStorage) -> None:
        """Deleting connection should cascade delete metadata."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")
        tables = [
            TableInfo(
                schema_name="public",
                name="users",
                type="TABLE",
                columns=[],
            )
        ]
        storage.save_metadata("testdb", tables, [])

        storage.delete_connection("testdb")

        metadata = storage.get_metadata("testdb")
        assert metadata is None

    def test_column_info_serialization(self, storage: SQLiteStorage) -> None:
        """Column info should serialize and deserialize correctly."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")

        tables = [
            TableInfo(
                schema_name="public",
                name="users",
                type="TABLE",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        nullable=False,
                        default_value="nextval('users_id_seq')",
                        is_primary_key=True,
                        is_foreign_key=False,
                    ),
                ],
            )
        ]

        storage.save_metadata("testdb", tables, [])

        metadata = storage.get_metadata("testdb")
        assert metadata is not None
        col = metadata.tables[0].columns[0]
        assert col.name == "id"
        assert col.data_type == "integer"
        assert col.nullable is False
        assert col.default_value == "nextval('users_id_seq')"
        assert col.is_primary_key is True
        assert col.is_foreign_key is False

    def test_get_metadata_empty_database(self, storage: SQLiteStorage) -> None:
        """Getting metadata for empty database should return empty lists, not None."""
        storage.upsert_connection("emptydb", "postgresql://localhost/empty")

        # Before saving metadata, should return None
        metadata = storage.get_metadata("emptydb")
        assert metadata is None

        # Save empty metadata (empty database with no tables/views)
        storage.save_metadata("emptydb", [], [])

        # After saving, should return empty DatabaseMetadata (not None)
        metadata = storage.get_metadata("emptydb")
        assert metadata is not None
        assert metadata.name == "emptydb"
        assert metadata.tables == []
        assert metadata.views == []
        assert metadata.cached_at is not None

    def test_get_metadata_not_cached_vs_empty(self, storage: SQLiteStorage) -> None:
        """Distinguish between 'never cached' and 'cached but empty'."""
        storage.upsert_connection("testdb", "postgresql://localhost/db")

        # Never cached: should return None
        assert storage.get_metadata("testdb") is None

        # Cache empty metadata
        storage.save_metadata("testdb", [], [])

        # Cached but empty: should return DatabaseMetadata with empty lists
        metadata = storage.get_metadata("testdb")
        assert metadata is not None
        assert metadata.tables == []
        assert metadata.views == []

        # Clear metadata: should return None again (reset to "never cached")
        storage.clear_metadata("testdb")
        assert storage.get_metadata("testdb") is None
