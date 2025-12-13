# Tasks: Database Query Tool

**Input**: Design documents from `/specs/001-db-query-tool/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/openapi.yaml

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 1: Setup & Foundation

**Goal**: Initialize project structure and core infrastructure for both backend and frontend

### Backend Setup

- [ ] T001 Create backend directory structure: `w2/db_query/backend/src/{models,services,api/v1,storage}/`
- [ ] T002 [P] Create `w2/db_query/backend/pyproject.toml` with dependencies (fastapi, pydantic, sqlglot, openai, asyncpg, aiosqlite)
- [ ] T003 [P] Create `w2/db_query/backend/src/__init__.py`
- [ ] T004 Create CamelCase base model in `w2/db_query/backend/src/models/base.py`
- [ ] T005 Create config module in `w2/db_query/backend/src/config.py` (OPENAI_API_KEY, DB path)
- [ ] T006 Create FastAPI app entry point in `w2/db_query/backend/src/main.py` with CORS middleware
- [ ] T007 Create SQLite storage module in `w2/db_query/backend/src/storage/sqlite.py` (init db, migrations)

### Frontend Setup

- [ ] T008 Initialize React + Vite project in `w2/db_query/frontend/`
- [ ] T009 [P] Configure TypeScript strict mode in `w2/db_query/frontend/tsconfig.json`
- [ ] T010 [P] Install dependencies: refine, antd, tailwindcss, @monaco-editor/react
- [ ] T011 [P] Configure Tailwind CSS in `w2/db_query/frontend/tailwind.config.js`
- [ ] T012 Create Refine app setup in `w2/db_query/frontend/src/App.tsx`
- [ ] T013 Create API client service in `w2/db_query/frontend/src/services/api.ts`

**Checkpoint**: Both backend and frontend can start without errors

---

## Phase 2: Core Features (US1 + US2)

**Goal**: Database connection, schema viewing, and SQL query execution

### Backend - Pydantic Models

- [ ] T014 [P] Create database models in `w2/db_query/backend/src/models/database.py` (DatabaseConnection, DatabaseMetadata, TableInfo, ColumnInfo)
- [ ] T015 [P] Create query models in `w2/db_query/backend/src/models/query.py` (QueryRequest, QueryResult, QueryError)
- [ ] T016 Create models `__init__.py` in `w2/db_query/backend/src/models/__init__.py`

### Backend - Services

- [ ] T017 Implement database connection service in `w2/db_query/backend/src/services/database.py` (connect, validate URL, mask URL)
- [ ] T018 Implement metadata extraction service in `w2/db_query/backend/src/services/metadata.py` (extract tables, views, columns from PostgreSQL)
- [ ] T019 Implement query service in `w2/db_query/backend/src/services/query.py` (parse with sqlglot, validate SELECT-only, add LIMIT, execute)

### Backend - API Endpoints

- [ ] T020 Implement database endpoints in `w2/db_query/backend/src/api/v1/dbs.py`:
  - GET /api/v1/dbs (list all)
  - PUT /api/v1/dbs/{name} (create/update)
  - GET /api/v1/dbs/{name} (get metadata)
  - DELETE /api/v1/dbs/{name}
  - POST /api/v1/dbs/{name}/refresh
  - POST /api/v1/dbs/{name}/query
- [ ] T021 Register router in `w2/db_query/backend/src/main.py`

### Frontend - TypeScript Types

- [ ] T022 [P] Create database types in `w2/db_query/frontend/src/types/database.ts`
- [ ] T023 [P] Create query types in `w2/db_query/frontend/src/types/query.ts`
- [ ] T024 Create types index in `w2/db_query/frontend/src/types/index.ts`

### Frontend - Components

- [ ] T025 Create SchemaTree component in `w2/db_query/frontend/src/components/SchemaTree/index.tsx` (tree view of tables/views/columns)
- [ ] T026 Create SqlEditor component in `w2/db_query/frontend/src/components/SqlEditor/index.tsx` (Monaco editor wrapper)
- [ ] T027 Create ResultTable component in `w2/db_query/frontend/src/components/ResultTable/index.tsx` (Ant Design Table)

### Frontend - Pages

- [ ] T028 Create database list page in `w2/db_query/frontend/src/pages/databases/list.tsx`
- [ ] T029 Create database detail page in `w2/db_query/frontend/src/pages/databases/show.tsx` (schema tree + add connection form)
- [ ] T030 Create query page in `w2/db_query/frontend/src/pages/query/index.tsx` (SQL editor + results)
- [ ] T031 Configure Refine resources and routes in `w2/db_query/frontend/src/App.tsx`

**Checkpoint**: User can add database, view schema, write and execute SQL queries

---

## Phase 3: Natural Language SQL (US3)

**Goal**: Generate SQL queries from natural language descriptions using LLM

### Backend

- [ ] T032 [P] Create natural query models in `w2/db_query/backend/src/models/natural.py` (NaturalQueryRequest, GeneratedSQL)
- [ ] T033 Implement natural language service in `w2/db_query/backend/src/services/natural.py` (OpenAI integration, schema context building)
- [ ] T034 Add natural query endpoint in `w2/db_query/backend/src/api/v1/dbs.py`: POST /api/v1/dbs/{name}/query/natural

### Frontend

- [ ] T035 [P] Create natural query types in `w2/db_query/frontend/src/types/natural.ts`
- [ ] T036 Create NaturalInput component in `w2/db_query/frontend/src/components/NaturalInput/index.tsx` (text input + generate button)
- [ ] T037 Integrate NaturalInput into query page in `w2/db_query/frontend/src/pages/query/index.tsx`

**Checkpoint**: User can describe query in natural language and get generated SQL

---

## Dependencies & Execution Order

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Core: US1 + US2)
    │
    ▼
Phase 3 (Advanced: US3)
```

### Within Phase 2

```
Models (T014-T016) ──▶ Services (T017-T019) ──▶ API (T020-T021)
                                                      │
Types (T022-T024) ──▶ Components (T025-T027) ──▶ Pages (T028-T031)
```

### Parallel Opportunities

**Phase 1**:
- T002, T003 can run in parallel
- T009, T010, T011 can run in parallel

**Phase 2**:
- T014, T015 (backend models) can run in parallel
- T022, T023 (frontend types) can run in parallel

**Phase 3**:
- T032, T035 (models/types) can run in parallel

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1 | T001-T013 | Setup & Foundation |
| Phase 2 | T014-T031 | Core Features (DB + SQL) |
| Phase 3 | T032-T037 | Natural Language SQL |
| **Total** | **37 tasks** | |

### MVP Scope

**Phase 1 + Phase 2** delivers a fully functional database query tool:
- Add/manage PostgreSQL connections
- Browse database schema (tables, views, columns)
- Write and execute SQL queries with validation

**Phase 3** adds AI-powered query generation as an enhancement.
