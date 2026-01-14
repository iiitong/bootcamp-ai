---
name: nl2sql
description: Convert natural language queries to SQL for PostgreSQL databases. Use this skill when users want to query pg_mcp_test_small (blog), pg_mcp_test_medium (ecommerce), or pg_mcp_test_large (ERP) databases using natural language descriptions. Generates safe, read-only SQL queries with validation and execution.
---

# Natural Language to SQL (nl2sql)

## Overview

This skill converts natural language query descriptions into safe, executable PostgreSQL SQL queries. It supports three test databases:

- **pg_mcp_test_small**: Blog system (users, posts, comments, tags)
- **pg_mcp_test_medium**: E-commerce platform (products, orders, customers, payments)
- **pg_mcp_test_large**: ERP system (HR, Finance, Inventory, CRM, Projects)

## Workflow

```text
User Request
    |
    v
1. Identify Target Database
    |
    v
2. Load Database Reference
    |
    v
3. Generate SQL Query
    |
    v
4. Security Validation (CRITICAL)
    |
    v
5. Execute Query via psql
    |
    +---> If execution fails --> Deep analysis --> Regenerate SQL --> Step 5
    |
    v
6. Validate Results (score 0-10)
    |
    +---> If score < 7 --> Deep analysis --> Regenerate SQL --> Step 5
    |
    v
7. Return Results (SQL or Data based on user preference)
```

## Database Selection

Based on the user's query context, select the appropriate database:

| Keywords/Context | Database | Schema |
|-----------------|----------|--------|
| blog, posts, articles, authors, comments, tags, readers, writers | pg_mcp_test_small | blog |
| products, orders, customers, shopping, cart, payments, shipping, reviews, inventory, coupons | pg_mcp_test_medium | ecommerce |
| employees, HR, departments, salaries, leave, attendance, vendors, invoices, accounting, projects, tasks, tickets, CRM, leads, opportunities | pg_mcp_test_large | erp |

## Reference Files

Load the appropriate reference file before generating SQL:

- [pg_mcp_test_small Reference](./references/pg_mcp_test_small.md) - Blog schema
- [pg_mcp_test_medium Reference](./references/pg_mcp_test_medium.md) - E-commerce schema
- [pg_mcp_test_large Reference](./references/pg_mcp_test_large.md) - ERP schema

## SQL Generation Guidelines

### Schema Qualification

**IMPORTANT**: Always use schema-qualified table names:

```sql
-- CORRECT
SELECT * FROM blog.posts;
SELECT * FROM ecommerce.orders;
SELECT * FROM erp.employees;

-- INCORRECT (will fail)
SELECT * FROM posts;
SELECT * FROM orders;
SELECT * FROM employees;
```

### Query Best Practices

1. **Use appropriate JOINs**: Leverage foreign key relationships documented in references
2. **Use views when available**: Views like `recent_posts`, `product_catalog`, `employee_directory` often provide pre-joined data
3. **Apply LIMIT**: Add `LIMIT 100` by default unless user specifies otherwise
4. **Use proper date/time functions**: PostgreSQL-specific functions like `date_trunc()`, `CURRENT_DATE`, etc.
5. **Leverage indexes**: Filter on indexed columns when possible for better performance

### Example Patterns

**Simple query:**
```sql
SELECT id, title, status, created_at
FROM blog.posts
WHERE status = 'published'
ORDER BY created_at DESC
LIMIT 10;
```

**Join query:**
```sql
SELECT p.title, u.username, COUNT(c.id) as comment_count
FROM blog.posts p
JOIN blog.users u ON p.author_id = u.id
LEFT JOIN blog.comments c ON p.id = c.post_id
WHERE p.status = 'published'
GROUP BY p.id, p.title, u.username
ORDER BY comment_count DESC
LIMIT 10;
```

**Using views:**
```sql
SELECT * FROM ecommerce.top_products LIMIT 10;
```

**Aggregate query:**
```sql
SELECT date_trunc('month', created_at) as month,
       COUNT(*) as order_count,
       SUM(total_amount) as total_revenue
FROM ecommerce.orders
WHERE status NOT IN ('cancelled', 'refunded')
GROUP BY date_trunc('month', created_at)
ORDER BY month DESC;
```

## CRITICAL: Security Validation

**Every generated SQL MUST pass these security checks before execution.**

### Forbidden Operations

The following are **STRICTLY FORBIDDEN** and must be rejected:

#### 1. Write Operations
```sql
-- FORBIDDEN: Any data modification
INSERT INTO ...
UPDATE ... SET ...
DELETE FROM ...
TRUNCATE ...
DROP ...
ALTER ...
CREATE ...
GRANT ...
REVOKE ...
```

#### 2. Dangerous Functions
```sql
-- FORBIDDEN: System commands
pg_sleep(...)
pg_terminate_backend(...)
pg_cancel_backend(...)
pg_reload_conf()
lo_import(...)
lo_export(...)
COPY ... FROM/TO ...

-- FORBIDDEN: File system access
pg_read_file(...)
pg_read_binary_file(...)
pg_ls_dir(...)
pg_stat_file(...)
```

#### 3. SQL Injection Patterns
```sql
-- FORBIDDEN: These patterns indicate injection attempts
; DROP TABLE ...
'; --
1=1
OR 1=1
UNION SELECT ...
INTO OUTFILE ...
INTO DUMPFILE ...
LOAD_FILE(...)
```

#### 4. Sensitive Data Access
```sql
-- FORBIDDEN: Direct access to sensitive columns
SELECT password_hash FROM ...
SELECT api_key FROM ...
SELECT secret FROM ...
SELECT token FROM ...
SELECT credit_card FROM ...
```

#### 5. Information Schema Abuse
```sql
-- FORBIDDEN: Excessive metadata queries that could aid attacks
SELECT * FROM pg_shadow ...
SELECT * FROM pg_authid ...
SELECT usename, passwd FROM pg_user ...
```

### Security Validation Checklist

Before executing, verify:

- [ ] Query starts with SELECT (or WITH for CTEs followed by SELECT)
- [ ] No semicolons except at the end (no statement chaining)
- [ ] No forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE
- [ ] No dangerous functions: pg_sleep, COPY, lo_import, lo_export
- [ ] No injection patterns: UNION SELECT, OR 1=1, etc.
- [ ] No access to password_hash, api_key, secret, token columns
- [ ] LIMIT clause present (default to LIMIT 100)
- [ ] Schema-qualified table names used

### Validation Implementation

```python
# Pseudo-code for validation
FORBIDDEN_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
    'TRUNCATE', 'GRANT', 'REVOKE', 'COPY'
]

DANGEROUS_FUNCTIONS = [
    'pg_sleep', 'pg_terminate_backend', 'pg_cancel_backend',
    'pg_reload_conf', 'lo_import', 'lo_export',
    'pg_read_file', 'pg_read_binary_file'
]

FORBIDDEN_PATTERNS = [
    r';\s*DROP', r';\s*DELETE', r';\s*UPDATE', r';\s*INSERT',
    r"'\s*;\s*--", r'\bOR\s+1\s*=\s*1\b', r'\bUNION\s+SELECT\b',
    r'\bINTO\s+OUTFILE\b', r'\bINTO\s+DUMPFILE\b'
]

SENSITIVE_COLUMNS = [
    'password_hash', 'password', 'api_key', 'secret',
    'token', 'credit_card', 'ssn'
]

def validate_sql(sql):
    sql_upper = sql.upper()

    # Must be SELECT query
    if not sql_upper.strip().startswith(('SELECT', 'WITH')):
        return False, "Only SELECT queries allowed"

    # Check forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return False, f"Forbidden keyword: {keyword}"

    # Check dangerous functions
    for func in DANGEROUS_FUNCTIONS:
        if func.upper() in sql_upper:
            return False, f"Dangerous function: {func}"

    # Check injection patterns
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, sql_upper):
            return False, f"Suspicious pattern detected"

    # Check sensitive columns
    for col in SENSITIVE_COLUMNS:
        if col.lower() in sql.lower():
            return False, f"Access to sensitive column: {col}"

    return True, "Validation passed"
```

## Query Execution

Execute validated SQL using psql:

```bash
PGPASSWORD='' psql -h localhost -p 5432 -U postgres -d <database_name> -c "<sql_query>"
```

### Connection Details

| Parameter | Value |
|-----------|-------|
| Host | localhost |
| Port | 5432 |
| User | postgres |
| Password | (empty string) |

### Execution Command Template

```bash
# For pg_mcp_test_small (blog)
PGPASSWORD='' psql -h localhost -p 5432 -U postgres -d pg_mcp_test_small -c "SELECT ..."

# For pg_mcp_test_medium (ecommerce)
PGPASSWORD='' psql -h localhost -p 5432 -U postgres -d pg_mcp_test_medium -c "SELECT ..."

# For pg_mcp_test_large (erp)
PGPASSWORD='' psql -h localhost -p 5432 -U postgres -d pg_mcp_test_large -c "SELECT ..."
```

## Result Validation

After execution, analyze the results:

### Scoring Criteria (0-10)

| Score | Meaning | Action |
|-------|---------|--------|
| 10 | Perfect match - results exactly answer the question | Return results |
| 9 | Excellent - results fully address the question with minor extras | Return results |
| 8 | Very Good - results answer the question well | Return results |
| 7 | Good - results adequately answer the question | Return results |
| 6 | Acceptable but incomplete - missing some aspects | Regenerate SQL |
| 5 | Partial - only partially answers the question | Regenerate SQL |
| 4 | Poor - results don't well match the intent | Regenerate SQL |
| 3 | Very Poor - results mostly irrelevant | Regenerate SQL |
| 2 | Bad - wrong tables/columns used | Regenerate SQL |
| 1 | Failed - execution error or empty results when data expected | Regenerate SQL |
| 0 | Security violation detected | ABORT immediately |

### Validation Questions

1. **Relevance**: Do the columns returned match what was asked?
2. **Completeness**: Are all requested data points included?
3. **Correctness**: Are joins and filters logically correct?
4. **Meaningfulness**: Do the results make sense in context?
5. **Row Count**: Is the number of rows appropriate?

### If Score < 7: Deep Analysis

When score is below 7, perform deep analysis:

1. **Identify the issue**:
   - Wrong table(s) selected?
   - Missing JOIN condition?
   - Incorrect WHERE filter?
   - Missing GROUP BY?
   - Wrong aggregate function?

2. **Review the reference documentation** for correct table/column names

3. **Regenerate SQL** with corrections

4. **Re-execute** and re-validate

## Output Format

### Default: Return Query Results

Present results in a clear format:

```markdown
## Query Results

**Question**: [User's original question]

**Database**: pg_mcp_test_medium (ecommerce)

**Generated SQL**:
```sql
SELECT ...
```

**Results** (showing first N rows):

| Column1 | Column2 | ... |
|---------|---------|-----|
| value1  | value2  | ... |

**Summary**: [Brief interpretation of the results]
```

### Alternative: Return SQL Only

When user specifically requests just the SQL:

```markdown
## Generated SQL

**Question**: [User's original question]

**Database**: pg_mcp_test_medium (ecommerce)

```sql
SELECT ...
```

**Notes**: [Any important considerations about the query]
```

## Error Handling

### Execution Errors

If psql returns an error:

1. **Parse the error message** (column not found, relation not found, syntax error, etc.)
2. **Identify the cause** (typo, wrong schema, missing table, etc.)
3. **Consult reference documentation**
4. **Regenerate corrected SQL**
5. **Re-execute**

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `relation "posts" does not exist` | Missing schema | Use `blog.posts` instead of `posts` |
| `column "xxx" does not exist` | Typo or wrong table | Check reference for correct column name |
| `syntax error at or near` | SQL syntax issue | Review and fix syntax |
| `ambiguous column` | Same column in multiple tables | Use table alias (e.g., `p.id`) |

## Examples

### Example 1: Blog Query

**User**: "Show me the top 5 most viewed published posts"

**Process**:
1. Database: pg_mcp_test_small (blog context)
2. Reference: blog.posts has view_count, status columns
3. SQL:
```sql
SELECT id, title, view_count, published_at
FROM blog.posts
WHERE status = 'published'
ORDER BY view_count DESC
LIMIT 5;
```
4. Security: PASS (SELECT only, no sensitive columns)
5. Execute and validate

### Example 2: E-commerce Analytics

**User**: "What are the total sales by month for 2024?"

**Process**:
1. Database: pg_mcp_test_medium (ecommerce context)
2. Reference: ecommerce.orders has total_amount, created_at
3. SQL:
```sql
SELECT
    date_trunc('month', created_at) as month,
    COUNT(*) as order_count,
    SUM(total_amount) as total_sales
FROM ecommerce.orders
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01'
  AND status NOT IN ('cancelled', 'refunded')
GROUP BY date_trunc('month', created_at)
ORDER BY month;
```
4. Security: PASS
5. Execute and validate

### Example 3: ERP HR Query

**User**: "List employees in the Engineering department with their managers"

**Process**:
1. Database: pg_mcp_test_large (HR/ERP context)
2. Reference: erp.employees, erp.departments
3. SQL:
```sql
SELECT
    e.employee_number,
    e.first_name || ' ' || e.last_name as employee_name,
    e.email,
    d.name as department,
    m.first_name || ' ' || m.last_name as manager_name
FROM erp.employees e
JOIN erp.departments d ON e.department_id = d.id
LEFT JOIN erp.employees m ON e.manager_id = m.id
WHERE d.name ILIKE '%engineering%'
  AND e.employment_status = 'active'
ORDER BY e.last_name
LIMIT 100;
```
4. Security: PASS
5. Execute and validate

## Troubleshooting

### Query Returns No Results

1. Check if filters are too restrictive
2. Verify enum values match exactly (case-sensitive)
3. Check date ranges
4. Verify table has data: `SELECT COUNT(*) FROM schema.table`

### Query Too Slow

1. Add LIMIT clause
2. Filter on indexed columns
3. Avoid SELECT * - specify needed columns
4. Use views when available

### Ambiguous Requirements

If the user's request is unclear:

1. Ask clarifying questions
2. Make reasonable assumptions and state them
3. Provide multiple query options if applicable
