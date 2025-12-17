# Data Model: MySQL 数据库支持

**Feature**: 002-mysql-support
**Date**: 2025-12-16

## 实体定义

### 1. DatabaseConnection (数据库连接)

存储用户添加的数据库连接信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| name | string | PK, 必填, 唯一 | 连接名称（用户定义） |
| url | string | 必填 | 完整连接 URL |
| db_type | string | 必填, enum | 数据库类型: `postgresql` \| `mysql` |
| created_at | datetime | 必填 | 创建时间 (UTC) |
| updated_at | datetime | 必填 | 更新时间 (UTC) |
| metadata_cached_at | datetime | 可空 | 元数据缓存时间 |

**验证规则**:
- `name`: 必须以字母开头，仅允许字母、数字、下划线、连字符
- `url`: 必须以 `postgresql://`、`postgres://`、`mysql://` 或 `mysql+aiomysql://` 开头
- `db_type`: 根据 URL 前缀自动推导

**状态转换**:
```
[Created] → [Metadata Cached] → [Updated] → [Deleted]
              ↑                    |
              └────────────────────┘ (refresh)
```

---

### 2. TableInfo (表信息)

数据库中的表或视图元数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| schema_name | string | 必填 | Schema 名称 (PostgreSQL) 或 Database 名称 (MySQL) |
| name | string | 必填 | 表/视图名称 |
| type | string | 必填, enum | 类型: `TABLE` \| `VIEW` |
| columns | ColumnInfo[] | 必填 | 列信息列表 |

**复合唯一键**: `(connection_name, schema_name, name)`

---

### 3. ColumnInfo (列信息)

表或视图中的列定义。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| name | string | 必填 | 列名 |
| data_type | string | 必填 | 数据类型 |
| nullable | boolean | 必填 | 是否可空 |
| default_value | string | 可空 | 默认值 |
| is_primary_key | boolean | 必填 | 是否为主键 |
| is_foreign_key | boolean | 必填 | 是否为外键 |

---

### 4. QueryRequest (查询请求)

用户提交的 SQL 查询。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| sql | string | 必填, 1-10000 字符 | SQL 查询语句 |

**验证规则**:
- 仅允许 SELECT 和 UNION 语句
- 禁止 INSERT, UPDATE, DELETE, DROP, TRUNCATE, CREATE, ALTER

---

### 5. QueryResult (查询结果)

SQL 查询执行结果。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| columns | string[] | 必填 | 列名列表 |
| rows | dict[] | 必填 | 数据行（键值对数组） |
| row_count | integer | 必填 | 返回行数 |
| execution_time_ms | float | 必填 | 执行时间（毫秒） |

---

### 6. NaturalLanguageQuery (自然语言查询)

用户的自然语言查询请求。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| prompt | string | 必填, 1-1000 字符 | 自然语言描述 |

---

### 7. NaturalLanguageQueryResult (自然语言查询结果)

自然语言转 SQL 的结果。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| generated_sql | string | 必填 | 生成的 SQL 语句 |
| result | QueryResult | 可空 | 执行结果（如果自动执行） |

---

## 测试数据库模型（电商领域）

### E-R 关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │       │  products   │       │   reviews   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──┐   │ id (PK)     │◄──────│ product_id  │
│ username    │   │   │ name        │       │ user_id     │──┐
│ email       │   │   │ description │       │ rating      │  │
│ created_at  │   │   │ price       │       │ comment     │  │
│ updated_at  │   │   │ stock       │       │ created_at  │  │
└─────────────┘   │   │ category    │       └─────────────┘  │
       ▲          │   │ created_at  │                        │
       │          │   └─────────────┘                        │
       │          │                                          │
       │          └──────────────────────────────────────────┘
       │
┌──────┴──────┐       ┌─────────────┐
│   orders    │       │  payments   │
├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ order_id    │
│ user_id (FK)│       │ id (PK)     │
│ total_amount│       │ amount      │
│ status      │       │ method      │
│ created_at  │       │ status      │
│ updated_at  │       │ paid_at     │
└─────────────┘       └─────────────┘
```

### 表详细定义

#### users (用户表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 用户名 |
| email | VARCHAR(100) | NOT NULL, UNIQUE | 邮箱 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### products (产品表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 产品 ID |
| name | VARCHAR(200) | NOT NULL | 产品名称 |
| description | TEXT | | 产品描述 |
| price | DECIMAL(10,2) | NOT NULL | 价格 |
| stock | INT | NOT NULL, DEFAULT 0 | 库存 |
| category | VARCHAR(50) | | 类别 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### orders (订单表) - 1000+ 条记录

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 订单 ID |
| user_id | INT | NOT NULL, FK → users.id | 用户 ID |
| total_amount | DECIMAL(10,2) | NOT NULL | 总金额 |
| status | ENUM | NOT NULL | 状态: pending, paid, shipped, completed, cancelled |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### payments (支付表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 支付 ID |
| order_id | INT | NOT NULL, FK → orders.id, UNIQUE | 订单 ID |
| amount | DECIMAL(10,2) | NOT NULL | 支付金额 |
| method | ENUM | NOT NULL | 支付方式: credit_card, debit_card, alipay, wechat |
| status | ENUM | NOT NULL | 状态: pending, success, failed, refunded |
| paid_at | DATETIME | | 支付时间 |

#### reviews (评价表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 评价 ID |
| user_id | INT | NOT NULL, FK → users.id | 用户 ID |
| product_id | INT | NOT NULL, FK → products.id | 产品 ID |
| rating | TINYINT | NOT NULL, CHECK (1-5) | 评分 |
| comment | TEXT | | 评价内容 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**唯一约束**: `(user_id, product_id)` - 每用户每产品只能评价一次

---

## 存储层扩展

### SQLite connections 表修改

```sql
-- 新增 db_type 列（向后兼容迁移）
ALTER TABLE connections ADD COLUMN db_type TEXT DEFAULT 'postgresql';

-- 更新后的表结构
CREATE TABLE connections (
    name TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    db_type TEXT NOT NULL DEFAULT 'postgresql',  -- 新增
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata_cached_at TEXT
);
```

### 索引建议

```sql
-- metadata_cache 表索引优化
CREATE INDEX idx_metadata_cache_connection ON metadata_cache(connection_name);
```
