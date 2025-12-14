# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐ │
│  │ Database  │  │  Schema   │  │   Query   │  │    Export     │ │
│  │   List    │  │   Tree    │  │  Editor   │  │   Buttons     │ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └───────┬───────┘ │
└────────┼──────────────┼──────────────┼────────────────┼─────────┘
         │              │              │                │
         └──────────────┼──────────────┼────────────────┘
                        │              │
                        ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    API Layer (/api/v1)                       ││
│  │  GET /dbs          PUT /dbs/{name}      POST /dbs/{name}/query│
│  │  GET /dbs/{name}   DELETE /dbs/{name}   POST /dbs/{name}/query/natural│
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                    Service Layer                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│  │
│  │  │  Metadata   │  │   Query     │  │   LLM (Text2SQL)    ││  │
│  │  │  Extractor  │  │  Executor   │  │    Generator        ││  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘│  │
│  └─────────┼────────────────┼───────────────────┼────────────┘  │
│            │                │                   │                │
│  ┌─────────┼────────────────┼───────────────────┼────────────┐  │
│  │         ▼                ▼                   ▼            │  │
│  │  ┌─────────────────────────────┐    ┌───────────────────┐│  │
│  │  │     PostgreSQL (Target)     │    │   OpenAI API      ││  │
│  │  │     psycopg3 async          │    │   (Compatible)    ││  │
│  │  └─────────────────────────────┘    └───────────────────┘│  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                    Storage Layer                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              SQLite (Local Storage)                  │  │  │
│  │  │   - Database connections                             │  │  │
│  │  │   - Metadata cache                                   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Backend Components

### API Layer (`src/api/`)

FastAPI router handling HTTP requests.

```
api/
└── v1/
    ├── __init__.py      # Router aggregation
    ├── router.py        # Version prefix setup
    └── databases.py     # All database endpoints
```

**Key Responsibilities:**
- Request validation using Pydantic
- Error handling and HTTP status codes
- Dependency injection for services

### Models (`src/models/`)

Pydantic models for data validation and serialization.

```
models/
├── database.py    # DatabaseInfo, DatabaseMetadata, TableInfo
├── query.py       # QueryRequest, QueryResult, NaturalLanguageQuery
└── errors.py      # ErrorResponse, ErrorCode enum
```

### Services (`src/services/`)

Business logic layer.

```
services/
├── metadata.py    # MetadataExtractor - schema introspection
├── query.py       # QueryExecutor, SQLProcessor
└── llm.py         # TextToSQLGenerator
```

#### MetadataExtractor
- Connects to PostgreSQL using psycopg3
- Queries information_schema for tables/columns
- Extracts primary keys and foreign keys
- Returns structured TableInfo objects

#### QueryExecutor
- Async query execution with timeout
- Returns columns and rows as structured result

#### SQLProcessor
- Uses sqlglot for SQL parsing
- Validates SELECT-only queries
- Auto-injects LIMIT clause
- Blocks dangerous statements (DROP, DELETE, etc.)

#### TextToSQLGenerator
- Integrates with OpenAI-compatible APIs
- Builds schema context from metadata
- Generates SQL from natural language prompts

### Storage (`src/storage/`)

Local persistence using SQLite.

```
storage/
└── sqlite.py      # SQLiteStorage class
```

**Tables:**
- `connections` - Database connection URLs
- `metadata_cache` - Cached schema information

**Features:**
- Password masking in stored URLs
- JSON serialization for metadata
- Upsert operations for connections

### Configuration (`src/config.py`)

Settings management using pydantic-settings.

```python
class Settings:
    data_dir: Path          # Local data storage path
    default_query_limit: int = 1000
    query_timeout_seconds: int = 30
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str = "gpt-4o-mini"
```

## Frontend Components

### Pages (`src/pages/`)

```
pages/
├── databases/
│   ├── list.tsx    # Database list page
│   └── show.tsx    # Database detail/schema page
└── query/
    └── index.tsx   # SQL query interface
```

### Components (`src/components/`)

```
components/
├── DatabaseList.tsx       # Database connection list
├── SchemaTree.tsx         # Schema browser tree view
├── SqlEditor.tsx          # Monaco-based SQL editor
├── QueryResults.tsx       # Result table display
├── ExportButtons.tsx      # CSV/JSON export
└── NaturalLanguageInput.tsx  # NL to SQL input
```

### Data Flow

1. **Database Connection**
   ```
   User Input → PUT /dbs/{name} → MetadataExtractor → SQLite Cache
   ```

2. **Schema Browsing**
   ```
   Page Load → GET /dbs/{name} → SQLite Cache → SchemaTree Component
   ```

3. **Query Execution**
   ```
   SQL Input → POST /dbs/{name}/query → SQLProcessor → QueryExecutor → Results
   ```

4. **Natural Language Query**
   ```
   NL Prompt → POST /dbs/{name}/query/natural → LLM → Generated SQL → User Review
   ```

## Security Considerations

### Query Safety
- Only SELECT statements allowed
- Auto LIMIT 1000 prevents large result sets
- Query timeout prevents long-running queries
- SQL injection prevented by parameterization

### Credential Protection
- Passwords masked in API responses
- Credentials stored locally only
- No logging of sensitive data

### CORS
- Development: All origins allowed
- Production: Configure specific origins

## Data Model

### DatabaseMetadata
```typescript
interface DatabaseMetadata {
  name: string;
  url: string;  // Password masked
  tables: TableInfo[];
  views: TableInfo[];
  cachedAt: string;
}
```

### TableInfo
```typescript
interface TableInfo {
  schemaName: string;
  name: string;
  type: "TABLE" | "VIEW";
  columns: ColumnInfo[];
}
```

### ColumnInfo
```typescript
interface ColumnInfo {
  name: string;
  dataType: string;
  nullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
}
```

### QueryResult
```typescript
interface QueryResult {
  columns: string[];
  rows: any[][];
  rowCount: number;
  executedSql: string;
  executionTimeMs: number;
}
```
