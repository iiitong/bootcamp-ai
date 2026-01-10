# PostgreSQL MCP Server 需求文档 (PRD)

**版本**: 1.1
**日期**: 2026-01-10
**状态**: 草稿待审核

---

## 1. 概述

### 1.1 项目背景

构建一个基于 Model Context Protocol (MCP) 的 PostgreSQL 智能查询服务器。该服务器能够接收用户的自然语言查询需求，利用大语言模型 (LLM) 生成 SQL，并返回查询语句或执行结果。

### 1.2 目标用户

- 不熟悉 SQL 语法但需要查询数据库的业务人员
- 需要快速验证数据的开发人员
- 通过 MCP 协议集成数据库查询能力的 AI Agent

### 1.3 核心价值

- **降低门槛**：用户无需掌握 SQL 即可查询数据库
- **安全可控**：仅允许只读查询，防止误操作
- **智能验证**：自动验证 SQL 正确性和结果合理性
- **上下文感知**：基于数据库 Schema 生成精准 SQL

---

## 2. 功能需求

### 2.1 MCP 服务器启动与初始化

#### 2.1.1 配置加载

| 配置项 | 说明 | 必填 |
|--------|------|------|
| `databases` | 可访问的 PostgreSQL 数据库连接配置列表 | 是 |
| `openai_api_key` | OpenAI API 密钥 | 是 |
| `openai_model` | 使用的模型名称，默认 `gpt-4o-mini` | 否 |
| `cache_refresh_interval` | Schema 缓存刷新间隔（秒），默认 3600 | 否 |
| `max_result_rows` | 单次查询最大返回行数，默认 1000 | 否 |
| `query_timeout` | SQL 执行超时时间（秒），默认 30 | 否 |

**数据库连接配置结构**:
```yaml
databases:
  - name: "production_analytics"      # 数据库别名（用于用户引用）
    host: "localhost"
    port: 5432
    database: "analytics"
    user: "readonly_user"
    password: "${PG_PASSWORD}"        # 支持环境变量引用
    ssl_mode: "require"               # 可选: disable, allow, prefer, require
  - name: "staging_orders"
    connection_string: "postgresql://user:pass@host:5432/db"  # 或使用连接字符串
```

#### 2.1.2 Schema 缓存

服务器启动时应自动扫描并缓存以下数据库元数据：

| 元数据类型 | 缓存内容 |
|-----------|---------|
| **Tables** | 表名、列名、列类型、主键、非空约束、默认值、列注释 |
| **Views** | 视图名、列定义 |
| **Indexes** | 索引名、索引列、索引类型（B-tree/Hash/GIN/GiST等）、唯一性 |
| **Custom Types** | ENUM 类型名称及其可选值、复合类型定义 |
| **Foreign Keys** | 外键关系、引用表、引用列 |

**缓存刷新机制**:
- 定时刷新：根据 `cache_refresh_interval` 配置定期刷新
- 启动时刷新：服务器启动时自动加载所有数据库的 Schema

---

### 2.2 MCP Resources 定义

通过 MCP Resources 暴露数据库元数据，供 AI 客户端读取上下文信息。

#### 2.2.1 `databases://list` - 数据库列表

**描述**: 返回当前 MCP 服务器配置的所有可查询数据库

**URI**: `databases://list`

**返回内容** (text/plain):
```
Available Databases:
- production_analytics (25 tables, 8 views)
- staging_orders (12 tables, 3 views)
```

#### 2.2.2 `schema://{database}` - 数据库 Schema

**描述**: 返回指定数据库的完整 Schema 信息

**URI**: `schema://production_analytics`

**返回内容** (text/plain):
```
Database: production_analytics

## Tables

### orders
Columns:
  - id: bigint (PRIMARY KEY)
  - user_id: integer (NOT NULL, FK -> users.id)
  - status: order_status (ENUM: 'pending', 'paid', 'shipped', 'cancelled')
  - total_amount: decimal(10,2)
  - created_at: timestamp with time zone

Indexes:
  - orders_pkey (PRIMARY, btree on id)
  - idx_orders_user_id (btree on user_id)
  - idx_orders_created_at (btree on created_at)

### users
Columns:
  - id: integer (PRIMARY KEY)
  - email: varchar(255) (UNIQUE)
  - name: varchar(100)

## Views
...

## Custom Types
- order_status: ENUM ('pending', 'paid', 'shipped', 'cancelled')
```

---

### 2.3 MCP Tools 定义

#### 2.3.1 `query` - 自然语言查询

**描述**: 根据用户的自然语言描述执行数据库查询

**输入参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `question` | string | 是 | 用户的自然语言查询需求 |
| `database` | string | 否 | 目标数据库名称，若只有一个数据库则可省略 |
| `return_type` | enum | 否 | 返回类型：`sql` 仅返回 SQL，`result` 返回查询结果，`both` 两者都返回。默认 `result` |
| `limit` | integer | 否 | 限制返回行数，覆盖默认配置 |

**输出**:
```json
{
  "success": true,
  "sql": "SELECT ...",           // 当 return_type 为 sql 或 both 时返回
  "result": {                     // 当 return_type 为 result 或 both 时返回
    "columns": ["col1", "col2"],
    "rows": [["val1", "val2"], ...],
    "row_count": 42,
    "truncated": false            // 是否因超过 limit 被截断
  },
  "explanation": "..."            // SQL 逻辑说明（可选）
}
```

**错误响应**:
```json
{
  "success": false,
  "error_code": "INVALID_QUERY",
  "error_message": "无法理解查询意图，请提供更多上下文"
}
```

---

### 2.4 SQL 生成流程

```
┌─────────────────┐
│  用户自然语言    │
│  查询需求        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  加载目标数据库  │
│  Schema 缓存    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  构建 LLM Prompt │
│  (Schema + 需求) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  调用 OpenAI    │
│  gpt-4o-mini    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  解析 LLM 响应  │
│  提取 SQL       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  安全校验       │──────┐
│  (只读检查)     │      │ 失败
└────────┬────────┘      │
         │ 通过          ▼
         │         ┌──────────┐
         ▼         │ 返回错误  │
┌─────────────────┐ └──────────┘
│  语法校验       │
│  (EXPLAIN)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  执行查询       │
│  (带超时控制)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  结果验证       │
│  (LLM 确认)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  返回结果       │
└─────────────────┘
```

#### 2.4.1 LLM Prompt 构建

Prompt 应包含以下信息：

1. **系统角色设定**: 说明 LLM 是一个 SQL 生成助手
2. **数据库 Schema**: 相关表结构、列类型、关系
3. **约束说明**:
   - 仅生成 SELECT 语句
   - 使用标准 PostgreSQL 语法
   - 优先使用索引列进行过滤
4. **用户需求**: 原始自然语言描述
5. **输出格式**: 要求返回可直接执行的 SQL

**示例 Prompt 结构**:
```
你是一个 PostgreSQL SQL 生成专家。请根据用户的需求生成安全、高效的查询语句。

## 数据库 Schema

### 表: orders
- id (bigint, 主键)
- user_id (integer, 非空, 外键 -> users.id)
- status (order_status: 'pending' | 'paid' | 'shipped' | 'cancelled')
- total_amount (decimal(10,2))
- created_at (timestamp with time zone)

索引: idx_orders_user_id, idx_orders_created_at

### 表: users
- id (integer, 主键)
- email (varchar(255), 唯一)
- name (varchar(100))

## 约束
1. 仅生成 SELECT 语句
2. 使用 PostgreSQL 标准语法
3. 查询应该尽可能利用已有索引

## 用户需求
{user_question}

请直接返回 SQL 语句，不要包含额外说明。
```

---

### 2.5 安全校验

#### 2.5.1 只读校验规则

生成的 SQL 必须通过以下安全检查：

| 检查项 | 规则 |
|--------|------|
| **禁止的语句类型** | INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, GRANT, REVOKE |
| **禁止的函数** | `pg_sleep`, `pg_terminate_backend`, `pg_cancel_backend`, `lo_*` 系列 |
| **禁止的语法** | `INTO OUTFILE`, `COPY TO`, `\copy` |
| **CTE 检查** | WITH 子句中不允许包含修改操作 |
| **子查询检查** | 所有子查询必须是 SELECT |

#### 2.5.2 校验实现方式

使用 `sqlglot` 解析 SQL 并验证：

1. **AST 解析**: 使用 sqlglot 将 SQL 解析为抽象语法树
2. **语句类型检查**: 验证根节点必须是 Select 类型
3. **递归检查**: 遍历所有子节点确保无修改操作
4. **函数检查**: 检查调用的函数是否在禁止列表中

**sqlglot 的优势**:
- 支持多种 SQL 方言（PostgreSQL、MySQL、SQLite 等），便于未来扩展
- 提供完整的 AST 遍历能力
- 可以进行 SQL 转换和优化

#### 2.5.3 数据库用户权限

**建议**: 配置的数据库用户应该在数据库层面也设置为只读：
```sql
CREATE USER mcp_readonly WITH PASSWORD 'xxx';
GRANT CONNECT ON DATABASE mydb TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;
```

---

### 2.6 结果验证

#### 2.6.1 语法验证

在执行查询前，使用 `EXPLAIN` 验证 SQL 语法正确性：
```sql
EXPLAIN (FORMAT JSON) SELECT ...
```

如果 EXPLAIN 失败，说明 SQL 存在语法错误，应返回错误信息并可选择让 LLM 重新生成。

#### 2.6.2 结果合理性验证（可选）

执行查询后，可将部分结果发送给 LLM 验证：

**验证 Prompt**:
```
用户需求: {original_question}
生成的 SQL: {generated_sql}
查询结果 (前 5 行): {sample_results}

请判断:
1. SQL 是否正确理解了用户意图？
2. 返回的结果是否符合预期？
3. 如果有问题，请指出问题所在。

返回 JSON: {"valid": true/false, "reason": "..."}
```

**触发条件**:
- 配置项 `enable_result_validation: true`
- 查询结果为空时自动触发（确认是数据问题还是 SQL 问题）

---

### 2.7 错误处理

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| `UNKNOWN_DATABASE` | 指定的数据库不存在 | 返回可用数据库列表 |
| `AMBIGUOUS_QUERY` | 查询意图不明确 | 要求用户提供更多上下文 |
| `UNSAFE_SQL` | 生成的 SQL 包含非只读操作 | 拒绝执行，记录告警日志 |
| `SYNTAX_ERROR` | SQL 语法错误 | 尝试让 LLM 重新生成（最多 2 次） |
| `EXECUTION_TIMEOUT` | 查询超时 | 返回超时错误，建议优化查询条件 |
| `CONNECTION_ERROR` | 数据库连接失败 | 返回连接错误，检查配置 |
| `OPENAI_ERROR` | OpenAI API 调用失败 | 返回 API 错误信息 |
| `RESULT_TOO_LARGE` | 结果集过大 | 自动添加 LIMIT，提示用户 |

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 目标值 |
|------|--------|
| Schema 缓存加载时间 | < 5 秒 (100 表规模) |
| SQL 生成响应时间 | < 3 秒 (不含 OpenAI 延迟) |
| 并发查询支持 | >= 10 个并发请求 |
| 内存占用 | < 512MB (稳态) |

### 3.2 可靠性要求

- 数据库连接池管理，支持自动重连
- OpenAI API 调用失败时的重试机制（指数退避）
- Schema 缓存持久化，服务重启后可快速恢复

### 3.3 可观测性要求

- **日志**: 结构化日志，记录每次查询的输入、生成的 SQL、执行时间、结果行数
- **指标**: 查询成功率、平均响应时间、LLM token 消耗
- **追踪**: 支持 OpenTelemetry trace ID 透传（可选）

### 3.4 安全要求

- API 密钥不得明文存储在配置文件中，支持环境变量
- 所有数据库连接支持 SSL/TLS
- 查询日志中敏感数据（如密码字段值）应脱敏

---

## 4. 技术约束

### 4.1 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 编程语言 | Python 3.13.5 | 使用最新稳定版本 |
| MCP 框架 | `fastmcp` | 简洁易用的 MCP 服务器框架 |
| PostgreSQL 驱动 | `asyncpg` | 高性能异步 PostgreSQL 客户端 |
| SQL 解析 | `sqlglot` | 多方言支持，便于未来扩展 |
| OpenAI 客户端 | `openai` | 官方 SDK |
| 配置管理 | YAML + 环境变量 | 灵活的配置方式 |

### 4.2 部署方式

- 作为独立进程运行，通过 stdio 或 SSE 与 MCP 客户端通信
- 支持容器化部署（提供 Dockerfile）
- 配置文件路径可通过环境变量或命令行参数指定

---

## 5. 未来扩展（Out of Scope for V1）

以下功能不在本期实现范围，但需在设计时考虑扩展性：

- [ ] 支持 MySQL、SQLite 等其他数据库（sqlglot 已支持多方言）
- [ ] 查询历史记录和收藏
- [ ] 自然语言生成数据可视化（图表）
- [ ] 多步骤复杂查询的对话式交互
- [ ] 查询结果导出（CSV、Excel）
- [ ] 基于用户反馈的 SQL 模板学习

---

## 6. 验收标准

### 6.1 功能验收

- [ ] 服务器可成功启动并缓存数据库 Schema
- [ ] MCP Resources 可正确返回数据库列表和 Schema 信息
- [ ] `query` 工具可根据自然语言生成正确的 SQL
- [ ] 生成的 SQL 通过安全校验（纯只读）
- [ ] 可正确执行查询并返回结果
- [ ] 错误场景有合适的错误提示

### 6.2 安全验收

- [ ] 无法通过任何输入生成修改数据的 SQL
- [ ] 数据库连接密码不出现在日志中
- [ ] 支持 SSL 数据库连接

### 6.3 性能验收

- [ ] 简单查询端到端响应时间 < 5 秒
- [ ] 服务内存占用 < 512MB

---

## 7. 术语表

| 术语 | 定义 |
|------|------|
| MCP | Model Context Protocol，Anthropic 提出的 AI Agent 工具协议 |
| Schema | 数据库结构定义，包括表、列、索引等 |
| LLM | Large Language Model，大语言模型 |
| AST | Abstract Syntax Tree，抽象语法树 |
| fastmcp | 基于 Python 的轻量级 MCP 服务器框架 |

---

## 8. 附录

### 8.1 参考资料

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [PostgreSQL System Catalogs](https://www.postgresql.org/docs/current/catalogs.html)
- [sqlglot Documentation](https://sqlglot.com/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

### 8.2 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-10 | 初始版本 | - |
| 1.1 | 2026-01-10 | 精简 Tools 为单一 query；更新技术栈为 Python 3.13.5 + fastmcp + asyncpg + sqlglot；新增 MCP Resources 暴露数据库元数据 | - |
