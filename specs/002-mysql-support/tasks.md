# Tasks: MySQL 数据库支持

**Input**: Design documents from `/specs/002-mysql-support/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: 未显式要求 TDD，不包含测试任务。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `w2/db_query/backend/` 为后端根目录
- 源码: `w2/db_query/backend/src/`
- 测试: `w2/db_query/backend/tests/`
- 脚本: `w2/db_query/backend/scripts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 添加依赖和项目配置

- [x] T001 添加 aiomysql 依赖到 w2/db_query/backend/pyproject.toml
- [x] T002 [P] 创建数据库类型检测工具函数 detect_db_type() 在 w2/db_query/backend/src/utils/db_utils.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 修改存储层和模型以支持多数据库类型，为所有用户故事提供基础

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 修改 SQLite 存储添加 db_type 列迁移逻辑在 w2/db_query/backend/src/storage/sqlite.py
- [x] T004 修改 DatabaseInfo 模型添加 db_type 字段在 w2/db_query/backend/src/models/database.py
- [x] T005 [P] 修改 DatabaseMetadata 模型添加 db_type 字段在 w2/db_query/backend/src/models/database.py
- [x] T006 修改 list_connections() 返回 db_type 在 w2/db_query/backend/src/storage/sqlite.py
- [x] T007 修改 upsert_connection() 保存 db_type 在 w2/db_query/backend/src/storage/sqlite.py
- [x] T008 修改 get_connection() 返回 db_type 在 w2/db_query/backend/src/storage/sqlite.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 添加 MySQL 数据库连接 (Priority: P1) 🎯 MVP

**Goal**: 用户可以添加、查看、删除 MySQL 数据库连接，密码掩码显示

**Independent Test**: 通过 PUT /dbs/{name} 添加 MySQL 连接，GET /dbs 查看列表，DELETE /dbs/{name} 删除连接

### Implementation for User Story 1

- [x] T009 [US1] 修改 DatabaseCreateRequest 模型验证支持 mysql:// URL 前缀在 w2/db_query/backend/src/models/database.py
- [x] T010 [US1] 实现 MySQL 连接测试函数 test_mysql_connection() 在 w2/db_query/backend/src/services/metadata_mysql.py
- [x] T011 [US1] 修改 PUT /dbs/{name} 端点支持 MySQL 连接类型检测和保存在 w2/db_query/backend/src/api/v1/databases.py
- [x] T012 [US1] 修改 GET /dbs 端点返回 dbType 字段在 w2/db_query/backend/src/api/v1/databases.py
- [x] T013 [US1] 修改 _mask_password() 支持 mysql:// URL 格式在 w2/db_query/backend/src/storage/sqlite.py
- [x] T014 [US1] 修改 DELETE /dbs/{name} 端点确保删除 MySQL 连接及其缓存在 w2/db_query/backend/src/api/v1/databases.py

**Checkpoint**: User Story 1 complete - MySQL 连接 CRUD 功能可独立验证

---

## Phase 4: User Story 2 - 提取 MySQL 数据库元数据 (Priority: P1)

**Goal**: 系统能从 MySQL information_schema 提取表、视图、列信息，包括主键外键标识

**Independent Test**: 添加 MySQL 连接后通过 GET /dbs/{name} 查看完整数据库结构

### Implementation for User Story 2

- [x] T015 [P] [US2] 创建 MySQL 元数据查询常量 MYSQL_TABLES_QUERY 和 MYSQL_COLUMNS_QUERY 在 w2/db_query/backend/src/services/metadata_mysql.py
- [x] T016 [US2] 实现 MySQLMetadataExtractor.extract() 异步元数据提取方法在 w2/db_query/backend/src/services/metadata_mysql.py
- [x] T017 [US2] 修改 PUT /dbs/{name} 端点在 MySQL 连接成功后调用 MySQL 元数据提取在 w2/db_query/backend/src/api/v1/databases.py
- [x] T018 [US2] 修改 GET /dbs/{name}?refresh=true 端点支持刷新 MySQL 元数据在 w2/db_query/backend/src/api/v1/databases.py
- [x] T019 [US2] 处理空数据库（无表无视图）场景返回空元数据在 w2/db_query/backend/src/services/metadata_mysql.py

**Checkpoint**: User Story 2 complete - MySQL 元数据提取功能可独立验证

---

## Phase 5: User Story 3 - 执行 MySQL 查询 (Priority: P1)

**Goal**: 用户可对 MySQL 执行 SELECT 查询，支持自动 LIMIT、超时控制、语法验证

**Independent Test**: 通过 POST /dbs/{name}/query 执行 MySQL SELECT 查询并获取结果

### Implementation for User Story 3

- [x] T020 [US3] 修改 SQLProcessor.process() 添加 dialect 参数支持 MySQL 方言在 w2/db_query/backend/src/services/query.py
- [x] T021 [P] [US3] 创建 MySQLQueryExecutor 类实现 MySQL 查询执行在 w2/db_query/backend/src/services/query_mysql.py
- [x] T022 [US3] 实现 MySQL 查询超时控制 SET max_execution_time 在 w2/db_query/backend/src/services/query_mysql.py
- [x] T023 [US3] 修改 POST /dbs/{name}/query 端点根据 db_type 选择正确的处理器和执行器在 w2/db_query/backend/src/api/v1/databases.py
- [x] T024 [US3] 添加 MySQL 查询错误处理（超时、语法错误、连接失败）在 w2/db_query/backend/src/services/query_mysql.py

**Checkpoint**: User Story 3 complete - MySQL 查询执行功能可独立验证

---

## Phase 6: User Story 4 - 自然语言生成 MySQL 查询 (Priority: P2)

**Goal**: LLM 能根据数据库类型生成正确语法的 MySQL SQL

**Independent Test**: 通过 POST /dbs/{name}/query/natural 输入自然语言，验证生成的 SQL 使用 MySQL 语法

### Implementation for User Story 4

- [x] T025 [US4] 修改 TextToSQLGenerator 添加 db_type 参数在 w2/db_query/backend/src/services/llm.py
- [x] T026 [US4] 修改系统提示词模板支持 MySQL 语法规则（反引号标识符、MySQL 函数）在 w2/db_query/backend/src/services/llm.py
- [x] T027 [US4] 修改 generate() 方法根据 db_type 选择正确的提示词在 w2/db_query/backend/src/services/llm.py
- [x] T028 [US4] 修改 POST /dbs/{name}/query/natural 端点传递 db_type 给 LLM 在 w2/db_query/backend/src/api/v1/databases.py

**Checkpoint**: User Story 4 complete - 自然语言生成 MySQL SQL 功能可独立验证

---

## Phase 7: User Story 5 - 测试数据库设置 (Priority: P2)

**Goal**: 提供电商领域测试数据库创建脚本，包含 5 张表和 1000+ 条订单数据

**Independent Test**: 运行脚本后通过 mysql -u root 验证数据库和数据创建成功

### Implementation for User Story 5

- [x] T029 [P] [US5] 创建测试数据库 DDL 脚本（users, products, orders, payments, reviews 表结构）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T030 [US5] 添加测试用户数据生成（100 条记录）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T031 [US5] 添加测试产品数据生成（50 条记录）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T032 [US5] 添加测试订单数据生成（1500 条记录，满足 1000+ 要求）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T033 [US5] 添加测试支付数据生成（1200 条记录）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T034 [US5] 添加测试评价数据生成（300 条记录）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql
- [x] T035 [US5] 添加脚本幂等性支持（DROP DATABASE IF EXISTS + CREATE DATABASE）在 w2/db_query/backend/scripts/setup_mysql_testdb.sql

**Checkpoint**: User Story 5 complete - 测试数据库脚本功能可独立验证

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T036 [P] 添加 MySQL 连接错误码 LLM_NOT_CONFIGURED 的处理在 w2/db_query/backend/src/models/errors.py
- [x] T037 [P] 运行 quickstart.md 验证流程确认所有功能正常
- [x] T038 确保所有 MySQL 功能对现有 PostgreSQL 功能无影响（回归验证）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User Story 1 (P1): 连接管理 - 无其他故事依赖
  - User Story 2 (P1): 元数据提取 - 依赖 US1 的连接功能
  - User Story 3 (P1): 查询执行 - 依赖 US1 的连接功能
  - User Story 4 (P2): 自然语言 SQL - 依赖 US2 的元数据和 US3 的查询
  - User Story 5 (P2): 测试数据库 - 独立，可与其他故事并行
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
                    ┌──────────────────────────────────────┐
                    │          Phase 2: Foundational       │
                    │  (T003-T008 存储层和模型修改)         │
                    └───────────────────┬──────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐               ┌───────────────┐               ┌───────────────┐
│  US1: 连接管理 │               │  US5: 测试DB   │               │               │
│   (T009-T014)  │               │  (T029-T035)  │               │  (可并行)      │
└───────┬───────┘               └───────────────┘               └───────────────┘
        │
        ├───────────────────────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐               ┌───────────────┐
│ US2: 元数据提取│               │ US3: 查询执行  │
│  (T015-T019)  │               │  (T020-T024)  │
└───────┬───────┘               └───────┬───────┘
        │                               │
        └───────────────┬───────────────┘
                        │
                        ▼
                ┌───────────────┐
                │US4: 自然语言SQL│
                │  (T025-T028)  │
                └───────────────┘
```

### Within Each User Story

- Core implementation before integration
- Models/utilities before services
- Services before API endpoints
- Story complete before moving to dependent stories

### Parallel Opportunities

- T002 可与 T001 并行（不同文件）
- T004, T005 可并行（同一文件但不同模型）
- T015, T021 可并行（不同文件）
- T029 可与 US1-US4 并行（独立脚本）
- T036, T037 可并行（不同关注点）

---

## Parallel Example: User Story 3

```bash
# Launch parallel tasks for User Story 3:
Task: "修改 SQLProcessor.process() 添加 dialect 参数" in query.py
Task: "创建 MySQLQueryExecutor 类" in query_mysql.py  # [P] 可并行
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 + 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (连接管理)
4. Complete Phase 4: User Story 2 (元数据提取)
5. Complete Phase 5: User Story 3 (查询执行)
6. **STOP and VALIDATE**: Test MySQL 基础功能可用

### Incremental Delivery

1. Phase 1-2: 基础设施 → 准备完成
2. US1: 连接管理 → 可添加删除 MySQL 连接
3. US2: 元数据提取 → 可查看数据库结构
4. US3: 查询执行 → 核心 MVP 完成
5. US4: 自然语言 SQL → 增强功能
6. US5: 测试数据库 → 开发验证工具
7. Phase 8: 收尾 → 发布准备

### Parallel Team Strategy

With multiple developers:
1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2
   - Developer B: User Story 3
   - Developer C: User Story 5 (独立)
3. US4 等 US2+US3 完成后开始

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
