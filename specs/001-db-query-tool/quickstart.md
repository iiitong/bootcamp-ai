# Quickstart: Database Query Tool

**Date**: 2025-12-13
**Branch**: `001-db-query-tool`

## Prerequisites

- Python 3.14+ (via uv)
- Node.js 24+ (for frontend)
- PostgreSQL database to connect to
- OpenAI API key

## Environment Setup

### 1. Set Environment Variables

```bash
# Required: OpenAI API key for natural language queries
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 2. Backend Setup

```bash
cd w2/db_query/backend

# Install dependencies with uv
uv sync

# Run the backend server
uv run uvicorn src.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.

### 3. Frontend Setup

```bash
cd w2/db_query/frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Quick Test

### 1. Add a Database Connection

```bash
curl -X PUT http://localhost:8000/api/v1/dbs/mydb \
  -H "Content-Type: application/json" \
  -d '{"url": "postgresql://postgres:postgres@localhost:5432/postgres"}'
```

Expected response:
```json
{
  "databaseName": "mydb",
  "tables": [...],
  "views": [...],
  "extractedAt": "2025-12-13T10:00:00Z"
}
```

### 2. List Database Connections

```bash
curl http://localhost:8000/api/v1/dbs
```

Expected response:
```json
[
  {
    "name": "mydb",
    "urlMasked": "postgresql://postgres:***@localhost:5432/postgres",
    "createdAt": "2025-12-13T10:00:00Z",
    "lastConnectedAt": "2025-12-13T10:00:00Z"
  }
]
```

### 3. Execute a SQL Query

```bash
curl -X POST http://localhost:8000/api/v1/dbs/mydb/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM pg_tables LIMIT 5"}'
```

Expected response:
```json
{
  "columns": ["schemaname", "tablename", "tableowner", ...],
  "rows": [...],
  "rowCount": 5,
  "executionTimeMs": 12.5,
  "truncated": false
}
```

### 4. Generate SQL from Natural Language

```bash
curl -X POST http://localhost:8000/api/v1/dbs/mydb/query/natural \
  -H "Content-Type: application/json" \
  -d '{"prompt": "显示所有表的名称"}'
```

Expected response:
```json
{
  "sql": "SELECT tablename FROM pg_tables WHERE schemaname = 'public'",
  "explanation": "This query retrieves all table names from the public schema",
  "confidence": 0.95
}
```

## Project Structure After Setup

```
w2/db_query/
├── backend/
│   ├── src/
│   │   ├── main.py           # FastAPI app
│   │   ├── models/           # Pydantic models
│   │   ├── services/         # Business logic
│   │   ├── api/v1/           # API routes
│   │   └── storage/          # SQLite operations
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Refine app
│   │   ├── types/            # TypeScript interfaces
│   │   ├── components/       # UI components
│   │   └── pages/            # Page components
│   ├── package.json
│   └── tsconfig.json
│
└── README.md
```

## Data Storage Location

Local data is stored in:
```
~/.db_query/db_query.db
```

This SQLite database contains:
- Database connection configurations (URLs base64-encoded)
- Cached metadata for each connected database

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Common Issues

### Connection Refused

If you see "Connection refused" when adding a database:
1. Ensure PostgreSQL is running
2. Check the connection URL format
3. Verify network access to the database host

### OpenAI API Error

If natural language queries fail:
1. Verify `OPENAI_API_KEY` is set correctly
2. Check your OpenAI API quota
3. Ensure network access to api.openai.com

### CORS Issues

The backend allows all origins by default. If you still see CORS errors:
1. Verify the backend is running on port 8000
2. Check browser console for specific CORS error messages

## Development Commands

### Backend

```bash
# Run with auto-reload
uv run uvicorn src.main:app --reload

# Run type checking
uv run mypy src/

# Run tests
uv run pytest

# Format code
uv run ruff format src/
```

### Frontend

```bash
# Development server
npm run dev

# Type checking
npm run typecheck

# Build for production
npm run build

# Run tests
npm run test
```

## Next Steps

1. **Add your database**: Use the UI or API to add your PostgreSQL connection
2. **Explore schema**: Browse tables and columns in the schema tree
3. **Write queries**: Use the Monaco SQL editor to write and execute queries
4. **Try natural language**: Describe what data you need in plain language

For detailed API documentation, see [contracts/openapi.yaml](./contracts/openapi.yaml).
