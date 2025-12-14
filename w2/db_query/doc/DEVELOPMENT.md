# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (for target database)
- uv (Python package manager)
- Yarn (Node package manager)

## Environment Setup

### Backend Setup

```bash
cd backend

# Install dependencies with uv
uv sync

# Install dev dependencies
uv sync --dev

# Create virtual environment (done automatically by uv)
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install
```

### Environment Variables

Create `.env` file in the backend directory:

```bash
# Optional: OpenAI API for natural language queries
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional custom endpoint
OPENAI_MODEL=gpt-4o-mini                    # Optional model override

# Data storage path (default: ~/.db_query_tool)
DATA_DIR=/path/to/data

# Query settings
DEFAULT_QUERY_LIMIT=1000
QUERY_TIMEOUT_SECONDS=30
```

## Running the Application

### Development Mode

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
yarn dev
```

Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Using Makefile

```bash
# Start both services
make dev

# Or individually
make backend
make frontend
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_query.py

# Run with verbose output
uv run pytest -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
yarn test

# Run tests once (CI mode)
yarn test:run

# Run with coverage
yarn test --coverage
```

## Code Quality

### Backend

```bash
cd backend

# Linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking
uv run mypy src
```

### Frontend

```bash
cd frontend

# Linting
yarn lint

# Type checking
yarn typecheck
```

## Project Structure

```
db_query/
├── backend/
│   ├── src/
│   │   ├── __init__.py          # Version info
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings management
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       └── databases.py # API endpoints
│   │   ├── models/
│   │   │   ├── database.py      # Database models
│   │   │   ├── query.py         # Query models
│   │   │   └── errors.py        # Error models
│   │   ├── services/
│   │   │   ├── metadata.py      # Schema extraction
│   │   │   ├── query.py         # Query execution
│   │   │   └── llm.py           # LLM integration
│   │   └── storage/
│   │       └── sqlite.py        # Local storage
│   ├── tests/
│   │   ├── conftest.py          # Test fixtures
│   │   ├── test_api.py
│   │   └── test_query.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # App entry
│   │   ├── App.tsx              # Root component
│   │   ├── components/
│   │   │   ├── DatabaseList.tsx
│   │   │   ├── SchemaTree.tsx
│   │   │   ├── SqlEditor.tsx
│   │   │   ├── QueryResults.tsx
│   │   │   └── ExportButtons.tsx
│   │   ├── pages/
│   │   │   ├── databases/
│   │   │   │   ├── list.tsx
│   │   │   │   └── show.tsx
│   │   │   └── query/
│   │   │       └── index.tsx
│   │   ├── providers/
│   │   │   └── dataProvider.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── utils/
│   │       ├── error.ts
│   │       └── export.ts
│   ├── package.json
│   └── vite.config.ts
├── fixtures/
│   └── test_schema.sql          # Test database schema
├── doc/
│   ├── README.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT.md
└── Makefile
```

## Adding Features

### Adding a New API Endpoint

1. Define models in `src/models/`
2. Implement service logic in `src/services/`
3. Add endpoint in `src/api/v1/databases.py`
4. Write tests in `tests/`

### Adding a New Frontend Component

1. Create component in `src/components/`
2. Add types in `src/types/index.ts`
3. Import and use in pages
4. Write tests if needed

## Database Setup for Testing

```bash
# Create test database
createdb db_query_test

# Load test schema
psql db_query_test < fixtures/test_schema.sql
```

## Troubleshooting

### Backend Issues

**Port already in use:**
```bash
lsof -i :8000
kill -9 <PID>
```

**Database connection failed:**
- Check PostgreSQL is running
- Verify connection URL format
- Check firewall/network settings

### Frontend Issues

**Module not found:**
```bash
rm -rf node_modules
yarn install
```

**Vite HMR not working:**
- Check port conflicts
- Clear browser cache
- Restart dev server

### Common Issues

**CORS errors:**
- Backend must have CORS middleware enabled
- Check allowed origins configuration

**LLM not working:**
- Verify OPENAI_API_KEY is set
- Check API endpoint accessibility
- Review model availability

## Contributing

1. Create feature branch from `main`
2. Make changes with tests
3. Run linting and tests
4. Submit pull request

### Commit Messages

Follow conventional commits:
```
feat: add new feature
fix: fix bug
docs: update documentation
test: add tests
refactor: code refactoring
```
