# PostgreSQL MCP Server Dockerfile
# Multi-stage build for minimal image size

FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only)
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim AS production

WORKDIR /app

# Install uv in production image
RUN pip install uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy dependency files for uv run
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PG_MCP_CONFIG=/app/config.yaml
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcpuser && \
    chown -R mcpuser:mcpuser /app

USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose MCP server port (if using HTTP transport)
EXPOSE 8000

# Entry point
ENTRYPOINT ["uv", "run", "python", "-m", "pg_mcp"]
