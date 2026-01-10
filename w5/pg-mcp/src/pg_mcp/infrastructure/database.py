import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import structlog

from pg_mcp.config.models import DatabaseConfig, SSLMode
from pg_mcp.models.errors import DatabaseConnectionError

logger = structlog.get_logger(__name__)


def create_ssl_context(
    ssl_mode: SSLMode,
    verify_cert: bool = True,
    ca_file: str | None = None,
) -> ssl.SSLContext | bool:
    """根据 SSL 模式创建 SSL 上下文

    Args:
        ssl_mode: SSL 模式配置
        verify_cert: 是否验证证书 (仅对 REQUIRE 模式有效)
        ca_file: CA 证书文件路径 (可选)

    Returns:
        SSL 上下文或布尔值
    """
    if ssl_mode in (SSLMode.DISABLE, SSLMode.ALLOW):
        return False

    if ssl_mode == SSLMode.PREFER:
        # PREFER 模式: 尝试 SSL 但不验证证书
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if ssl_mode == SSLMode.REQUIRE:
        # REQUIRE 模式: 强制 SSL，默认验证证书
        ctx = ssl.create_default_context(cafile=ca_file)
        if verify_cert:
            # 保持默认的证书验证
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            # 如果明确禁用验证（不推荐）
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    return False


class DatabasePool:
    """数据库连接池封装"""

    def __init__(self, config: DatabaseConfig):
        """初始化连接池

        Args:
            config: 数据库配置
        """
        self.config = config
        self._pool: asyncpg.Pool | None = None
        self._logger = logger.bind(database=config.name)

    @property
    def is_connected(self) -> bool:
        """检查连接池是否已初始化"""
        return self._pool is not None

    async def connect(self) -> None:
        """初始化连接池"""
        if self._pool is not None:
            return

        try:
            ssl_context = create_ssl_context(
                self.config.ssl_mode,
                verify_cert=self.config.ssl_verify_cert,
                ca_file=self.config.ssl_ca_file,
            )
            self._pool = await asyncpg.create_pool(
                dsn=self.config.get_dsn(),
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                ssl=ssl_context,
                command_timeout=60.0,
            )
            self._logger.info("Database pool created",
                            min_size=self.config.min_pool_size,
                            max_size=self.config.max_pool_size)
        except Exception as e:
            self._logger.error("Failed to create database pool", error=str(e))
            raise DatabaseConnectionError(self.config.name, str(e)) from e

    async def disconnect(self) -> None:
        """关闭连接池"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._logger.info("Database pool closed")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection]:
        """获取数据库连接

        Yields:
            数据库连接

        Raises:
            DatabaseConnectionError: 连接池未初始化
        """
        if self._pool is None:
            raise DatabaseConnectionError(self.config.name, "Connection pool not initialized")

        async with self._pool.acquire() as conn:
            yield conn

    async def fetch(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        """执行查询并返回结果

        Args:
            query: SQL 查询
            *args: 查询参数
            timeout: 超时时间（秒）

        Returns:
            查询结果列表
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetch_readonly(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> list[asyncpg.Record]:
        """在只读事务中执行查询（深度防御）

        Args:
            query: SQL 查询
            *args: 查询参数
            timeout: 超时时间（秒）

        Returns:
            查询结果列表
        """
        async with self.acquire() as conn, conn.transaction(readonly=True):
            # 设置服务端语句超时
            if timeout:
                await conn.execute(
                    f"SET LOCAL statement_timeout = '{int(timeout * 1000)}'"
                )
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchrow(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> asyncpg.Record | None:
        """执行查询并返回单行结果

        Args:
            query: SQL 查询
            *args: 查询参数
            timeout: 超时时间（秒）

        Returns:
            单行结果或 None
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def execute(
        self,
        query: str,
        *args: Any,
        timeout: float | None = None,
    ) -> str:
        """执行 SQL 语句

        Args:
            query: SQL 语句
            *args: 查询参数
            timeout: 超时时间（秒）

        Returns:
            执行状态
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            True 如果连接正常
        """
        try:
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            self._logger.warning("Health check failed", error=str(e))
            return False


class DatabasePoolManager:
    """多数据库连接池管理器"""

    def __init__(self) -> None:
        """初始化管理器"""
        self._pools: dict[str, DatabasePool] = {}
        self._logger = logger

    async def add_database(self, config: DatabaseConfig) -> None:
        """添加数据库连接池

        Args:
            config: 数据库配置
        """
        if config.name in self._pools:
            self._logger.warning("Database pool already exists", database=config.name)
            return

        pool = DatabasePool(config)
        await pool.connect()
        self._pools[config.name] = pool
        self._logger.info("Database pool added", database=config.name)

    def get_pool(self, name: str) -> DatabasePool:
        """获取指定数据库的连接池

        Args:
            name: 数据库名称

        Returns:
            数据库连接池

        Raises:
            KeyError: 数据库不存在
        """
        if name not in self._pools:
            raise KeyError(f"Database '{name}' not found")
        return self._pools[name]

    def has_pool(self, name: str) -> bool:
        """检查数据库连接池是否存在

        Args:
            name: 数据库名称

        Returns:
            是否存在
        """
        return name in self._pools

    @property
    def database_names(self) -> list[str]:
        """获取所有数据库名称"""
        return list(self._pools.keys())

    async def close_all(self) -> None:
        """关闭所有连接池"""
        for name, pool in self._pools.items():
            await pool.disconnect()
            self._logger.info("Database pool closed", database=name)
        self._pools.clear()

    async def health_check_all(self) -> dict[str, bool]:
        """检查所有数据库健康状态

        Returns:
            数据库名称到健康状态的映射
        """
        results = {}
        for name, pool in self._pools.items():
            results[name] = await pool.health_check()
        return results
