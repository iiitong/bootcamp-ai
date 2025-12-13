# Research: Database Query Tool

**Date**: 2025-12-13
**Branch**: `001-db-query-tool`
**Purpose**: Document technology decisions and best practices for implementation

## Technology Decisions

### 1. SQL Parsing Library: sqlglot

**Decision**: Use `sqlglot` for SQL parsing, validation, and transformation.

**Rationale**:
- Pure Python implementation with no external dependencies
- Supports PostgreSQL dialect natively
- Can parse, transform, and generate SQL
- Provides AST-based validation (SELECT-only detection)
- Can modify queries programmatically (auto-add LIMIT clause)
- Active development and good documentation

**Alternatives Considered**:
| Library | Pros | Cons | Rejected Because |
|---------|------|------|------------------|
| sqlparse | Lightweight, widely used | Limited transformation capabilities | Cannot easily add LIMIT clause |
| pyparsing | Flexible, customizable | Requires building grammar from scratch | Too much implementation effort |
| pglast | PostgreSQL-specific, accurate | Requires libpg_query C extension | Adds build complexity |

**Implementation Notes**:
```python
import sqlglot
from sqlglot import exp

# Parse and validate SELECT-only
parsed = sqlglot.parse_one(sql, dialect="postgres")
if not isinstance(parsed, exp.Select):
    raise ValueError("Only SELECT queries are allowed")

# Add LIMIT if missing
if parsed.args.get("limit") is None:
    parsed = parsed.limit(1000)

# Generate back to SQL
validated_sql = parsed.sql(dialect="postgres")
```

### 2. PostgreSQL Driver: asyncpg

**Decision**: Use `asyncpg` for async PostgreSQL connections.

**Rationale**:
- Native async support for FastAPI integration
- High performance (C-based protocol implementation)
- Supports connection pooling
- Returns native Python types (no manual conversion)

**Alternatives Considered**:
| Library | Pros | Cons | Rejected Because |
|---------|------|------|------------------|
| psycopg2 | Mature, well-documented | Synchronous only | Blocks FastAPI event loop |
| psycopg3 | Modern, async support | Newer, less battle-tested | asyncpg has better performance |
| databases | ORM-agnostic abstraction | Extra layer of abstraction | Direct driver is simpler |

**Implementation Notes**:
```python
import asyncpg

async def execute_query(conn_url: str, sql: str) -> list[dict]:
    conn = await asyncpg.connect(conn_url)
    try:
        rows = await conn.fetch(sql)
        return [dict(row) for row in rows]
    finally:
        await conn.close()
```

### 3. Local Storage: aiosqlite

**Decision**: Use `aiosqlite` for local SQLite database operations.

**Rationale**:
- Async wrapper around standard sqlite3
- Consistent async pattern with asyncpg
- File-based storage at `~/.db_query/db_query.db`
- No additional server process needed

**Implementation Notes**:
- Store connection configs with encrypted URL (credentials protection)
- Cache metadata as JSON blobs per database
- Use migrations for schema versioning

### 4. LLM Integration: OpenAI SDK

**Decision**: Use official `openai` Python SDK with `OPENAI_API_KEY` environment variable.

**Rationale**:
- Official SDK with good async support
- GPT-4 provides high-quality SQL generation
- Well-documented API
- Environment variable configuration is secure

**Implementation Notes**:
```python
from openai import AsyncOpenAI

client = AsyncOpenAI()  # Uses OPENAI_API_KEY env var

async def generate_sql(prompt: str, schema_context: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Generate PostgreSQL SELECT queries. Schema:\n{schema_context}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1  # Low temperature for consistent SQL
    )
    return response.choices[0].message.content
```

### 5. Frontend Framework: Refine 5 + Ant Design

**Decision**: Use Refine 5 as the React meta-framework with Ant Design UI components.

**Rationale**:
- Refine provides headless CRUD operations out-of-the-box
- Ant Design offers production-ready data tables and forms
- Strong TypeScript support
- Built-in data provider pattern for API integration

**Alternatives Considered**:
| Framework | Pros | Cons | Rejected Because |
|-----------|------|------|------------------|
| Plain React | Maximum flexibility | More boilerplate | Refine reduces dev time |
| Next.js | SSR, file-based routing | Overkill for local tool | No SEO/SSR needed |
| Remix | Modern patterns | Newer, less ecosystem | Refine better for data-heavy UIs |

### 6. SQL Editor: Monaco Editor

**Decision**: Use Monaco Editor for SQL input with syntax highlighting.

**Rationale**:
- VS Code's editor component, familiar UX
- Built-in SQL language support
- Customizable completions (can add table/column names)
- React wrapper available (`@monaco-editor/react`)

**Implementation Notes**:
```tsx
import Editor from '@monaco-editor/react';

<Editor
  language="sql"
  theme="vs-dark"
  value={sql}
  onChange={setSql}
  options={{
    minimap: { enabled: false },
    lineNumbers: 'on',
  }}
/>
```

## Best Practices

### Pydantic CamelCase Configuration

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase input
    )

# All API models inherit from CamelModel
class DatabaseConnection(CamelModel):
    name: str
    url: str
    last_connected: datetime | None = None
```

### FastAPI Response Serialization

```python
from fastapi.responses import JSONResponse

# Ensure camelCase in responses
@app.get("/api/v1/dbs/{name}")
async def get_database(name: str) -> DatabaseMetadata:
    db = await get_db_metadata(name)
    return db.model_dump(by_alias=True)  # Forces camelCase output
```

### TypeScript Types (Matching Backend)

```typescript
// frontend/src/types/database.ts
export interface DatabaseConnection {
  name: string;
  url: string;
  lastConnected: string | null;  // camelCase matches API
}

export interface Column {
  name: string;
  dataType: string;
  isNullable: boolean;
  isPrimaryKey: boolean;
}
```

### Error Handling Pattern

```python
from fastapi import HTTPException

class QueryValidationError(Exception):
    """Raised when SQL validation fails"""
    pass

@app.exception_handler(QueryValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": "validation_error"}
    )
```

## Security Considerations

### Connection String Handling

- Store connection URLs in SQLite with base64 encoding (not encryption for MVP)
- Never log full connection URLs (mask passwords)
- Validate URL format before connecting

### SQL Injection Prevention

- sqlglot parsing rejects malicious SQL constructs
- SELECT-only validation prevents data modification
- Parameterized queries for internal SQLite operations

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # As specified in requirements
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Which SQL parser? | sqlglot - pure Python, good transformation support |
| Sync or async PostgreSQL? | asyncpg - native async for FastAPI |
| LLM provider? | OpenAI via OPENAI_API_KEY env var |
| Frontend framework? | Refine 5 + Ant Design |
| SQL editor component? | Monaco Editor |
