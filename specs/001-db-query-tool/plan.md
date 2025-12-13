# Implementation Plan: Database Query Tool

**Branch**: `001-db-query-tool` | **Date**: 2025-12-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-db-query-tool/spec.md`

## Summary

A web-based database query tool that allows users to connect to PostgreSQL databases, browse schema metadata, execute SQL queries, and generate SQL from natural language descriptions. The backend provides a REST API for database management and query execution, while the frontend offers a rich UI with schema browsing and a Monaco-based SQL editor.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript 5.0+ (frontend)
**Primary Dependencies**:
- Backend: FastAPI, Pydantic v2, sqlglot, openai, psycopg2/asyncpg, aiosqlite
- Frontend: React 19+, Refine 5, Ant Design, Tailwind CSS 4+, Monaco Editor
**Storage**:
- Local: SQLite at `~/.db_query/db_query.db` (connection configs + cached metadata)
- Target: PostgreSQL databases (user-provided)
**Testing**: pytest (backend), vitest (frontend)
**Target Platform**: Web application (browser + local server)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Query results within 5 seconds, schema display within 30 seconds
**Constraints**: SELECT-only queries, LIMIT 1000 auto-append, CORS enabled for all origins
**Scale/Scope**: Single-user local tool, multiple database connections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status |
|-----------|-------------|--------|
| I. Ergonomic Python Backend | Idiomatic Python, clear naming, single-responsibility functions | ✅ Will comply |
| II. TypeScript Frontend | React + TypeScript with strict mode, explicit prop types | ✅ Will comply |
| III. Strict Type Annotations | Python type hints + TypeScript strict, mypy + tsc enforcement | ✅ Will comply |
| IV. Pydantic Data Models | All API schemas as Pydantic models with validation | ✅ Will comply |
| V. CamelCase JSON | `alias_generator = to_camel`, `by_alias=True` serialization | ✅ Will comply |
| No Authentication | Open access for all users | ✅ Will comply |

**Gate Status**: ✅ PASSED - All constitution principles will be followed.

## Project Structure

### Documentation (this feature)

```text
specs/001-db-query-tool/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
│   └── openapi.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root: w2/db_query/)

```text
w2/db_query/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Environment & app configuration
│   │   ├── models/              # Pydantic models (camelCase JSON)
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # CamelCase base model
│   │   │   ├── database.py      # DatabaseConnection, DatabaseMetadata
│   │   │   ├── query.py         # QueryRequest, QueryResult
│   │   │   └── natural.py       # NaturalQueryRequest, GeneratedSQL
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # Connection management
│   │   │   ├── metadata.py      # Schema extraction
│   │   │   ├── query.py         # SQL validation & execution
│   │   │   └── natural.py       # LLM-based SQL generation
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── dbs.py       # /api/v1/dbs/* endpoints
│   │   └── storage/             # SQLite persistence
│   │       ├── __init__.py
│   │       └── sqlite.py        # Local DB operations
│   └── tests/
│       ├── contract/            # API schema tests
│       ├── integration/         # End-to-end tests
│       └── unit/                # Service unit tests
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Refine app setup
│   │   ├── index.tsx            # Entry point
│   │   ├── types/               # TypeScript interfaces (match backend)
│   │   │   ├── index.ts
│   │   │   ├── database.ts      # DatabaseConnection, DatabaseMetadata
│   │   │   ├── query.ts         # QueryRequest, QueryResult
│   │   │   └── natural.ts       # NaturalQueryRequest, GeneratedSQL
│   │   ├── components/          # Reusable UI components
│   │   │   ├── SchemaTree/      # Database schema browser
│   │   │   ├── SqlEditor/       # Monaco Editor wrapper
│   │   │   ├── ResultTable/     # Query results display
│   │   │   └── NaturalInput/    # Natural language input
│   │   ├── pages/               # Refine resources/pages
│   │   │   ├── databases/       # Database list & detail
│   │   │   └── query/           # Query editor page
│   │   └── services/            # API client
│   │       └── api.ts           # Typed API client
│   ├── public/
│   ├── index.html
│   ├── tailwind.config.js
│   ├── tsconfig.json            # strict: true
│   └── vite.config.ts
│
├── pyproject.toml               # Backend Python dependencies
├── package.json                 # Frontend Node dependencies
└── README.md
```

**Structure Decision**: Web application with separate `backend/` and `frontend/` directories. Backend uses FastAPI with Pydantic models; frontend uses React + Refine 5 + Ant Design.

## Complexity Tracking

> No constitution violations. All principles will be followed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |
