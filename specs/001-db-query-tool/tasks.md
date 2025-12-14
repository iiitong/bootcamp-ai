# Tasks: 数据库查询工具 (DB Query Tool)

**Input**: Design documents from `/specs/001-db-query-tool/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Organization**: 按用户要求简化为 3 个阶段，涵盖后端、前端及集成。

**更新**: 2025-12-14 - 新增用户故事 2.1 (导出查询结果) 相关任务

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 关联的用户故事 (US1, US2, US2.1, US3)

## Path Conventions

- **后端**: `backend/src/`, `backend/tests/`
- **前端**: `frontend/src/`, `frontend/tests/`

---

## Phase 1: 后端完整实现 (Backend Complete)

**目标**: 完成所有后端 API，支持全部 3 个用户故事

**验收标准**:
- 所有 6 个 API 端点可通过 Swagger UI 测试
- `uv run pytest` 测试通过

### 1.1 项目初始化

- [x] T001 [P] 创建 `backend/pyproject.toml`，配置 Python 3.14+ 和所有依赖 (fastapi, pydantic, sqlglot, openai, psycopg)
- [x] T002 [P] 创建 `backend/src/__init__.py` 包初始化文件
- [x] T003 创建 `backend/src/config.py`，实现环境变量配置 (OPENAI_API_KEY, DB_QUERY_DATA_DIR)

### 1.2 数据模型 (Pydantic DTOs)

> 参考: [data-model.md #API数据传输对象](./data-model.md#api-数据传输对象-dto)

- [x] T004 [P] 创建 `backend/src/models/__init__.py` 包初始化
- [x] T005 [P] 创建 `backend/src/models/database.py`，实现 DatabaseInfo, ColumnInfo, TableInfo, DatabaseMetadata 模型
- [x] T006 [P] 创建 `backend/src/models/query.py`，实现 QueryRequest, QueryResult, NaturalLanguageQueryRequest, NaturalLanguageQueryResult 模型
- [x] T007 [P] 创建 `backend/src/models/errors.py`，实现 ErrorResponse 模型和错误代码枚举

### 1.3 存储层 (SQLite)

> 参考: [data-model.md #SQLite存储模型](./data-model.md#sqlite-存储模型)

- [x] T008 创建 `backend/src/storage/__init__.py` 包初始化
- [x] T009 创建 `backend/src/storage/sqlite.py`，实现 SQLiteStorage 类:
  - 初始化数据库 (~/.db_query/db_query.db)
  - connections 表 CRUD 操作
  - metadata_cache 表 CRUD 操作

### 1.4 核心服务层

> 参考: [research.md #核心库代码示例](./research.md)

- [x] T010 创建 `backend/src/services/__init__.py` 包初始化
- [x] T011 [US1] 创建 `backend/src/services/metadata.py`，实现 PostgreSQL 元数据提取:
  - 使用 psycopg 连接 PostgreSQL
  - 查询 information_schema 获取表/视图/列信息
  - 参考 research.md #psycopg 元数据提取
- [x] T012 [US2] 创建 `backend/src/services/query.py`，实现 SQL 验证和执行:
  - SQLProcessor 类: 解析、验证 SELECT、添加 LIMIT
  - 参考 research.md #sqlglot SQL 解析
- [x] T013 [US3] 创建 `backend/src/services/llm.py`，实现自然语言转 SQL:
  - TextToSQLGenerator 类: 设置 schema context、调用 OpenAI API
  - 参考 research.md #OpenAI SDK

### 1.5 API 端点

> 参考: [contracts/openapi.yaml](./contracts/openapi.yaml)

- [x] T014 创建 `backend/src/api/__init__.py` 包初始化
- [x] T015 创建 `backend/src/api/v1/__init__.py` 包初始化
- [x] T016 [US1] 创建 `backend/src/api/v1/databases.py`，实现数据库管理端点:
  - GET /api/v1/dbs - 获取所有连接
  - PUT /api/v1/dbs/{name} - 添加/更新连接
  - GET /api/v1/dbs/{name} - 获取元数据
  - DELETE /api/v1/dbs/{name} - 删除连接
- [x] T017 [US2] 在 `backend/src/api/v1/databases.py` 添加查询端点:
  - POST /api/v1/dbs/{name}/query - 执行 SQL 查询
- [x] T018 [US3] 在 `backend/src/api/v1/databases.py` 添加自然语言端点:
  - POST /api/v1/dbs/{name}/query/natural - 自然语言生成 SQL
- [x] T019 创建 `backend/src/api/v1/router.py`，配置路由和异常处理

### 1.6 应用入口

- [x] T020 创建 `backend/src/main.py`:
  - FastAPI 应用实例
  - CORS 配置 (允许所有 origin)
  - 路由挂载
  - 参考 research.md #FastAPI + Pydantic v2

### 1.7 后端测试

- [x] T021 [P] 创建 `backend/tests/__init__.py`
- [x] T022 [P] 创建 `backend/tests/test_sql_processor.py`，测试 SQL 验证:
  - SELECT 通过、非 SELECT 拒绝、LIMIT 自动添加
- [x] T023 [P] 创建 `backend/tests/test_storage.py`，测试 SQLite 存储层

**Phase 1 检查点**:
```bash
cd backend && uv sync && uv run uvicorn src.main:app --reload --port 8000
# 访问 http://localhost:8000/docs 验证 API
```

---

## Phase 2: 前端完整实现 (Frontend Complete)

**目标**: 完成 React + Refine 前端，实现完整用户界面

**验收标准**:
- `yarn dev` 启动成功
- 可以添加数据库、查看结构、执行查询、生成 SQL

### 2.1 项目初始化

- [x] T024 [P] 创建 `frontend/package.json`，配置依赖 (react, refine, antd, monaco-editor, tailwindcss)
- [x] T025 [P] 创建 `frontend/tsconfig.json`，TypeScript 配置
- [x] T026 [P] 创建 `frontend/vite.config.ts`，Vite 配置
- [x] T027 [P] 创建 `frontend/tailwind.config.js`，Tailwind CSS 配置
- [x] T028 [P] 创建 `frontend/postcss.config.js`，PostCSS 配置
- [x] T029 创建 `frontend/index.html`，HTML 入口

### 2.2 类型定义

> 参考: [data-model.md #TypeScript类型](./data-model.md#类型定义-typescript)

- [x] T030 创建 `frontend/src/types/index.ts`，定义所有 TypeScript 类型:
  - DatabaseInfo, ColumnInfo, TableInfo, DatabaseMetadata
  - QueryResult, NaturalLanguageQueryResult, ErrorResponse

### 2.3 Refine 配置

> 参考: [research.md #Refine 5](./research.md#5-refine-5)

- [x] T031 创建 `frontend/src/providers/dataProvider.ts`，自定义 Data Provider:
  - 实现 getList, getOne, create, update, deleteOne
  - 连接后端 API (http://localhost:8000)
- [x] T032 创建 `frontend/src/App.tsx`，Refine 应用入口:
  - 配置 Ant Design 主题
  - 配置 dataProvider
  - 配置路由

### 2.4 UI 组件

> 参考: [research.md #Monaco Editor](./research.md#6-monaco-editor-sql-编辑器)

- [x] T033 [P] 创建 `frontend/src/components/DatabaseList.tsx`，数据库连接列表组件
- [x] T034 [P] 创建 `frontend/src/components/SchemaTree.tsx`，Schema 树形展示组件
- [x] T035 [P] 创建 `frontend/src/components/SqlEditor.tsx`，Monaco SQL 编辑器组件
- [x] T036 [P] 创建 `frontend/src/components/QueryResults.tsx`，查询结果表格组件
- [x] T037 [P] 创建 `frontend/src/components/NaturalLanguageInput.tsx`，自然语言输入组件

### 2.5 导出功能 (新增 - US2.1)

> 参考: [research.md #8 查询结果导出](./research.md#8-查询结果导出-新增)
> 参考: [data-model.md #导出功能](./data-model.md#导出功能-前端)

**说明**: 导出功能完全在前端实现，无需后端 API

- [x] T054 [P] [US2.1] 创建 `frontend/src/utils/export.ts`，实现 exportToCSV 函数:
  - UTF-8 with BOM 编码确保 Excel 正确显示中文
  - 正确转义逗号、换行符、双引号
  - 生成 query_result_YYYYMMDD_HHMMSS.csv 文件名
- [x] T055 [P] [US2.1] 在 `frontend/src/utils/export.ts` 添加 exportToJSON 函数:
  - 输出简单数组格式 [{col1: val1}, ...]
  - 生成 query_result_YYYYMMDD_HHMMSS.json 文件名
- [x] T056 [P] [US2.1] 在 `frontend/src/utils/export.ts` 添加 downloadBlob 辅助函数:
  - 使用 Blob + URL.createObjectURL 触发下载
  - 下载后清理临时 URL
- [x] T057 [US2.1] 创建 `frontend/src/components/ExportButtons.tsx`，导出按钮组件:
  - CSV 导出按钮
  - JSON 导出按钮
  - 无结果时隐藏或禁用按钮
- [x] T058 [US2.1] 集成 ExportButtons 到 QueryResults.tsx 组件:
  - 在结果表格上方或下方显示导出按钮
  - 传递 columns 和 rows 数据给导出函数
- [x] T059 [P] [US2.1] 创建 `frontend/tests/unit/export.test.ts`，导出功能单元测试:
  - 测试 CSV 包含 UTF-8 BOM
  - 测试特殊字符正确转义
  - 测试文件名格式正确
  - 测试 JSON 格式正确

### 2.6 页面实现

- [x] T038 [US1] 创建 `frontend/src/pages/databases/list.tsx`，数据库管理页面:
  - 显示已保存的数据库连接列表
  - 添加新连接表单
  - 删除连接功能
- [x] T039 [US1] 创建 `frontend/src/pages/databases/show.tsx`，数据库详情页面:
  - 显示 Schema 树形结构
  - 表/视图详细信息
  - 刷新元数据功能
- [x] T040 [US2][US3] 创建 `frontend/src/pages/query/index.tsx`，查询页面:
  - SQL 编辑器 (Monaco)
  - 执行按钮和结果表格
  - 自然语言输入区域
  - 生成的 SQL 预览和编辑

### 2.7 样式和入口

- [x] T041 创建 `frontend/src/index.css`，全局样式 (Tailwind 导入)
- [x] T042 创建 `frontend/src/main.tsx`，React 入口文件

**Phase 2 检查点**:
```bash
cd frontend && yarn install && yarn dev
# 访问 http://localhost:5173 验证界面
```

---

## Phase 3: 集成测试和优化 (Integration & Polish)

**目标**: 端到端验证，确保所有用户故事满足验收标准

**验收标准**:
- SC-001: 30 秒内完成数据库连接和结构展示
- SC-002: 100% 阻止非 SELECT 查询
- SC-003: 5 秒内返回查询结果 (<1000 行)
- SC-009: 导出 2 秒内完成下载 (1000 行以内)
- SC-010: CSV 在 Excel 中打开时中文正确显示

### 3.1 端到端验证

- [x] T043 [US1] 验证用户故事 1: 添加 PostgreSQL 连接并查看表结构
- [x] T044 [US2] 验证用户故事 2: 执行 SELECT 查询并查看表格结果
- [x] T060 [US2.1] 验证用户故事 2.1: 执行查询后导出 CSV 和 JSON 文件
  - 验证 CSV 文件在 Excel 中打开时中文正确显示
  - 验证 JSON 文件格式正确
  - 验证文件名格式 query_result_YYYYMMDD_HHMMSS
- [x] T045 [US3] 验证用户故事 3: 自然语言描述生成 SQL 并执行

### 3.2 边界情况测试

> 参考: [spec.md #边界情况](./spec.md)

- [x] T046 测试空数据库场景 (无表/视图)
- [x] T047 测试连接失败场景 (无效 URL、网络错误)
- [x] T048 测试非 SELECT 查询拒绝 (INSERT/UPDATE/DELETE/DROP)
- [x] T049 测试 LIMIT 自动添加
- [x] T050 测试 LLM 服务不可用场景
- [x] T061 [US2.1] 测试导出空结果场景 (0 行时按钮禁用)
- [x] T062 [US2.1] 测试 CSV 特殊字符转义 (逗号、换行、双引号)

### 3.3 文档更新

- [x] T051 [P] 更新 `backend/README.md`，后端使用说明
- [x] T052 [P] 更新 `frontend/README.md`，前端使用说明
- [x] T053 验证 quickstart.md 步骤可执行

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (后端) ──────────────────────────────────┐
                                                 ├──▶ Phase 3 (集成)
Phase 2 (前端) ──────────────────────────────────┘
```

- **Phase 1 和 Phase 2 可以并行开发** (前端可以使用 mock 数据)
- **Phase 3 必须等待 Phase 1 和 Phase 2 完成**

### Within Phase 1 (后端)

```
T001-T003 (初始化)
    ↓
T004-T007 (模型) ──[P]──▶ 可并行
    ↓
T008-T009 (存储)
    ↓
T010-T013 (服务) ──[部分P]──▶ T011/T012/T013 可并行
    ↓
T014-T019 (API)
    ↓
T020 (入口)
    ↓
T021-T023 (测试) ──[P]──▶ 可并行
```

### Within Phase 2 (前端)

```
T024-T029 (初始化) ──[P]──▶ 可并行
    ↓
T030 (类型)
    ↓
T031-T032 (Refine)
    ↓
T033-T037 (组件) ──[P]──▶ 可并行
    ↓
T038-T040 (页面)
    ↓
T041-T042 (入口)
```

---

## Parallel Example

```bash
# Phase 1 中可并行的任务:
T004, T005, T006, T007  # 所有模型文件
T011, T012, T013        # 三个核心服务 (元数据、查询、LLM)
T021, T022, T023        # 所有测试文件

# Phase 2 中可并行的任务:
T024, T025, T026, T027, T028  # 所有配置文件
T033, T034, T035, T036, T037  # 所有组件
T054, T055, T056              # 导出工具函数 (US2.1)
T059                          # 导出单元测试 (US2.1)
```

---

## Implementation Strategy

### 推荐执行顺序 (单人开发)

1. **Phase 1 全部** → 验证 API (Swagger UI)
2. **Phase 2 全部** → 验证界面 (http://localhost:5173)
3. **Phase 3 全部** → 端到端验证

### 并行开发策略 (多人团队)

- **开发者 A**: Phase 1 (后端)
- **开发者 B**: Phase 2 (前端，使用 mock 数据)
- **共同**: Phase 3 (集成测试)

---

## Summary

| Phase | 任务数 | 可并行任务 | 关联用户故事 |
|-------|--------|------------|--------------|
| Phase 1: 后端 | 23 | 11 | US1, US2, US3 |
| Phase 2: 前端 | 25 | 14 | US1, US2, US2.1, US3 |
| Phase 3: 集成 | 14 | 2 | 全部 |
| **总计** | **62** | **27** | - |

### 新增任务 (US2.1 导出功能)

| 任务 ID | 描述 | 类型 |
|---------|------|------|
| T054 | exportToCSV 函数 | 前端工具 |
| T055 | exportToJSON 函数 | 前端工具 |
| T056 | downloadBlob 辅助函数 | 前端工具 |
| T057 | ExportButtons 组件 | 前端组件 |
| T058 | 集成到 QueryResults | 前端集成 |
| T059 | 导出单元测试 | 测试 |
| T060 | US2.1 端到端验证 | 集成测试 |
| T061 | 空结果测试 | 边界测试 |
| T062 | CSV 特殊字符测试 | 边界测试 |

### MVP 交付顺序

1. **MVP v0.1**: Phase 1 完成 → 可通过 API 使用全部功能
2. **MVP v0.2**: Phase 1 + Phase 2 (不含 US2.1) → 完整 Web 界面
3. **MVP v0.3**: Phase 1 + Phase 2 (含 US2.1) → 支持导出功能
4. **Release v1.0**: Phase 1 + Phase 2 + Phase 3 完成 → 生产就绪
