# DB Query Tool - Backend

Backend API for database query tool with PostgreSQL support and natural language SQL generation.

## Features

- PostgreSQL database connection management
- Metadata extraction (tables, views, columns)
- SQL query execution (SELECT only, auto LIMIT 1000)
- Natural language to SQL generation using OpenAI
- SQLite local storage for connection persistence

## Requirements

- Python 3.11+
- uv (Python package manager)
- PostgreSQL (target database)

## Setup

```bash
# Install dependencies
uv sync

# Set environment variables
export OPENAI_API_KEY="your-api-key"  # Required for natural language queries
export DB_QUERY_DATA_DIR="~/.db_query"  # Optional, default: ~/.db_query

# Run development server
uv run uvicorn src.main:app --reload --port 8000
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key for natural language queries |
| `DB_QUERY_DATA_DIR` | No | `~/.db_query` | Directory for SQLite storage |

\* Only required if using natural language query feature

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dbs` | List all database connections |
| PUT | `/api/v1/dbs/{name}` | Add/update database connection |
| GET | `/api/v1/dbs/{name}` | Get database metadata |
| DELETE | `/api/v1/dbs/{name}` | Delete database connection |
| POST | `/api/v1/dbs/{name}/query` | Execute SQL query |
| POST | `/api/v1/dbs/{name}/query/natural` | Generate SQL from natural language |

API documentation available at: http://localhost:8000/docs

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Environment configuration
│   ├── api/v1/              # API endpoints
│   │   ├── databases.py     # Database management endpoints
│   │   └── router.py        # API router configuration
│   ├── models/              # Pydantic data models
│   │   ├── database.py      # Database-related models
│   │   ├── query.py         # Query-related models
│   │   └── errors.py        # Error response models
│   ├── services/            # Business logic
│   │   ├── metadata.py      # PostgreSQL metadata extraction
│   │   ├── query.py         # SQL validation and execution
│   │   └── llm.py           # Natural language to SQL
│   └── storage/
│       └── sqlite.py        # SQLite local storage
└── tests/                   # Test files
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_sql_processor.py -v
```

## Security Notes

- Only SELECT queries are allowed (INSERT, UPDATE, DELETE, DROP rejected)
- LIMIT 1000 is auto-added to queries without LIMIT
- Database passwords are masked in API responses
- CORS is enabled for all origins (development mode)
