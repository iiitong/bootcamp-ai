# Research: MySQL 数据库支持

**Feature**: 002-mysql-support
**Date**: 2025-12-16

## 1. MySQL 异步驱动选择

### Decision: aiomysql

### Rationale
- aiomysql 是 Python 生态中最成熟的异步 MySQL 驱动
- 基于 PyMySQL，API 稳定且文档完善
- 与 asyncio 原生集成，符合现有项目的异步架构
- 支持连接池、事务、prepared statements
- 活跃维护，兼容 MySQL 5.7+ 和 8.0

### Alternatives considered
| 驱动 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| aiomysql | 成熟稳定，广泛使用 | 依赖 PyMySQL | ✅ 选用 |
| asyncmy | 纯异步实现，性能更优 | 较新，社区较小 | 备选 |
| mysql-connector-python | Oracle 官方驱动 | 异步支持有限 | ❌ 不适合 |
| databases + aiomysql | 统一 ORM 抽象 | 引入额外抽象层，过度设计 | ❌ 不适合 |

---

## 2. MySQL information_schema 元数据提取

### Decision: 使用 information_schema 标准查询

### Rationale
MySQL 的 `information_schema` 数据库提供与 PostgreSQL 类似的元数据查询能力：
- `information_schema.tables` - 表和视图信息
- `information_schema.columns` - 列定义
- `information_schema.key_column_usage` - 主键和外键
- `information_schema.table_constraints` - 约束类型

### MySQL 与 PostgreSQL information_schema 差异

| 特性 | PostgreSQL | MySQL | 适配策略 |
|------|------------|-------|----------|
| Schema 概念 | 支持多 schema | 使用 database 作为 schema | 将 database 名映射为 schema_name |
| 系统表过滤 | `pg_catalog`, `information_schema` | `mysql`, `information_schema`, `performance_schema`, `sys` | 调整过滤条件 |
| 外键查询 | 标准 SQL | 需要额外 JOIN `referential_constraints` | 简化为基本外键检测 |
| 数据类型表示 | `data_type` 标准化 | `column_type` 更详细（含长度） | 使用 `data_type` 保持一致 |

### MySQL 元数据查询模板

```sql
-- 表和视图
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
ORDER BY table_schema, table_name;

-- 列信息（含主键/外键标识）
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
WHERE c.table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
ORDER BY c.table_schema, c.table_name, c.ordinal_position;
```

---

## 3. sqlglot MySQL 方言支持

### Decision: 使用 sqlglot 的 `mysql` 方言

### Rationale
sqlglot 已在项目中用于 PostgreSQL，同样支持 MySQL 方言：
- 解析：`sqlglot.parse_one(sql, dialect="mysql")`
- 生成：`parsed.sql(dialect="mysql")`
- 支持 MySQL 特有语法：反引号标识符、LIMIT 语法、数据类型映射

### MySQL SQL 特性处理

| 特性 | PostgreSQL | MySQL | sqlglot 处理 |
|------|------------|-------|--------------|
| 标识符引用 | `"identifier"` | `` `identifier` `` | 自动转换 |
| LIMIT 语法 | `LIMIT n OFFSET m` | `LIMIT m, n` 或 `LIMIT n OFFSET m` | 两种都支持 |
| 布尔类型 | `true/false` | `1/0` | 自动转换 |
| 字符串引号 | `'string'` | `'string'` | 相同 |

### 代码修改策略

```python
# SQLProcessor 修改
def process(cls, sql: str, dialect: str = "postgres", max_limit: int | None = None) -> str:
    parsed = sqlglot.parse_one(sql, dialect=dialect)
    # ... validation ...
    return parsed.sql(dialect=dialect)
```

---

## 4. 数据库类型识别策略

### Decision: 基于 URL 前缀自动识别

### Rationale
连接 URL 已包含明确的数据库类型信息：
- PostgreSQL: `postgresql://` 或 `postgres://`
- MySQL: `mysql://` 或 `mysql+aiomysql://`

### URL 解析实现

```python
from urllib.parse import urlparse

def detect_db_type(url: str) -> str:
    """检测数据库类型"""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in ("postgresql", "postgres"):
        return "postgresql"
    elif scheme in ("mysql", "mysql+aiomysql"):
        return "mysql"
    else:
        raise ValueError(f"Unsupported database type: {scheme}")
```

---

## 5. MySQL 查询超时控制

### Decision: 使用 `SET max_execution_time` 或连接参数

### Rationale
MySQL 提供多种超时控制方式：

| 方法 | 适用版本 | 粒度 | 推荐度 |
|------|----------|------|--------|
| `SET max_execution_time=N` | 5.7.8+ | 查询级 | ⭐⭐⭐ 推荐 |
| `connect_timeout` | 全部 | 连接级 | ⭐⭐ 备选 |
| `wait_timeout` | 全部 | 会话级 | ⭐ 不推荐 |

### 实现方案

```python
async def execute_mysql(connection_url: str, sql: str, timeout_seconds: int = 30):
    async with aiomysql.connect(...) as conn:
        async with conn.cursor() as cur:
            # 设置查询超时（毫秒）
            await cur.execute(f"SET max_execution_time = {timeout_seconds * 1000}")
            await cur.execute(sql)
            # ...
```

---

## 6. 自然语言 SQL 生成适配

### Decision: 修改 LLM 系统提示词，增加数据库类型参数

### Rationale
自然语言生成 SQL 需要知道目标数据库类型，以生成正确的语法：
- MySQL 使用反引号引用标识符
- MySQL 的 GROUP BY 行为与 PostgreSQL 不同
- MySQL 特有函数：`IFNULL` vs `COALESCE`，`CONCAT` vs `||`

### 系统提示词模板

```python
def get_system_prompt(self, db_type: str) -> str:
    db_name = "MySQL" if db_type == "mysql" else "PostgreSQL"
    return f"""You are a {db_name} expert. Generate SQL queries based on natural language descriptions.

Database schema:
{self.schema_context}

Rules:
- Only generate SELECT statements
- Do not add LIMIT (the system will add it automatically)
- Return only the SQL code, no explanations
- Use standard {db_name} syntax
- {"Use backticks for identifiers if needed" if db_type == "mysql" else "Use double quotes for identifiers if needed"}
- If the request is unclear, make reasonable assumptions based on the schema
"""
```

---

## 7. SQLite 存储扩展

### Decision: 添加 `db_type` 字段到 connections 表

### Rationale
需要存储数据库类型以便后续查询时选择正确的驱动和方言：

```sql
ALTER TABLE connections ADD COLUMN db_type TEXT DEFAULT 'postgresql';
```

### 迁移策略
- 检查列是否存在，不存在则添加
- 现有数据默认为 `postgresql`
- 新增连接时根据 URL 自动设置

---

## 8. 测试数据库设计（电商领域）

### Decision: 5 张表，orders 表 1000+ 条记录

### 表结构设计

```
users (用户表)
├── id (PK)
├── username
├── email
├── created_at
└── updated_at

products (产品表)
├── id (PK)
├── name
├── description
├── price
├── stock
├── category
└── created_at

orders (订单表) - 1000+ 条记录
├── id (PK)
├── user_id (FK → users.id)
├── total_amount
├── status
├── created_at
└── updated_at

payments (支付表)
├── id (PK)
├── order_id (FK → orders.id)
├── amount
├── method
├── status
└── paid_at

reviews (评价表)
├── id (PK)
├── user_id (FK → users.id)
├── product_id (FK → products.id)
├── rating
├── comment
└── created_at
```

### 测试数据量规划

| 表 | 记录数 | 说明 |
|---|--------|------|
| users | 100 | 基础用户数据 |
| products | 50 | 产品目录 |
| orders | 1500 | 满足 1000+ 要求 |
| payments | 1200 | 约 80% 订单已支付 |
| reviews | 300 | 部分产品有评价 |

---

## 总结

所有技术决策已完成，无需进一步澄清。可继续执行 Phase 1。
