# PostgreSQL MCP Server - Development Guidelines

## Project Overview

A high-performance MCP (Model Context Protocol) server for PostgreSQL that enables natural language database querying via LLM-generated SQL. The server provides intelligent, secure, read-only database access through MCP tools and resources.

**Core Features:**
- Natural language to SQL conversion using OpenAI
- Multi-database schema caching and management
- SQL validation and security enforcement (read-only)
- MCP Resources for schema introspection
- Rate limiting and connection pooling

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13.5+ | Runtime |
| FastMCP | latest | MCP server framework |
| asyncpg | ^0.29.0 | Async PostgreSQL driver |
| sqlglot | ^26.0 | SQL parsing & validation |
| Pydantic | ^2.10 | Data models & validation |
| openai | ^1.60 | LLM API client |
| structlog | ^24.0 | Structured logging |
| PyYAML | ^6.0 | Configuration |
| pytest | ^8.0 | Testing framework |
| pytest-asyncio | ^0.24 | Async test support |

## Project Structure

```
pg-mcp/
├── pyproject.toml
├── config.example.yaml
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── __main__.py           # Entry point
│       ├── server.py             # FastMCP server definition
│       ├── config/               # Configuration management
│       │   ├── models.py         # Pydantic config models
│       │   └── loader.py         # Config loading with env vars
│       ├── models/               # Domain models
│       │   ├── schema.py         # Database schema models
│       │   ├── query.py          # Query request/response models
│       │   └── errors.py         # Error types and exceptions
│       ├── services/             # Business logic layer
│       │   ├── query_service.py  # Query orchestration
│       │   ├── schema_service.py # Schema management
│       │   └── validation_service.py
│       ├── infrastructure/       # External integrations
│       │   ├── database.py       # Connection pool management
│       │   ├── schema_cache.py   # Schema caching
│       │   ├── openai_client.py  # LLM integration
│       │   ├── sql_parser.py     # SQLGlot wrapper
│       │   └── rate_limiter.py   # Request throttling
│       └── utils/
│           ├── logging.py        # Logging configuration
│           └── env.py            # Environment variable handling
└── tests/
    ├── conftest.py               # Shared fixtures
    ├── unit/                     # Unit tests
    ├── integration/              # Integration tests
    └── fixtures/                 # Test data
```

## Commands

```bash
# Install dependencies (using uv)
uv sync

# Run the MCP server
uv run python -m pg_mcp

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pg_mcp --cov-report=term-missing

# Run only unit tests
uv run pytest tests/unit/

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

## Code Style & Python Best Practices

### Idiomatic Python

```python
# PREFER: Use type hints consistently
async def get_schema(self, database: str) -> DatabaseSchema:
    ...

# PREFER: Use dataclasses or Pydantic models, not dicts
class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool = True

# PREFER: Context managers for resource management
async with pool.acquire() as conn:
    result = await conn.fetch(query)

# PREFER: Structural pattern matching (Python 3.10+)
match error:
    case UnknownDatabaseError():
        return {"error": "database_not_found", ...}
    case UnsafeSQLError():
        return {"error": "unsafe_sql", ...}

# PREFER: Walrus operator for assignment expressions
if (schema := cache.get(database)) is not None:
    return schema

# PREFER: Use collections.abc for type hints
from collections.abc import Sequence, Mapping

def process_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    ...

# AVOID: Mutable default arguments
def bad_func(items: list = []):  # Bug!
    ...
def good_func(items: list | None = None):
    items = items or []
```

### Async Patterns

```python
# PREFER: Gather for concurrent operations
results = await asyncio.gather(
    self._load_tables(),
    self._load_views(),
    self._load_enum_types(),
)

# PREFER: asynccontextmanager for async resources
@asynccontextmanager
async def acquire(self) -> AsyncIterator[Connection]:
    async with self._pool.acquire() as conn:
        yield conn

# PREFER: Lock for shared state
async with self._lock:
    self._schema = new_schema

# AVOID: Blocking calls in async code
# Use asyncio.to_thread() for CPU-bound or blocking I/O
result = await asyncio.to_thread(cpu_intensive_func, data)
```

### Error Handling

```python
# PREFER: Custom exception hierarchy
class PgMcpError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details

class UnsafeSQLError(PgMcpError):
    def __init__(self, reason: str):
        super().__init__(ErrorCode.UNSAFE_SQL, f"Unsafe SQL: {reason}")

# PREFER: Specific exception handling
try:
    await pool.fetch(query)
except asyncpg.PostgresError as e:
    raise SQLSyntaxError(query, str(e)) from e
except asyncio.TimeoutError:
    raise QueryTimeoutError(timeout)

# PREFER: Use `raise ... from` for exception chaining
except Exception as e:
    raise PgMcpError(ErrorCode.INTERNAL_ERROR, str(e)) from e
```

## Design Principles

### SOLID Principles

**Single Responsibility (SRP)**
```python
# Each class has one reason to change
class SQLParser:        # Only SQL parsing/validation
class SchemaCache:      # Only schema caching
class OpenAIClient:     # Only LLM interaction
class QueryService:     # Only query orchestration
```

**Open/Closed Principle (OCP)**
```python
# Open for extension, closed for modification
# Use protocols/ABCs for extensibility
from typing import Protocol

class DatabaseDriver(Protocol):
    async def fetch(self, query: str) -> list[Record]: ...
    async def execute(self, query: str) -> str: ...

# Future: Add MySQLDriver without changing existing code
```

**Liskov Substitution (LSP)**
```python
# Subclasses must be substitutable for base classes
class PgMcpError(Exception):
    def to_response(self) -> ErrorResponse: ...

class UnsafeSQLError(PgMcpError):
    # Must implement to_response() correctly
    def to_response(self) -> ErrorResponse:
        return ErrorResponse(error_code=self.code, ...)
```

**Interface Segregation (ISP)**
```python
# Prefer small, focused interfaces
class SchemaProvider(Protocol):
    async def get_schema(self, database: str) -> DatabaseSchema: ...

class SchemaRefresher(Protocol):
    async def refresh(self, database: str | None = None) -> None: ...

# Don't force clients to depend on methods they don't use
```

**Dependency Inversion (DIP)**
```python
# High-level modules depend on abstractions
class QueryService:
    def __init__(
        self,
        pool_manager: DatabasePoolManager,  # Abstract dependency
        schema_manager: SchemaCacheManager,  # Abstract dependency
        openai_client: OpenAIClient,         # Abstract dependency
    ):
        ...

# Inject dependencies, don't create them internally
```

### DRY (Don't Repeat Yourself)

```python
# Extract common patterns
async def _fetch_with_timeout(
    self,
    pool: DatabasePool,
    query: str,
    timeout: float
) -> list[Record]:
    """Reusable fetch with timeout handling."""
    try:
        return await asyncio.wait_for(
            pool.fetch(query),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise QueryTimeoutError(timeout)

# Use base models for shared fields
class BaseTableInfo(BaseModel):
    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)

class TableInfo(BaseTableInfo):
    indexes: list[IndexInfo] = Field(default_factory=list)

class ViewInfo(BaseTableInfo):
    definition: str | None = None
```

### ETC (Easy To Change)

```python
# Configuration-driven behavior
class ServerConfig(BaseModel):
    max_result_rows: int = 1000      # Easy to adjust
    query_timeout: float = 30.0       # Easy to adjust
    max_sql_retry: int = 2            # Easy to adjust

# Strategy pattern for extensibility
class SQLDialect(Protocol):
    def validate(self, sql: str) -> ValidationResult: ...
    def add_limit(self, sql: str, limit: int) -> str: ...

# Registry pattern for adding new dialects
DIALECTS: dict[str, type[SQLDialect]] = {
    "postgres": PostgresSQLDialect,
    # Future: "mysql": MySQLDialect,
}
```

## Testing Requirements

### Test Structure

```python
# tests/conftest.py - Shared fixtures
import pytest
import pytest_asyncio
from pg_mcp.config.models import AppConfig, DatabaseConfig

@pytest_asyncio.fixture
async def mock_pool():
    """Mock database pool for unit tests."""
    ...

@pytest.fixture
def sample_schema() -> DatabaseSchema:
    """Sample schema for testing."""
    return DatabaseSchema(
        name="test_db",
        tables=[...],
        views=[...],
    )
```

### Unit Test Coverage Requirements

- **Minimum 85% line coverage**
- **100% coverage for security-critical code** (SQL validation, safety checks)
- Test all error paths and edge cases

```python
# tests/unit/test_sql_parser.py
class TestSQLParser:
    """SQL parser unit tests."""

    @pytest.mark.parametrize("sql,expected_safe", [
        ("SELECT * FROM users", True),
        ("SELECT * FROM users; DROP TABLE users", False),  # Stacked queries
        ("SELECT pg_sleep(10)", False),  # Dangerous function
        ("DELETE FROM users", False),     # Non-SELECT
        ("SELECT * FROM users WHERE id = 1; --", True),  # Comments OK
    ])
    def test_sql_safety_validation(self, sql: str, expected_safe: bool):
        parser = SQLParser()
        result = parser.validate(sql)
        assert result.is_safe == expected_safe

    def test_cte_with_insert_rejected(self):
        sql = "WITH ins AS (INSERT INTO logs VALUES (1) RETURNING *) SELECT * FROM ins"
        result = SQLParser().validate(sql)
        assert not result.is_safe
        assert "CTE" in result.error_message
```

### Integration Tests

```python
# tests/integration/test_query_flow.py
@pytest_asyncio.fixture
async def test_database():
    """Set up test database with sample data."""
    ...

@pytest.mark.integration
async def test_full_query_flow(test_database, mock_openai):
    """Test complete query flow from NL to results."""
    service = QueryService(...)
    response = await service.execute_query(
        QueryRequest(question="List all users", database="test")
    )
    assert response.success
    assert response.result.row_count > 0
```

### Test Patterns

```python
# Use parametrize for data-driven tests
@pytest.mark.parametrize("input,expected", [...])
def test_something(input, expected):
    ...

# Use fixtures for setup/teardown
@pytest_asyncio.fixture
async def db_pool():
    pool = await create_test_pool()
    yield pool
    await pool.close()

# Mock external services
@pytest.fixture
def mock_openai(mocker):
    return mocker.patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI")

# Test async code properly
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_func()
    assert result == expected
```

## Performance Requirements

| Metric | Target |
|--------|--------|
| Schema cache load | < 5s (100 tables) |
| SQL generation latency | < 3s (excluding OpenAI) |
| Concurrent queries | >= 10 |
| Memory usage (steady-state) | < 512MB |
| Connection pool efficiency | > 90% utilization under load |

### Performance Patterns

```python
# Use connection pooling
pool = await asyncpg.create_pool(
    dsn=dsn,
    min_size=2,    # Keep warm connections
    max_size=10,   # Limit max connections
)

# Cache schema to avoid repeated queries
class SchemaCache:
    async def get(self) -> DatabaseSchema:
        if self._schema is None:
            await self.load()
        return self._schema

# Use asyncio.gather for concurrent operations
tables, views, enums = await asyncio.gather(
    self._load_tables(),
    self._load_views(),
    self._load_enum_types(),
)

# Limit result sets to prevent memory issues
sql = self._sql_parser.add_limit(sql, max_rows + 1)

# Use streaming for large results (future)
async for row in conn.cursor(query):
    yield row
```

## Security Guidelines

### SQL Injection Prevention

```python
# ALWAYS use parameterized queries
await conn.fetch("SELECT * FROM users WHERE id = $1", user_id)

# NEVER string interpolation for SQL
# BAD: f"SELECT * FROM users WHERE id = {user_id}"

# Validate all generated SQL before execution
validation = self._sql_parser.validate(sql)
if not validation.is_safe:
    raise UnsafeSQLError(validation.error_message)
```

### Read-Only Enforcement

```python
# Multi-layer defense
# 1. SQL parsing validation
FORBIDDEN_STATEMENT_TYPES = {Insert, Update, Delete, Drop, Create, ...}

# 2. Dangerous function blocking
FORBIDDEN_FUNCTIONS = {"pg_sleep", "pg_terminate_backend", ...}

# 3. EXPLAIN validation in read-only transaction
async with conn.transaction(readonly=True):
    await conn.execute(f"EXPLAIN {sql}")

# 4. Database-level permissions (recommendation)
# CREATE USER mcp_readonly WITH PASSWORD '...';
# GRANT SELECT ON ALL TABLES ...;
```

### Secret Management

```python
# Use SecretStr for sensitive data
class DatabaseConfig(BaseModel):
    password: SecretStr | None = None

    def get_dsn(self) -> str:
        password = self.password.get_secret_value() if self.password else ""
        return f"postgresql://...:{password}@..."

# Support environment variable substitution
# password: "${PG_PASSWORD}"

# Never log secrets
logger.info("Connecting", host=config.host)  # OK
logger.info("Connecting", password=config.password)  # BAD
```

## Logging Standards

```python
import structlog

logger = structlog.get_logger()

# Use structured logging with context
log = logger.bind(database=db_name, request_id=req_id)
log.info("Query started", question=question[:100])
log.info("Query completed", duration_ms=int(duration * 1000), row_count=count)

# Log levels:
# - DEBUG: Detailed diagnostic info
# - INFO: Normal operations
# - WARNING: Recoverable issues
# - ERROR: Failures requiring attention

# Always include context
try:
    ...
except Exception as e:
    logger.exception("Query failed", sql=sql[:200], error=str(e))
```

## Git Commit Standards

```
feat(query): add natural language query support
fix(parser): handle edge case in CTE validation
refactor(cache): improve schema refresh atomicity
test(security): add SQL injection test cases
docs(readme): update installation instructions
perf(pool): optimize connection acquisition
```

## Configuration Example

```yaml
# config.yaml
databases:
  - name: production_analytics
    host: localhost
    port: 5432
    database: analytics
    user: readonly_user
    password: "${PG_PASSWORD}"
    ssl_mode: require
    min_pool_size: 2
    max_pool_size: 10

openai:
  api_key: "${OPENAI_API_KEY}"
  model: gpt-4o-mini
  max_retries: 3
  timeout: 30.0

server:
  cache_refresh_interval: 3600
  max_result_rows: 1000
  query_timeout: 30.0
  enable_result_validation: false
  max_sql_retry: 2
  rate_limit:
    enabled: true
    requests_per_minute: 60
    requests_per_hour: 1000
```

## Architecture Decision Records

### ADR-001: Use sqlglot for SQL parsing
- **Decision**: Use sqlglot instead of simple regex
- **Rationale**: Proper AST parsing, multi-dialect support, safe validation
- **Consequences**: Additional dependency, but more robust security

### ADR-002: Async-first design
- **Decision**: Use async/await throughout
- **Rationale**: Better performance for I/O-bound operations
- **Consequences**: Requires asyncpg, AsyncOpenAI, proper async testing

### ADR-003: Pydantic for data validation
- **Decision**: Use Pydantic v2 for all data models
- **Rationale**: Type safety, validation, serialization in one package
- **Consequences**: Slight performance overhead, but significant safety gains
