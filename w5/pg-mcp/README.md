# PostgreSQL MCP Server

A Model Context Protocol (MCP) server that enables natural language querying of PostgreSQL databases. Simply ask questions in plain English and get SQL results.

## Features

- **Natural Language Queries**: Convert plain English questions to SQL using OpenAI
- **Multi-Database Support**: Configure and query multiple PostgreSQL databases
- **SQL Safety Validation**: Defense-in-depth SQL validation with sqlglot
- **Read-Only Enforcement**: Guaranteed read-only access with transaction-level protection
- **Schema Caching**: Efficient schema caching with configurable refresh intervals
- **Rate Limiting**: Built-in request and token rate limiting
- **Connection Pooling**: Async connection pool management with asyncpg
- **MCP Resources**: Expose database schema and metadata via MCP resources

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL database (9.5+)
- OpenAI API key

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd pg-mcp

# Install dependencies
uv sync

# Install with development dependencies
uv sync --all-extras
```

### Verify Installation

```bash
# Check that the module can be imported
uv run python -c "import pg_mcp; print('Installation successful!')"
```

## Configuration

The server is configured using environment variables with the `PG_MCP_` prefix. Copy `.env.example` and customize it:

```bash
cp .env.example .env
# Edit .env with your settings
```

### Required Environment Variables

```bash
# OpenAI Configuration (required)
PG_MCP_OPENAI_API_KEY=sk-your-openai-api-key

# Database Configuration
PG_MCP_DATABASE_HOST=localhost
PG_MCP_DATABASE_PORT=5432
PG_MCP_DATABASE_DBNAME=mydb
PG_MCP_DATABASE_USER=postgres
PG_MCP_DATABASE_PASSWORD=your-password

# Alternative: Use connection URL (overrides individual params)
# PG_MCP_DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

### All Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| **Database** | | |
| `PG_MCP_DATABASE_NAME` | Database alias for referencing | `main` |
| `PG_MCP_DATABASE_HOST` | Database host | - |
| `PG_MCP_DATABASE_PORT` | Database port | `5432` |
| `PG_MCP_DATABASE_DBNAME` | Database name | - |
| `PG_MCP_DATABASE_USER` | Database user | - |
| `PG_MCP_DATABASE_PASSWORD` | Database password | - |
| `PG_MCP_DATABASE_URL` | Connection URL (overrides above) | - |
| `PG_MCP_DATABASE_SSL_MODE` | SSL mode: disable/allow/prefer/require | `prefer` |
| `PG_MCP_DATABASE_MIN_POOL_SIZE` | Minimum pool connections | `2` |
| `PG_MCP_DATABASE_MAX_POOL_SIZE` | Maximum pool connections | `10` |
| **OpenAI** | | |
| `PG_MCP_OPENAI_API_KEY` | OpenAI API key (required) | - |
| `PG_MCP_OPENAI_MODEL` | Model for SQL generation | `gpt-4o-mini` |
| `PG_MCP_OPENAI_BASE_URL` | Custom API endpoint | - |
| `PG_MCP_OPENAI_MAX_RETRIES` | Max API retries | `3` |
| `PG_MCP_OPENAI_TIMEOUT` | Request timeout (seconds) | `30.0` |
| **Server** | | |
| `PG_MCP_SERVER_CACHE_REFRESH_INTERVAL` | Schema cache refresh (seconds) | `3600` |
| `PG_MCP_SERVER_MAX_RESULT_ROWS` | Max rows to return | `1000` |
| `PG_MCP_SERVER_QUERY_TIMEOUT` | Query timeout (seconds) | `30.0` |
| `PG_MCP_SERVER_USE_READONLY_TRANSACTIONS` | Enable read-only mode | `true` |
| `PG_MCP_SERVER_MAX_SQL_RETRY` | SQL generation retries | `2` |
| **Rate Limiting** | | |
| `PG_MCP_RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `PG_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE` | Max requests/minute | `60` |
| `PG_MCP_RATE_LIMIT_REQUESTS_PER_HOUR` | Max requests/hour | `1000` |
| `PG_MCP_RATE_LIMIT_OPENAI_TOKENS_PER_MINUTE` | Max tokens/minute | `100000` |

## Usage

### Running the MCP Server

```bash
# Set required environment variables
export PG_MCP_OPENAI_API_KEY=sk-your-api-key
export PG_MCP_DATABASE_HOST=localhost
export PG_MCP_DATABASE_DBNAME=mydb
export PG_MCP_DATABASE_USER=postgres
export PG_MCP_DATABASE_PASSWORD=your-password

# Run the server
uv run python -m pg_mcp

# Or use the installed script
uv run pg-mcp
```

### MCP Tools

The server exposes the following MCP tools:

#### `query` - Execute Natural Language Query

Execute a natural language query against a PostgreSQL database.

**Parameters:**
- `question` (string, required): The natural language question to answer
- `database` (string, optional): Target database name (uses default if not specified)
- `return_type` (string, optional): What to return - `"sql"`, `"result"`, or `"both"` (default: `"result"`)
- `limit` (int, optional): Maximum number of rows to return

**Examples:**

```
# Get query results only
query(question="How many users registered last month?")

# Get SQL without executing
query(question="Show me the top 10 products by sales", return_type="sql")

# Get both SQL and results
query(question="What is the average order value?", return_type="both")

# Query a specific database
query(question="List all tables", database="analytics")

# Limit results
query(question="Show recent orders", limit=50)
```

#### `refresh_schema` - Refresh Schema Cache

Manually refresh the schema cache for one or all databases.

**Parameters:**
- `database` (string, optional): Database to refresh (refreshes all if not specified)

**Examples:**

```
# Refresh all databases
refresh_schema()

# Refresh specific database
refresh_schema(database="main")
```

### MCP Resources

The server exposes the following MCP resources:

#### `databases://list`

List all available databases configured in the server.

**Response:**
```
- main
- analytics
- production
```

#### `schema://{database}`

Get the schema for a specific database, including tables, columns, indexes, and relationships.

**Example:** `schema://main`

**Response:**
```
Database: main

Tables:
  users
    - id: integer (PK)
    - email: varchar(255)
    - created_at: timestamp

  orders
    - id: integer (PK)
    - user_id: integer (FK -> users.id)
    - total: numeric(10,2)
    - status: order_status
...
```

### Natural Language Query Examples

Here are some example queries you can ask:

```
# Aggregations
"How many active users do we have?"
"What is the total revenue for Q4 2024?"
"Show me the average order value by month"

# Filtering
"Find all orders from the last 7 days"
"List users who haven't logged in for 30 days"
"Show products with inventory below 10 units"

# Joins
"Which users have placed more than 5 orders?"
"Show me products that have never been ordered"
"List customers with their total spend"

# Complex queries
"What are the top 10 best-selling products by category?"
"Show me the month-over-month growth in new user registrations"
"Find the correlation between order value and customer lifetime"
```

## Claude Desktop Integration

### Configuration

Add the following to your Claude Desktop configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/pg-mcp",
        "run",
        "python",
        "-m",
        "pg_mcp"
      ],
      "env": {
        "PG_MCP_OPENAI_API_KEY": "sk-your-openai-api-key",
        "PG_MCP_DATABASE_HOST": "localhost",
        "PG_MCP_DATABASE_PORT": "5432",
        "PG_MCP_DATABASE_DBNAME": "your-database",
        "PG_MCP_DATABASE_USER": "postgres",
        "PG_MCP_DATABASE_PASSWORD": "your-password"
      }
    }
  }
}
```

### Verifying the Integration

After configuring Claude Desktop:

1. Restart Claude Desktop
2. Look for the MCP server icon in the chat interface
3. Try asking a question like "What databases are available?"

## Docker Deployment

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  pg-mcp:
    build: .
    environment:
      - PG_MCP_OPENAI_API_KEY=${PG_MCP_OPENAI_API_KEY}
      - PG_MCP_DATABASE_HOST=postgres
      - PG_MCP_DATABASE_PORT=5432
      - PG_MCP_DATABASE_DBNAME=testdb
      - PG_MCP_DATABASE_USER=postgres
      - PG_MCP_DATABASE_PASSWORD=${PG_MCP_DATABASE_PASSWORD}
    # For MCP stdio communication
    stdin_open: true
    tty: true
    depends_on:
      - postgres

  # Optional: local PostgreSQL for testing
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${PG_MCP_DATABASE_PASSWORD}
      POSTGRES_DB: testdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Create a `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev

# Run the MCP server
CMD ["uv", "run", "python", "-m", "pg_mcp"]
```

### Running with Docker Compose

```bash
# Set environment variables
export PG_MCP_OPENAI_API_KEY=sk-your-api-key
export PG_MCP_DATABASE_PASSWORD=your-password

# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

### Environment Variables for Docker

| Variable | Description | Required |
|----------|-------------|----------|
| `PG_MCP_OPENAI_API_KEY` | OpenAI API key | Yes |
| `PG_MCP_DATABASE_HOST` | PostgreSQL host | Yes |
| `PG_MCP_DATABASE_DBNAME` | Database name | Yes |
| `PG_MCP_DATABASE_USER` | Database user | Yes |
| `PG_MCP_DATABASE_PASSWORD` | Database password | Yes |

## Security

### Read-Only Guarantees

The server implements multiple layers of defense to ensure read-only access:

1. **SQL Parsing Validation**: All generated SQL is parsed and validated using sqlglot. Only SELECT statements are allowed.

2. **Dangerous Function Blocking**: Functions like `pg_sleep`, `pg_terminate_backend`, and others that could affect server operation are blocked.

3. **Read-Only Transactions**: Queries are executed within read-only transactions (`SET TRANSACTION READ ONLY`), providing database-level enforcement.

4. **Stacked Query Prevention**: Multiple statements separated by semicolons are rejected.

5. **CTE Validation**: Common Table Expressions (CTEs) with data modification (INSERT, UPDATE, DELETE) are detected and blocked.

### SQL Injection Prevention

- All SQL generation uses the OpenAI API with carefully crafted prompts
- Generated SQL is validated against an AST parser before execution
- No user input is directly interpolated into SQL strings

### Recommended Database User Configuration

For maximum security, create a dedicated read-only database user:

```sql
-- Create a read-only user
CREATE USER mcp_readonly WITH PASSWORD 'secure-password';

-- Grant connect permission
GRANT CONNECT ON DATABASE your_database TO mcp_readonly;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO mcp_readonly;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;

-- Grant SELECT on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO mcp_readonly;

-- Grant SELECT on all sequences (for auto-increment fields)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO mcp_readonly;

-- Optional: restrict to specific tables only
-- REVOKE SELECT ON sensitive_table FROM mcp_readonly;
```

### Sensitive Data Considerations

- Avoid exposing tables containing passwords, API keys, or PII directly
- Consider creating views that mask sensitive columns
- Use PostgreSQL row-level security (RLS) for fine-grained access control

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=pg_mcp --cov-report=term-missing

# Run only unit tests
uv run pytest tests/unit/

# Run integration tests (requires PostgreSQL)
uv run pytest tests/integration/
```

### Code Quality

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy src/
```

### Project Structure

```
pg-mcp/
├── pyproject.toml           # Project configuration
├── config.example.yaml      # Example configuration
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── server.py        # FastMCP server definition
│       ├── config/          # Configuration management
│       ├── models/          # Domain models (Pydantic)
│       ├── infrastructure/  # External integrations
│       │   ├── database.py      # Connection pool
│       │   ├── schema_cache.py  # Schema caching
│       │   ├── openai_client.py # LLM client
│       │   ├── sql_parser.py    # SQL validation
│       │   └── rate_limiter.py  # Rate limiting
│       └── utils/           # Utilities
└── tests/
    ├── unit/                # Unit tests
    └── integration/         # Integration tests
```

## Troubleshooting

### Common Issues

**Connection refused to PostgreSQL**
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify connection with psql
psql -h localhost -U postgres -d your_database
```

**OpenAI API errors**
```bash
# Verify your API key is set
echo $OPENAI_API_KEY

# Test the API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Schema cache issues**
```
# Force refresh the schema cache
Use the refresh_schema tool: refresh_schema()
```

**Rate limiting errors**
- Reduce the frequency of queries
- Adjust rate limit settings in config.yaml
- Check OpenAI token usage

### Debug Logging

Enable debug logging by setting the log level:

```bash
LOG_LEVEL=DEBUG uv run python -m pg_mcp
```

## License

MIT

## Contributing

Contributions are welcome! Please read the development guidelines in CLAUDE.md before submitting pull requests.
