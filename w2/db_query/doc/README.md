# DB Query Tool

A full-stack database query tool with PostgreSQL support and natural language SQL generation.

## Overview

DB Query Tool is a web application that allows users to:

- Connect to PostgreSQL databases
- Browse database schema (tables, views, columns)
- Execute SQL queries with safety restrictions
- Generate SQL from natural language using LLM
- Export query results to CSV/JSON

## Features

### Database Management
- Add/update/delete database connections
- Automatic metadata extraction (tables, views, columns, constraints)
- Metadata caching with refresh capability
- Password masking for security

### Query Execution
- SQL syntax validation using sqlglot
- Read-only query enforcement (SELECT only)
- Automatic LIMIT 1000 injection for safety
- Query timeout protection
- Rich result display with pagination

### Natural Language to SQL
- LLM-powered SQL generation
- Schema-aware context for accurate queries
- Support for custom OpenAI-compatible endpoints

### Export
- CSV export with proper escaping
- JSON export for structured data

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL (target), SQLite (local storage)
- **SQL Processing**: sqlglot
- **LLM Integration**: OpenAI API compatible
- **Async Support**: psycopg3 async driver

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Ant Design 5
- **Admin Framework**: Refine
- **Code Editor**: Monaco Editor
- **Build Tool**: Vite

## Quick Start

See [DEVELOPMENT.md](./DEVELOPMENT.md) for detailed setup instructions.

```bash
# Backend
cd backend
uv sync
uv run uvicorn src.main:app --reload

# Frontend
cd frontend
yarn install
yarn dev
```

## Documentation

- [API Reference](./API.md) - REST API endpoints
- [Architecture](./ARCHITECTURE.md) - System design and components
- [Development Guide](./DEVELOPMENT.md) - Setup and contribution guide

## Project Structure

```
db_query/
├── backend/
│   ├── src/
│   │   ├── api/v1/          # API endpoints
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic
│   │   └── storage/         # SQLite storage
│   ├── tests/               # Test files
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── providers/       # Data providers
│   │   └── utils/           # Utility functions
│   └── package.json
├── fixtures/                # Test data
├── doc/                     # Documentation
└── Makefile                 # Build automation
```

## License

MIT License
