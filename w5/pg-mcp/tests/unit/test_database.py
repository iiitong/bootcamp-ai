# tests/unit/test_database.py

"""Database connection pool unit tests."""

import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.config.models import DatabaseConfig, SSLMode
from pg_mcp.infrastructure.database import (
    DatabasePool,
    DatabasePoolManager,
    create_ssl_context,
)
from pg_mcp.models.errors import DatabaseConnectionError


class TestCreateSSLContext:
    """SSL context creation tests."""

    def test_ssl_disable_returns_false(self):
        """Test DISABLE mode returns False."""
        result = create_ssl_context(SSLMode.DISABLE)
        assert result is False

    def test_ssl_allow_returns_false(self):
        """Test ALLOW mode returns False."""
        result = create_ssl_context(SSLMode.ALLOW)
        assert result is False

    def test_ssl_prefer_returns_context(self):
        """Test PREFER mode returns SSLContext with no verification."""
        result = create_ssl_context(SSLMode.PREFER)

        assert isinstance(result, ssl.SSLContext)
        assert result.check_hostname is False
        assert result.verify_mode == ssl.CERT_NONE

    def test_ssl_require_returns_context_with_verification(self):
        """Test REQUIRE mode returns SSLContext with verification."""
        result = create_ssl_context(SSLMode.REQUIRE, verify_cert=True)

        assert isinstance(result, ssl.SSLContext)
        assert result.check_hostname is True
        assert result.verify_mode == ssl.CERT_REQUIRED

    def test_ssl_require_without_verification(self):
        """Test REQUIRE mode without certificate verification."""
        result = create_ssl_context(SSLMode.REQUIRE, verify_cert=False)

        assert isinstance(result, ssl.SSLContext)
        assert result.check_hostname is False
        assert result.verify_mode == ssl.CERT_NONE


class TestDatabasePool:
    """Database connection pool tests."""

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config."""
        return DatabaseConfig(
            name="test_db",
            host="localhost",
            port=5432,
            dbname="testdb",
            user="testuser",
            password="testpass",
            ssl_mode=SSLMode.DISABLE,
            min_pool_size=2,
            max_pool_size=5,
        )

    def test_pool_initialization(self, db_config):
        """Test pool initializes with correct config."""
        pool = DatabasePool(db_config)

        assert pool.config == db_config
        assert pool.is_connected is False
        assert pool._pool is None

    @pytest.mark.asyncio
    async def test_pool_connect_success(self, db_config):
        """Test successful pool connection."""
        pool = DatabasePool(db_config)

        with patch(
            "pg_mcp.infrastructure.database.asyncpg.create_pool",
            new_callable=AsyncMock
        ) as mock_create:
            mock_pool = MagicMock()
            mock_create.return_value = mock_pool

            await pool.connect()

            assert pool.is_connected is True
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_connect_already_connected(self, db_config):
        """Test connect when already connected does nothing."""
        pool = DatabasePool(db_config)
        pool._pool = MagicMock()

        with patch("pg_mcp.infrastructure.database.asyncpg.create_pool") as mock_create:
            await pool.connect()

            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_pool_connect_failure(self, db_config):
        """Test connection failure raises DatabaseConnectionError."""
        pool = DatabasePool(db_config)

        with patch("pg_mcp.infrastructure.database.asyncpg.create_pool") as mock_create:
            mock_create.side_effect = Exception("Connection refused")

            with pytest.raises(DatabaseConnectionError) as exc_info:
                await pool.connect()

            assert "test_db" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pool_disconnect(self, db_config):
        """Test pool disconnection."""
        pool = DatabasePool(db_config)
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        pool._pool = mock_pool

        await pool.disconnect()

        mock_pool.close.assert_called_once()
        assert pool._pool is None
        assert pool.is_connected is False

    @pytest.mark.asyncio
    async def test_pool_disconnect_when_not_connected(self, db_config):
        """Test disconnect when not connected does nothing."""
        pool = DatabasePool(db_config)

        await pool.disconnect()

        assert pool._pool is None

    @pytest.mark.asyncio
    async def test_pool_acquire_not_initialized(self, db_config):
        """Test acquire raises error when pool not initialized."""
        pool = DatabasePool(db_config)

        with pytest.raises(DatabaseConnectionError) as exc_info:
            async with pool.acquire():
                pass

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pool_acquire_success(self, db_config):
        """Test successful connection acquisition."""
        pool = DatabasePool(db_config)

        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        async with pool.acquire() as conn:
            assert conn == mock_conn

    @pytest.mark.asyncio
    async def test_pool_fetch(self, db_config):
        """Test fetch query execution."""
        pool = DatabasePool(db_config)

        mock_record = {"id": 1, "name": "test"}
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_record])

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        result = await pool.fetch("SELECT * FROM test")

        assert result == [mock_record]
        mock_conn.fetch.assert_called_once_with(
            "SELECT * FROM test", timeout=None
        )

    @pytest.mark.asyncio
    async def test_pool_fetch_readonly(self, db_config):
        """Test fetch_readonly executes in read-only transaction."""
        pool = DatabasePool(db_config)

        mock_record = {"id": 1}
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_record])
        mock_conn.execute = AsyncMock()

        # Mock transaction context manager
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=None)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=mock_transaction)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        result = await pool.fetch_readonly("SELECT 1", timeout=5.0)

        assert result == [mock_record]
        mock_conn.transaction.assert_called_once_with(readonly=True)
        mock_conn.execute.assert_called_once()  # SET LOCAL statement_timeout

    @pytest.mark.asyncio
    async def test_pool_fetchrow(self, db_config):
        """Test fetchrow returns single row."""
        pool = DatabasePool(db_config)

        mock_record = {"id": 1, "name": "test"}
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_record)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        result = await pool.fetchrow("SELECT * FROM test WHERE id = 1")

        assert result == mock_record

    @pytest.mark.asyncio
    async def test_pool_execute(self, db_config):
        """Test execute returns status."""
        pool = DatabasePool(db_config)

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        result = await pool.execute("INSERT INTO test VALUES (1)")

        assert result == "INSERT 0 1"

    @pytest.mark.asyncio
    async def test_pool_health_check_success(self, db_config):
        """Test successful health check."""
        pool = DatabasePool(db_config)

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        pool._pool = mock_pool

        result = await pool.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_pool_health_check_failure(self, db_config):
        """Test failed health check."""
        pool = DatabasePool(db_config)

        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection error")
        )
        pool._pool = mock_pool

        result = await pool.health_check()

        assert result is False


class TestDatabasePoolManager:
    """Database pool manager tests."""

    @pytest.fixture
    def configs(self) -> list[DatabaseConfig]:
        """Create test database configs."""
        return [
            DatabaseConfig(
                name="db1",
                host="localhost",
                dbname="db1",
                user="user",
                ssl_mode=SSLMode.DISABLE,
            ),
            DatabaseConfig(
                name="db2",
                host="localhost",
                dbname="db2",
                user="user",
                ssl_mode=SSLMode.DISABLE,
            ),
        ]

    def test_manager_initialization(self):
        """Test manager initializes empty."""
        manager = DatabasePoolManager()

        assert manager.database_names == []

    @pytest.mark.asyncio
    async def test_manager_add_database(self, configs):
        """Test adding database to manager."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])

        assert "db1" in manager.database_names
        assert manager.has_pool("db1")

    @pytest.mark.asyncio
    async def test_manager_add_duplicate_database(self, configs):
        """Test adding duplicate database is ignored."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock) as mock_connect:
            await manager.add_database(configs[0])
            await manager.add_database(configs[0])

            # Should only connect once
            assert mock_connect.call_count == 1

    @pytest.mark.asyncio
    async def test_manager_get_pool(self, configs):
        """Test getting pool from manager."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])

        pool = manager.get_pool("db1")
        assert pool is not None
        assert pool.config.name == "db1"

    def test_manager_get_pool_not_found(self):
        """Test getting non-existent pool raises KeyError."""
        manager = DatabasePoolManager()

        with pytest.raises(KeyError) as exc_info:
            manager.get_pool("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manager_has_pool(self, configs):
        """Test has_pool check."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])

        assert manager.has_pool("db1") is True
        assert manager.has_pool("nonexistent") is False

    @pytest.mark.asyncio
    async def test_manager_database_names(self, configs):
        """Test database_names property."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])
            await manager.add_database(configs[1])

        names = manager.database_names
        assert "db1" in names
        assert "db2" in names
        assert len(names) == 2

    @pytest.mark.asyncio
    async def test_manager_close_all(self, configs):
        """Test closing all pools."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])
            await manager.add_database(configs[1])

        with patch.object(DatabasePool, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            await manager.close_all()

            assert mock_disconnect.call_count == 2

        assert manager.database_names == []

    @pytest.mark.asyncio
    async def test_manager_health_check_all(self, configs):
        """Test health check for all pools."""
        manager = DatabasePoolManager()

        with patch.object(DatabasePool, "connect", new_callable=AsyncMock):
            await manager.add_database(configs[0])
            await manager.add_database(configs[1])

        with patch.object(DatabasePool, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            results = await manager.health_check_all()

            assert results == {"db1": True, "db2": True}
            assert mock_health.call_count == 2
