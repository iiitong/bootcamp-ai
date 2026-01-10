import asyncio
import re
import time
from typing import TYPE_CHECKING

import structlog

from pg_mcp.models.schema import (
    ColumnInfo,
    DatabaseSchema,
    EnumTypeInfo,
    IndexInfo,
    IndexType,
    TableInfo,
    ViewInfo,
)

if TYPE_CHECKING:
    from pg_mcp.infrastructure.database import DatabasePool

logger = structlog.get_logger(__name__)

# 预编译正则表达式
INDEX_COLUMNS_PATTERN = re.compile(r'\(([^)]+)\)')


# Schema 查询 SQL
TABLES_QUERY = """
SELECT
    t.table_schema,
    t.table_name,
    obj_description((t.table_schema || '.' || t.table_name)::regclass) as table_comment
FROM information_schema.tables t
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
    AND t.table_type = 'BASE TABLE'
ORDER BY t.table_schema, t.table_name
"""

COLUMNS_QUERY = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.udt_name,
    col_description(
        (c.table_schema || '.' || c.table_name)::regclass,
        c.ordinal_position
    ) as column_comment
FROM information_schema.columns c
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""

PRIMARY_KEYS_QUERY = """
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
"""

FOREIGN_KEYS_QUERY = """
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
"""

UNIQUE_CONSTRAINTS_QUERY = """
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE'
    AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
"""

INDEXES_QUERY = """
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
"""

VIEWS_QUERY = """
SELECT
    v.table_schema,
    v.table_name,
    v.view_definition
FROM information_schema.views v
WHERE v.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY v.table_schema, v.table_name
"""

ENUMS_QUERY = """
SELECT
    n.nspname as schema_name,
    t.typname as type_name,
    array_agg(e.enumlabel ORDER BY e.enumsortorder) as enum_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
JOIN pg_namespace n ON t.typnamespace = n.oid
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
GROUP BY n.nspname, t.typname
ORDER BY n.nspname, t.typname
"""


class SchemaCache:
    """Schema 缓存管理器"""

    def __init__(self, refresh_interval: int = 3600) -> None:
        """初始化缓存

        Args:
            refresh_interval: 缓存刷新间隔（秒）
        """
        self._cache: dict[str, DatabaseSchema] = {}
        self._refresh_interval = refresh_interval
        self._lock = asyncio.Lock()
        self._logger = logger

    def get(self, database: str) -> DatabaseSchema | None:
        """获取缓存的 Schema

        Args:
            database: 数据库名称

        Returns:
            缓存的 Schema 或 None
        """
        schema = self._cache.get(database)
        if schema and self._is_valid(schema):
            return schema
        return None

    def _is_valid(self, schema: DatabaseSchema) -> bool:
        """检查缓存是否有效

        Args:
            schema: 缓存的 Schema

        Returns:
            是否有效
        """
        if schema.cached_at is None:
            return False
        return (time.time() - schema.cached_at) < self._refresh_interval

    async def refresh(self, database: str, pool: "DatabasePool") -> DatabaseSchema:
        """刷新指定数据库的 Schema 缓存

        Args:
            database: 数据库名称
            pool: 数据库连接池

        Returns:
            刷新后的 Schema
        """
        async with self._lock:
            self._logger.info("Refreshing schema cache", database=database)

            schema = await self._load_schema(database, pool)
            self._cache[database] = schema

            self._logger.info(
                "Schema cache refreshed",
                database=database,
                tables=schema.tables_count,
                views=schema.views_count,
            )

            return schema

    async def get_or_refresh(
        self, database: str, pool: "DatabasePool"
    ) -> DatabaseSchema:
        """获取 Schema，如果缓存无效则刷新

        Args:
            database: 数据库名称
            pool: 数据库连接池

        Returns:
            Schema
        """
        cached = self.get(database)
        if cached:
            return cached
        return await self.refresh(database, pool)

    async def _load_schema(
        self, database: str, pool: "DatabasePool"
    ) -> DatabaseSchema:
        """从数据库加载 Schema

        Args:
            database: 数据库名称
            pool: 数据库连接池

        Returns:
            加载的 Schema
        """
        # 并行执行所有查询
        tables_task = pool.fetch(TABLES_QUERY)
        columns_task = pool.fetch(COLUMNS_QUERY)
        pk_task = pool.fetch(PRIMARY_KEYS_QUERY)
        fk_task = pool.fetch(FOREIGN_KEYS_QUERY)
        unique_task = pool.fetch(UNIQUE_CONSTRAINTS_QUERY)
        indexes_task = pool.fetch(INDEXES_QUERY)
        views_task = pool.fetch(VIEWS_QUERY)
        enums_task = pool.fetch(ENUMS_QUERY)

        (
            tables_rows,
            columns_rows,
            pk_rows,
            fk_rows,
            unique_rows,
            indexes_rows,
            views_rows,
            enums_rows,
        ) = await asyncio.gather(
            tables_task,
            columns_task,
            pk_task,
            fk_task,
            unique_task,
            indexes_task,
            views_task,
            enums_task,
        )

        # 构建主键集合
        primary_keys: set[tuple[str, str, str]] = {
            (row["table_schema"], row["table_name"], row["column_name"])
            for row in pk_rows
        }

        # 构建外键映射
        foreign_keys: dict[tuple[str, str, str], tuple[str, str]] = {
            (row["table_schema"], row["table_name"], row["column_name"]): (
                f"{row['foreign_table_schema']}.{row['foreign_table_name']}"
                if row["foreign_table_schema"] != "public"
                else row["foreign_table_name"],
                row["foreign_column_name"],
            )
            for row in fk_rows
        }

        # 构建唯一约束集合
        unique_columns: set[tuple[str, str, str]] = {
            (row["table_schema"], row["table_name"], row["column_name"])
            for row in unique_rows
        }

        # 构建列信息映射
        columns_map: dict[tuple[str, str], list[ColumnInfo]] = {}
        for row in columns_rows:
            key = (row["table_schema"], row["table_name"])
            col_key = (row["table_schema"], row["table_name"], row["column_name"])

            fk = foreign_keys.get(col_key)
            column = ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"] == "YES",
                is_primary_key=col_key in primary_keys,
                is_unique=col_key in unique_columns,
                default_value=row["column_default"],
                comment=row["column_comment"],
                foreign_key_table=fk[0] if fk else None,
                foreign_key_column=fk[1] if fk else None,
            )

            if key not in columns_map:
                columns_map[key] = []
            columns_map[key].append(column)

        # 构建索引映射
        indexes_map: dict[tuple[str, str], list[IndexInfo]] = {}
        for row in indexes_rows:
            key = (row["schemaname"], row["tablename"])
            indexdef = row["indexdef"].lower()

            # 解析索引类型
            index_type = IndexType.BTREE
            if "using hash" in indexdef:
                index_type = IndexType.HASH
            elif "using gin" in indexdef:
                index_type = IndexType.GIN
            elif "using gist" in indexdef:
                index_type = IndexType.GIST
            elif "using brin" in indexdef:
                index_type = IndexType.BRIN

            # 解析索引列（使用预编译正则）
            columns_match = INDEX_COLUMNS_PATTERN.search(row["indexdef"])
            columns = []
            if columns_match:
                columns = [c.strip() for c in columns_match.group(1).split(",")]

            index = IndexInfo(
                name=row["indexname"],
                columns=columns,
                index_type=index_type,
                is_unique="unique" in indexdef,
                is_primary=row["indexname"].endswith("_pkey"),
            )

            if key not in indexes_map:
                indexes_map[key] = []
            indexes_map[key].append(index)

        # 构建表信息
        tables: list[TableInfo] = []
        for row in tables_rows:
            key = (row["table_schema"], row["table_name"])
            table = TableInfo(
                name=row["table_name"],
                schema_name=row["table_schema"],
                columns=columns_map.get(key, []),
                indexes=indexes_map.get(key, []),
                comment=row["table_comment"],
            )
            tables.append(table)

        # 构建视图信息
        views: list[ViewInfo] = []
        for row in views_rows:
            key = (row["table_schema"], row["table_name"])
            view = ViewInfo(
                name=row["table_name"],
                schema_name=row["table_schema"],
                columns=columns_map.get(key, []),
                definition=row["view_definition"],
            )
            views.append(view)

        # 构建枚举类型
        enum_types: list[EnumTypeInfo] = []
        for row in enums_rows:
            enum = EnumTypeInfo(
                name=row["type_name"],
                schema_name=row["schema_name"],
                values=list(row["enum_values"]),
            )
            enum_types.append(enum)

        return DatabaseSchema(
            name=database,
            tables=tables,
            views=views,
            enum_types=enum_types,
            cached_at=time.time(),
        )

    def invalidate(self, database: str) -> None:
        """使指定数据库的缓存失效

        Args:
            database: 数据库名称
        """
        if database in self._cache:
            del self._cache[database]
            self._logger.info("Schema cache invalidated", database=database)

    def invalidate_all(self) -> None:
        """使所有缓存失效"""
        self._cache.clear()
        self._logger.info("All schema caches invalidated")

    @property
    def cached_databases(self) -> list[str]:
        """获取已缓存的数据库列表"""
        return list(self._cache.keys())
