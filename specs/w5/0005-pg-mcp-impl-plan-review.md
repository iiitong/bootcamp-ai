# PostgreSQL MCP Server 实现计划 Review 报告

**版本**: 1.0
**日期**: 2026-01-10
**审核工具**: OpenAI Codex CLI v0.80.0 (gpt-5.2-codex)
**审核对象**: [0004-pg-mcp-impl-plan.md](./0004-pg-mcp-impl-plan.md)

---

## 执行摘要

实现计划结构良好、阶段划分合理，但存在以下需要在实现前解决的阻塞性问题：

1. **依赖顺序问题** - Phase 2 组件引用了 Phase 3 中定义的模型/错误类
2. **安全深度防御不足** - 查询执行缺少只读事务保护
3. **SQL 验证遗漏** - 未阻止 `SELECT INTO`、`FOR UPDATE` 等特殊 SELECT 变体

总体评估：**需要修订后方可实施**

---

## 详细发现

### 高严重性 (High)

#### H-1: Phase 2 模块依赖 Phase 3 定义的类型

**位置**:
- `0004-pg-mcp-impl-plan.md:304` (SQLValidationResult)
- `0004-pg-mcp-impl-plan.md:450` (SQLGenerationResult)
- `0004-pg-mcp-impl-plan.md:481` (PgMcpError)
- `0004-pg-mcp-impl-plan.md:525`

**问题描述**:
Phase 2 的基础设施组件（如 SQLParser、OpenAIClient）引用了 `SQLValidationResult`、`SQLGenerationResult`、`PgMcpError` 等类型，但这些类型被规划在 Phase 3 (Task 3.1) 中实现。这破坏了增量构建和测试的可能性。

**影响**:
- 无法按计划顺序逐步构建
- 单元测试无法在 Phase 2 独立运行
- 依赖图与实际代码依赖不匹配

**建议**:
将共享模型（`models/query.py` 和 `models/errors.py`）移动到 Phase 1 或 Phase 2 早期阶段。

---

#### H-2: 查询执行缺少只读事务保护

**位置**:
- `0004-pg-mcp-impl-plan.md:545`
- `0004-pg-mcp-impl-plan.md:556`

**问题描述**:
计划中仅对 `EXPLAIN` 命令使用只读事务，但实际查询执行 (`_execute_sql`) 没有强制使用只读事务。如果 SQL 验证遗漏了某些危险语句，将没有最后一道防线。

**影响**:
- 如果验证器被绕过，可能执行修改数据的操作
- 缺少深度防御

**建议**:
1. 所有查询执行都应在只读事务中进行：
   ```python
   async with conn.transaction(readonly=True):
       rows = await conn.fetch(sql)
   ```
2. 考虑使用只读数据库角色连接
3. 配置 `default_transaction_read_only=on`

---

#### H-3: SQL 验证规则未阻止特殊 SELECT 变体

**位置**:
- `0004-pg-mcp-impl-plan.md:281`
- `0004-pg-mcp-impl-plan.md:323`

**问题描述**:
以下 SQL 语句可能被解析为 SELECT 类型但实际上会修改数据或获取锁：
- `SELECT INTO` - 创建新表
- `CREATE TABLE AS SELECT (CTAS)` - 创建新表
- `SELECT ... FOR UPDATE/SHARE` - 获取行锁
- `COPY ... TO PROGRAM` - 执行系统命令
- `SET ROLE` - 提权攻击
- `LISTEN/NOTIFY` - 会话状态操作

**影响**:
- 安全边界被绕过
- 可能导致数据泄露、锁等待或权限提升

**建议**:
1. 扩展 SQL 验证规则，显式阻止：
   ```python
   FORBIDDEN_SELECT_VARIANTS = {
       exp.Into,       # SELECT INTO
       exp.Lock,       # FOR UPDATE/SHARE
   }

   FORBIDDEN_KEYWORDS.update({
       "SELECT INTO",
       "FOR UPDATE",
       "FOR SHARE",
       "FOR NO KEY UPDATE",
       "COPY",
       "SET ROLE",
       "SET SESSION",
       "LISTEN",
       "NOTIFY",
   })
   ```
2. 添加对应的测试用例

---

### 中等严重性 (Medium)

#### M-1: 资源限制不完整

**位置**: `0004-pg-mcp-impl-plan.md:314`, `0004-pg-mcp-impl-plan.md:545`

**问题描述**:
资源限制仅通过 `LIMIT` 子句实现，缺少：
- `statement_timeout` - 语句超时
- `lock_timeout` - 锁等待超时
- `idle_in_transaction_session_timeout` - 空闲事务超时
- 输出大小限制（字节数）

**影响**:
- DoS 风险：长时间运行的查询占用连接
- 内存耗尽：大结果集

**建议**:
1. 在连接池配置中设置服务器端超时：
   ```python
   await conn.execute("SET statement_timeout = '30s'")
   await conn.execute("SET lock_timeout = '5s'")
   ```
2. 添加结果大小限制（字节数）

---

#### M-2: 速率限制器缺少并发安全定义

**位置**: `0004-pg-mcp-impl-plan.md:481`

**问题描述**:
速率限制器设计未明确：
- 作用域（全局 vs 每数据库 vs 每客户端）
- 高并发下的竞态条件处理
- 分布式场景支持

**影响**:
- 高并发下可能允许超限请求
- 多实例部署时限制失效

**建议**:
1. 明确定义限制粒度
2. 使用 `asyncio.Lock` 保护计数器
3. 考虑 Redis 实现分布式限制

---

#### M-3: OpenAI 客户端缺少最佳实践

**位置**: `0004-pg-mcp-impl-plan.md:450`

**问题描述**:
OpenAI 客户端计划缺少：
- 显式异步客户端使用
- 指数退避重试策略
- Token 使用统计
- 超时配置

**影响**:
- API 调用可靠性不足
- 无法追踪 Token 消耗
- 潜在的阻塞问题

**建议**:
1. 使用 `AsyncOpenAI` 客户端
2. 实现指数退避 + 抖动重试
3. 添加 Token 计数和上报
4. 配置显式超时

---

#### M-4: Schema 缓存缺少过滤机制

**位置**: `0004-pg-mcp-impl-plan.md:374`, `0004-pg-mcp-impl-plan.md:394`

**问题描述**:
Schema 缓存没有：
- 允许/拒绝列表（表/schema 级别）
- 系统 schema 过滤
- Prompt 大小限制

**影响**:
- 大型数据库加载缓慢
- Prompt 超出 Token 限制
- 敏感表信息泄露

**建议**:
1. 添加 `include_schemas`/`exclude_schemas` 配置
2. 默认排除 `pg_catalog`, `information_schema`
3. 限制 Prompt 最大长度

---

#### M-5: MCP Resources 缺少访问控制

**位置**: `0004-pg-mcp-impl-plan.md:609`

**问题描述**:
`databases://list` 和 `schema://{database}` 资源暴露了数据库列表和完整 Schema，但没有访问控制机制。

**影响**:
- 多租户环境下的信息泄露
- 敏感 Schema 信息暴露

**建议**:
1. 添加访问控制配置选项
2. 文档说明安全边界
3. 考虑日志脱敏

---

#### M-6: 集成测试不完整

**位置**: `0004-pg-mcp-impl-plan.md:750`, `0004-pg-mcp-impl-plan.md:766`

**问题描述**:
- 真实数据库 E2E 测试被标记为可选
- 缺少异步并发测试
- 缺少只读事务强制测试

**影响**:
- 关键行为未验证
- 并发问题可能遗漏

**建议**:
1. 使用 `testcontainers` 进行真实数据库测试
2. 添加并发场景测试
3. 添加只读强制测试

---

#### M-7: 风险评估遗漏

**位置**: `0004-pg-mcp-impl-plan.md:786`

**问题描述**:
风险评估未包含：
- LLM 数据隐私/合规风险
- Prompt 注入风险
- Python 3.13 + FastMCP/asyncpg 兼容性

**影响**:
- 安全风险未识别
- 运行时兼容性问题

**建议**:
1. 添加 LLM 数据处理风险分析
2. 评估 Prompt 注入防护
3. 验证依赖版本兼容性

---

### 低严重性 (Low)

#### L-1: 依赖列表不完整

**位置**: `0004-pg-mcp-impl-plan.md:16`, `0004-pg-mcp-impl-plan.md:151`, `0004-pg-mcp-impl-plan.md:750`

**问题描述**:
依赖列表缺少：
- `pydantic-settings`（配置管理）
- `pytest-asyncio`（异步测试）
- `testcontainers`（集成测试）

**影响**:
- 项目依赖不完整
- 复现性问题

**建议**:
1. 补充完整依赖列表
2. 锁定版本号

---

## 建议行动项

按优先级排序：

### 必须修复 (Blocker)

| ID | 建议 | 对应发现 |
|----|------|---------|
| A-1 | 将共享模型/错误移至 Phase 1/2 早期，更新依赖图 | H-1 |
| A-2 | 所有查询执行使用只读事务 + 只读角色 + 服务端超时 | H-2 |
| A-3 | 扩展 SQL 验证阻止 `SELECT INTO`, CTAS, `FOR UPDATE`, `COPY ... PROGRAM`, `SET ROLE`, `LISTEN/NOTIFY`，并添加测试 | H-3 |

### 建议修复 (Should Fix)

| ID | 建议 | 对应发现 |
|----|------|---------|
| A-4 | OpenAI 客户端使用 AsyncOpenAI，添加超时、指数退避、Token 统计 | M-3 |
| A-5 | 添加 Schema 允许/拒绝列表，排除系统 schema，限制 Prompt 大小 | M-4 |
| A-6 | 定义 MCP 访问控制机制，文档说明数据处理和日志脱敏 | M-5 |
| A-7 | 使用 testcontainers 进行真实数据库测试，添加并发测试 | M-6 |
| A-8 | 锁定依赖版本，验证 Python 3.13 兼容性 | M-7, L-1 |

### 可选改进 (Nice to Have)

| ID | 建议 | 对应发现 |
|----|------|---------|
| A-9 | 添加服务端 statement_timeout, lock_timeout | M-1 |
| A-10 | 明确速率限制粒度，考虑分布式实现 | M-2 |
| A-11 | 补充 LLM 数据隐私风险分析 | M-7 |

---

## 总体评估

### 优点

1. **结构清晰** - 分层架构和阶段划分合理
2. **安全意识** - 已考虑 SQL 注入防护、速率限制等
3. **可测试性** - 包含完整的测试策略
4. **文档完整** - 详细的任务描述和验证标准

### 需要改进

1. **依赖顺序** - 需要重新调整模块边界
2. **深度防御** - 需要添加只读事务作为最后防线
3. **SQL 验证覆盖** - 需要扩展验证规则
4. **集成测试** - 需要真实数据库测试

### 结论

该实现计划框架良好，但在**依赖重整**和**安全深度防御**方面需要修订后方可开始实施。预计修订工作量较小，不影响整体时间线。

**建议**：根据上述建议修订实现计划后再开始编码。

---

## 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-10 | 初始 Review 报告 | Codex (gpt-5.2-codex) |
