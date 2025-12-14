# API Reference

## Interactive Documentation

FastAPI 自动生成交互式 API 文档，启动后端后可直接访问：

- **Swagger UI**: http://localhost:8000/docs - 可直接测试 API
- **ReDoc**: http://localhost:8000/redoc - 更详细的文档格式
- **OpenAPI JSON**: http://localhost:8000/openapi.json - OpenAPI 规范文件

以下为 API 端点的详细说明。

---

Base URL: `http://localhost:8000/api/v1`

## Database Endpoints

### List Databases

```
GET /dbs
```

Returns all saved database connections.

**Response** `200 OK`
```json
[
  {
    "name": "mydb",
    "url": "postgresql://user:***@localhost:5432/mydb",
    "created_at": "2025-12-14T10:00:00Z",
    "updated_at": "2025-12-14T10:00:00Z"
  }
]
```

---

### Add/Update Database

```
PUT /dbs/{name}
```

Add a new database connection or update existing one. Automatically extracts and caches metadata.

**Path Parameters**
| Name | Type | Description |
|------|------|-------------|
| name | string | Database connection name (must start with letter) |

**Request Body**
```json
{
  "url": "postgresql://user:password@localhost:5432/dbname"
}
```

**Response** `200 OK`
```json
{
  "name": "mydb",
  "url": "postgresql://user:***@localhost:5432/mydb",
  "tables": [...],
  "views": [...],
  "cached_at": "2025-12-14T10:00:00Z"
}
```

**Errors**
| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_URL | Invalid connection URL format |
| 400 | CONNECTION_FAILED | Cannot connect to database |

---

### Get Database Metadata

```
GET /dbs/{name}
```

Returns complete metadata for a database including tables and views.

**Path Parameters**
| Name | Type | Description |
|------|------|-------------|
| name | string | Database connection name |

**Query Parameters**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| refresh | boolean | false | Force refresh cached metadata |

**Response** `200 OK`
```json
{
  "name": "mydb",
  "url": "postgresql://user:***@localhost:5432/mydb",
  "tables": [
    {
      "schema_name": "public",
      "name": "users",
      "type": "TABLE",
      "columns": [
        {
          "name": "id",
          "data_type": "integer",
          "nullable": false,
          "is_primary_key": true,
          "is_foreign_key": false
        }
      ]
    }
  ],
  "views": [...],
  "cached_at": "2025-12-14T10:00:00Z"
}
```

**Errors**
| Status | Code | Description |
|--------|------|-------------|
| 404 | CONNECTION_NOT_FOUND | Database connection not found |

---

### Delete Database

```
DELETE /dbs/{name}
```

Delete a database connection and its cached metadata.

**Response** `204 No Content`

**Errors**
| Status | Code | Description |
|--------|------|-------------|
| 404 | CONNECTION_NOT_FOUND | Database connection not found |

---

## Query Endpoints

### Execute SQL Query

```
POST /dbs/{name}/query
```

Execute a SELECT query against a database.

**Security Features**
- Only SELECT statements allowed
- LIMIT 1000 auto-added if not specified
- Query timeout protection (default 30s)

**Request Body**
```json
{
  "sql": "SELECT * FROM users WHERE active = true"
}
```

**Response** `200 OK`
```json
{
  "columns": ["id", "name", "email", "active"],
  "rows": [
    [1, "John", "john@example.com", true],
    [2, "Jane", "jane@example.com", true]
  ],
  "row_count": 2,
  "executed_sql": "SELECT * FROM users WHERE active = true LIMIT 1000",
  "execution_time_ms": 12.5
}
```

**Errors**
| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_SQL | SQL syntax error |
| 400 | NON_SELECT_QUERY | Non-SELECT statement detected |
| 404 | CONNECTION_NOT_FOUND | Database connection not found |
| 408 | QUERY_TIMEOUT | Query execution timed out |

---

### Natural Language Query

```
POST /dbs/{name}/query/natural
```

Generate SQL from natural language description using LLM.

**Prerequisites**
- OPENAI_API_KEY environment variable must be set
- Database metadata must be cached

**Request Body**
```json
{
  "prompt": "Show me all orders placed in the last 7 days with total amount greater than 1000"
}
```

**Response** `200 OK`
```json
{
  "generated_sql": "SELECT * FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL '7 days' AND total_amount > 1000",
  "result": null,
  "error": null
}
```

**Errors**
| Status | Code | Description |
|--------|------|-------------|
| 404 | CONNECTION_NOT_FOUND | Database connection not found |
| 500 | LLM_ERROR | LLM service error or API key not configured |

---

## Health Check

### Check API Health

```
GET /health
```

**Response** `200 OK`
```json
{
  "status": "healthy"
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": {
    "detail": "Error message description",
    "code": "ERROR_CODE"
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| INVALID_URL | Invalid database connection URL |
| CONNECTION_FAILED | Failed to connect to database |
| CONNECTION_NOT_FOUND | Database connection not found |
| INVALID_SQL | SQL syntax error |
| NON_SELECT_QUERY | Non-SELECT statement not allowed |
| QUERY_TIMEOUT | Query execution timed out |
| LLM_ERROR | LLM service error |

---

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
