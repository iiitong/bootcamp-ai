# 实现计划：数据库查询工具

**分支**: `001-db-query-tool` | **日期**: 2025-12-13 | **规范**: [spec.md](./spec.md)
**输入**: 功能规范 `/specs/001-db-query-tool/spec.md`

## 概要

构建一个数据库查询工具，支持 PostgreSQL 数据库的连接管理、元数据提取、SQL 查询执行和自然语言生成 SQL。采用前后端分离架构，后端使用 Python/FastAPI 提供 RESTful API，前端使用 React/Refine 提供 Web 界面。

## 技术上下文

**后端**:
- **语言/版本**: Python 3.14+ (使用 uv 管理依赖)
- **Web 框架**: FastAPI
- **SQL 解析**: sqlglot
- **LLM 集成**: OpenAI SDK (兼容 API)
- **数据库驱动**: psycopg (PostgreSQL), sqlite3 (本地存储)
- **测试**: pytest

**前端**:
- **框架**: React 18+
- **管理框架**: Refine 5
- **样式**: Tailwind CSS
- **UI 组件**: Ant Design
- **SQL 编辑器**: Monaco Editor
- **包管理**: yarn
- **测试**: Vitest + React Testing Library

**存储**:
- **本地存储**: SQLite (`~/.db_query/db_query.db`)
- **目标数据库**: PostgreSQL

**目标平台**: Web 应用 (现代浏览器)
**项目类型**: Web 应用 (前后端分离)

**性能目标**:
- 数据库连接和元数据展示: < 30 秒
- 查询结果返回: < 5 秒 (1000 行以下)
- 自然语言生成 SQL: < 10 秒

**约束**:
- 仅支持 SELECT 查询
- 默认 LIMIT 1000
- CORS 允许所有 origin
- OpenAI API Key 从环境变量 `OPENAI_API_KEY` 读取

## Constitution Check

*GATE: 必须在 Phase 0 研究前通过。Phase 1 设计后重新检查。*

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 项目数量限制 | ✅ 通过 | 2 个项目 (backend + frontend) |
| 复杂度控制 | ✅ 通过 | 使用成熟框架，无过度工程 |
| 测试要求 | ✅ 通过 | pytest (后端) + Vitest (前端) |

---

## 实现阶段

### Phase 1: 后端基础设施 (Backend Foundation)

**目标**: 搭建 FastAPI 项目骨架，实现 SQLite 存储层

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 1.1 | 初始化 uv 项目，配置依赖 | `backend/pyproject.toml` | [research.md #版本清单](./research.md#版本清单) |
| 1.2 | 创建 FastAPI 应用入口，配置 CORS | `backend/src/main.py` | [research.md #FastAPI](./research.md#1-fastapi--pydantic-v2) |
| 1.3 | 实现配置管理 (环境变量) | `backend/src/config.py` | - |
| 1.4 | 实现 SQLite 存储层 | `backend/src/storage/sqlite.py` | [data-model.md #SQLite存储模型](./data-model.md#sqlite-存储模型) |
| 1.5 | 创建 Pydantic 数据模型 | `backend/src/models/*.py` | [data-model.md #API数据传输对象](./data-model.md#api-数据传输对象-dto) |

**验收标准**:
- [ ] `uv run uvicorn src.main:app --reload` 启动成功
- [ ] 访问 `http://localhost:8000/docs` 显示 Swagger UI
- [ ] SQLite 数据库文件在 `~/.db_query/` 创建成功

---

### Phase 2: 核心服务层 (Core Services)

**目标**: 实现数据库连接、元数据提取、SQL 验证三大核心服务

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 2.1 | 实现 PostgreSQL 元数据提取 | `backend/src/services/metadata.py` | [research.md #psycopg元数据提取](./research.md#4-psycopg-postgresql-驱动) |
| 2.2 | 实现 SQL 解析和验证 (SELECT-only, LIMIT) | `backend/src/services/query.py` | [research.md #sqlglot完整验证流程](./research.md#2-sqlglot-sql-解析) |
| 2.3 | 实现自然语言转 SQL | `backend/src/services/llm.py` | [research.md #OpenAI Text-to-SQL](./research.md#3-openai-sdk-自然语言转-sql) |
| 2.4 | 编写单元测试 | `backend/tests/unit/test_*.py` | [research.md #sqlglot测试用例](./research.md#2-sqlglot-sql-解析) |

**关键实现细节**:

**2.1 元数据提取** → 参考 [research.md 第330-390行](./research.md#4-psycopg-postgresql-驱动):
```python
# 使用 information_schema 查询
TABLES_QUERY = "SELECT table_schema, table_name, table_type FROM information_schema.tables..."
COLUMNS_QUERY = "SELECT table_schema, table_name, column_name, data_type..."
```

**2.2 SQL 验证** → 参考 [research.md 第128-174行](./research.md#2-sqlglot-sql-解析):
```python
# SQLProcessor.process() 方法
# 1. sqlglot.parse_one(sql, dialect="postgres")
# 2. isinstance(parsed, exp.Select) 检查
# 3. parsed.limit(1000) 添加 LIMIT
```

**2.3 自然语言转 SQL** → 参考 [research.md 第213-269行](./research.md#3-openai-sdk-自然语言转-sql):
```python
# TextToSQLGenerator 类
# - set_schema_context() 设置数据库结构
# - generate() 调用 OpenAI API
# - temperature=0 确保一致性
```

**验收标准**:
- [ ] `pytest backend/tests/unit/` 全部通过
- [ ] SQL 验证拒绝 INSERT/UPDATE/DELETE
- [ ] 无 LIMIT 的查询自动添加 LIMIT 1000

---

### Phase 3: API 端点实现 (API Endpoints)

**目标**: 实现所有 RESTful API 端点

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 3.1 | 实现 `GET /api/v1/dbs` | `backend/src/api/v1/endpoints/databases.py` | [openapi.yaml #listDatabases](./contracts/openapi.yaml) |
| 3.2 | 实现 `PUT /api/v1/dbs/{name}` | 同上 | [openapi.yaml #upsertDatabase](./contracts/openapi.yaml) |
| 3.3 | 实现 `GET /api/v1/dbs/{name}` | 同上 | [openapi.yaml #getDatabaseMetadata](./contracts/openapi.yaml) |
| 3.4 | 实现 `DELETE /api/v1/dbs/{name}` | 同上 | [openapi.yaml #deleteDatabase](./contracts/openapi.yaml) |
| 3.5 | 实现 `POST /api/v1/dbs/{name}/query` | 同上 | [openapi.yaml #executeQuery](./contracts/openapi.yaml) |
| 3.6 | 实现 `POST /api/v1/dbs/{name}/query/natural` | 同上 | [openapi.yaml #generateNaturalLanguageQuery](./contracts/openapi.yaml) |
| 3.7 | 配置路由和错误处理 | `backend/src/api/v1/router.py` | [data-model.md #错误代码](./data-model.md#错误代码) |
| 3.8 | 编写集成测试 | `backend/tests/integration/test_api.py` | - |

**API 端点概览** → 完整定义见 [contracts/openapi.yaml](./contracts/openapi.yaml):

| 方法 | 路径 | 操作 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | `/api/v1/dbs` | listDatabases | - | `DatabaseInfo[]` |
| PUT | `/api/v1/dbs/{name}` | upsertDatabase | `DatabaseCreateRequest` | `DatabaseMetadata` |
| GET | `/api/v1/dbs/{name}` | getDatabaseMetadata | - | `DatabaseMetadata` |
| DELETE | `/api/v1/dbs/{name}` | deleteDatabase | - | 204 |
| POST | `/api/v1/dbs/{name}/query` | executeQuery | `QueryRequest` | `QueryResult` |
| POST | `/api/v1/dbs/{name}/query/natural` | generateNaturalLanguageQuery | `NaturalLanguageQueryRequest` | `NaturalLanguageQueryResult` |

**验收标准**:
- [ ] 所有端点可通过 Swagger UI 测试
- [ ] 错误响应符合 `ErrorResponse` 格式
- [ ] `pytest backend/tests/integration/` 全部通过

---

### Phase 4: 前端基础设施 (Frontend Foundation)

**目标**: 搭建 React + Refine 项目骨架

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 4.1 | 初始化 Vite + React 项目 | `frontend/package.json` | [quickstart.md #前端设置](./quickstart.md#3-前端设置) |
| 4.2 | 配置 Tailwind CSS | `frontend/tailwind.config.js` | [research.md #Tailwind配置](./research.md#7-tailwind-css--ant-design-集成) |
| 4.3 | 配置 Refine + Ant Design | `frontend/src/App.tsx` | [research.md #Refine5](./research.md#5-refine-5) |
| 4.4 | 实现自定义 Data Provider | `frontend/src/providers/dataProvider.ts` | [research.md #自定义DataProvider](./research.md#5-refine-5) |
| 4.5 | 定义 TypeScript 类型 | `frontend/src/types/index.ts` | [data-model.md #TypeScript类型](./data-model.md#类型定义-typescript) |

**验收标准**:
- [ ] `yarn dev` 启动成功
- [ ] 访问 `http://localhost:5173` 显示 Refine 默认布局
- [ ] Data Provider 可以调用后端 API

---

### Phase 5: 前端组件实现 (Frontend Components)

**目标**: 实现所有 UI 组件

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 5.1 | 实现数据库列表组件 | `frontend/src/components/DatabaseList.tsx` | - |
| 5.2 | 实现 Schema 树形组件 | `frontend/src/components/SchemaTree.tsx` | - |
| 5.3 | 实现 SQL 编辑器组件 | `frontend/src/components/SqlEditor.tsx` | [research.md #Monaco编辑器](./research.md#6-monaco-editor-sql-编辑器) |
| 5.4 | 实现查询结果表格组件 | `frontend/src/components/QueryResults.tsx` | - |
| 5.5 | 实现自然语言输入组件 | `frontend/src/components/NaturalLanguageInput.tsx` | - |

**关键实现细节**:

**5.3 SQL 编辑器** → 参考 [research.md 第501-556行](./research.md#6-monaco-editor-sql-编辑器):
```typescript
// SqlEditor 组件
// - language="sql"
// - minimap: { enabled: false }
// - automaticLayout: true
// - 使用 memo + useCallback 优化性能
```

**验收标准**:
- [ ] SQL 编辑器支持语法高亮
- [ ] Schema 树形展示正常
- [ ] 查询结果表格支持分页/滚动

---

### Phase 6: 前端页面集成 (Frontend Pages)

**目标**: 实现完整的用户流程

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 6.1 | 实现数据库管理页面 | `frontend/src/pages/DatabasesPage.tsx` | [spec.md #用户故事1](./spec.md#用户故事-1---连接数据库并查看结构-优先级-p1) |
| 6.2 | 实现查询页面 | `frontend/src/pages/QueryPage.tsx` | [spec.md #用户故事2](./spec.md#用户故事-2---手动执行-sql-查询-优先级-p2) |
| 6.3 | 集成自然语言查询 | 同上 | [spec.md #用户故事3](./spec.md#用户故事-3---自然语言生成-sql-优先级-p3) |
| 6.4 | 实现错误处理和提示 | 全局 | [data-model.md #错误响应](./data-model.md#错误响应) |
| 6.5 | 编写组件测试 | `frontend/tests/components/*.test.tsx` | - |

**验收标准**:
- [ ] 完成用户故事 1: 添加数据库并查看结构
- [ ] 完成用户故事 2: 执行 SQL 查询并查看结果
- [ ] 完成用户故事 3: 自然语言生成 SQL

---

### Phase 7: 集成测试和优化 (Integration & Polish)

**目标**: 端到端测试，性能优化

| 步骤 | 任务 | 输出文件 | 参考文档 |
|------|------|----------|----------|
| 7.1 | 端到端测试 | - | [spec.md #验收场景](./spec.md) |
| 7.2 | 性能测试 (SC-001 ~ SC-003) | - | [spec.md #成功标准](./spec.md#可衡量的结果) |
| 7.3 | 边界情况测试 | - | [spec.md #边界情况](./spec.md#边界情况) |
| 7.4 | 更新文档 | `README.md`, `quickstart.md` | - |

**成功标准对照**:
- [ ] SC-001: 30 秒内完成数据库连接和结构展示
- [ ] SC-002: 100% 阻止非 SELECT 查询
- [ ] SC-003: 5 秒内返回查询结果 (<1000 行)
- [ ] SC-006: 所有错误显示用户友好消息

---

## 项目结构

### 文档 (本功能)

```text
specs/001-db-query-tool/
├── plan.md              # 本文件 - 实现计划和任务序列
├── spec.md              # 功能规范 - 用户故事和验收标准
├── research.md          # 技术研究 - 代码示例和最佳实践
├── data-model.md        # 数据模型 - SQLite schema 和 DTO
├── quickstart.md        # 快速入门 - 开发环境设置
├── contracts/           # API 契约
│   └── openapi.yaml     # OpenAPI 3.1 规范
└── tasks.md             # 任务分解 (/speckit.tasks 生成)
```

### 源代码与文档映射

```text
backend/
├── pyproject.toml           → [research.md #版本清单]
├── src/
│   ├── main.py              → [research.md #FastAPI + Pydantic v2]
│   ├── config.py
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       └── databases.py → [contracts/openapi.yaml]
│   ├── models/
│   │   ├── database.py      → [data-model.md #响应模型]
│   │   └── query.py         → [data-model.md #请求模型]
│   ├── services/
│   │   ├── metadata.py      → [research.md #psycopg 元数据提取]
│   │   ├── query.py         → [research.md #sqlglot SQL 解析]
│   │   └── llm.py           → [research.md #OpenAI SDK]
│   └── storage/
│       └── sqlite.py        → [data-model.md #SQLite 存储模型]
└── tests/

frontend/
├── package.json             → [research.md #版本清单]
├── tailwind.config.js       → [research.md #Tailwind CSS 配置]
├── src/
│   ├── App.tsx              → [research.md #Refine 5]
│   ├── components/
│   │   └── SqlEditor.tsx    → [research.md #Monaco Editor]
│   ├── providers/
│   │   └── dataProvider.ts  → [research.md #自定义 Data Provider]
│   └── types/
│       └── index.ts         → [data-model.md #TypeScript 类型]
└── tests/
```

---

## API 设计

基于用户输入，API 端点如下（完整定义见 [contracts/openapi.yaml](./contracts/openapi.yaml)）：

| 方法 | 路径 | 描述 | Phase |
|------|------|------|-------|
| GET | `/api/v1/dbs` | 获取所有已存储的数据库连接 | 3.1 |
| PUT | `/api/v1/dbs/{name}` | 添加/更新数据库连接 | 3.2 |
| GET | `/api/v1/dbs/{name}` | 获取数据库元数据 | 3.3 |
| DELETE | `/api/v1/dbs/{name}` | 删除数据库连接 | 3.4 |
| POST | `/api/v1/dbs/{name}/query` | 执行 SQL 查询 | 3.5 |
| POST | `/api/v1/dbs/{name}/query/natural` | 自然语言生成 SQL | 3.6 |

---

## 复杂度追踪

> 无需填写 - Constitution Check 无违规项

---

## 文档交叉引用索引

| 实现任务 | 主要参考文档 | 具体章节 |
|----------|--------------|----------|
| FastAPI 初始化 | research.md | [#1 FastAPI + Pydantic v2](./research.md#1-fastapi--pydantic-v2) |
| SQLite 存储 | data-model.md | [#SQLite 存储模型](./data-model.md#sqlite-存储模型) |
| Pydantic 模型 | data-model.md | [#API 数据传输对象](./data-model.md#api-数据传输对象-dto) |
| SQL 解析验证 | research.md | [#2 sqlglot](./research.md#2-sqlglot-sql-解析) |
| 元数据提取 | research.md | [#4 psycopg](./research.md#4-psycopg-postgresql-驱动) |
| 自然语言转SQL | research.md | [#3 OpenAI SDK](./research.md#3-openai-sdk-自然语言转-sql) |
| API 端点规范 | contracts/openapi.yaml | 全文 |
| 错误代码定义 | data-model.md | [#错误代码](./data-model.md#错误代码) |
| TypeScript 类型 | data-model.md | [#TypeScript 类型](./data-model.md#类型定义-typescript) |
| Refine 配置 | research.md | [#5 Refine 5](./research.md#5-refine-5) |
| Monaco 编辑器 | research.md | [#6 Monaco Editor](./research.md#6-monaco-editor-sql-编辑器) |
| Tailwind 配置 | research.md | [#7 Tailwind + Ant Design](./research.md#7-tailwind-css--ant-design-集成) |
| 用户验收标准 | spec.md | [#验收场景](./spec.md) |
| 成功指标 | spec.md | [#成功标准](./spec.md#可衡量的结果) |

---

## 下一步

运行以下命令生成详细任务分解：

```
/speckit.tasks
```
