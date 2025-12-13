# Feature Specification: Database Query Tool

**Feature Branch**: `001-db-query-tool`
**Created**: 2025-12-13
**Status**: Draft
**Input**: User description: "Database query tool with metadata extraction, SQL execution, and natural language query generation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect to Database and View Schema (Priority: P1)

As a user, I want to add a database connection URL so that the system connects to my database and displays all available tables and views with their structure.

**Why this priority**: This is the foundational capability - without database connectivity and metadata visibility, no other features can function. Users need to see what data is available before they can query it.

**Independent Test**: Can be fully tested by providing a valid PostgreSQL connection URL and verifying that the system displays the database's tables and views with their columns. Delivers immediate value by giving users visibility into their database structure.

**Acceptance Scenarios**:

1. **Given** the user is on the main interface, **When** they enter a valid PostgreSQL connection URL and submit, **Then** the system connects to the database, extracts metadata (tables, views, columns, types), stores it locally, and displays a browsable schema tree.

2. **Given** a connection URL has been added previously, **When** the user returns to the application, **Then** they can see their previously added database connections with cached metadata.

3. **Given** the user enters an invalid or unreachable connection URL, **When** they submit, **Then** the system displays a clear error message explaining the connection failure (e.g., "Cannot connect: authentication failed" or "Host unreachable").

4. **Given** a database connection exists, **When** the user selects a table or view, **Then** they see the column names, data types, and any constraints (primary keys, foreign keys, nullable).

---

### User Story 2 - Execute SQL Queries Manually (Priority: P2)

As a user, I want to write and execute SQL SELECT queries against my connected database and see the results in a table format.

**Why this priority**: Direct SQL querying is the core utility of the tool. Users familiar with SQL need this capability to explore and analyze their data. This enables power users immediately while NL generation (P3) serves users who need assistance.

**Independent Test**: Can be fully tested by writing a SELECT query in the input area and verifying that results display in a formatted table. Delivers immediate value for data exploration.

**Acceptance Scenarios**:

1. **Given** a database is connected, **When** the user enters a valid SELECT query and executes it, **Then** the results are displayed in a tabular format with column headers.

2. **Given** the user enters a query without a LIMIT clause, **When** they execute it, **Then** the system automatically appends LIMIT 1000 to prevent excessive data retrieval.

3. **Given** the user enters a query with syntax errors, **When** they execute it, **Then** the system displays a helpful error message indicating the syntax problem before sending to the database.

4. **Given** the user enters a non-SELECT statement (INSERT, UPDATE, DELETE, DROP), **When** they attempt to execute, **Then** the system blocks the query and displays an error: "Only SELECT queries are allowed."

5. **Given** a SELECT query is executed successfully, **When** results are returned, **Then** the data is displayed in JSON format (camelCase field names) and rendered as an interactive table in the frontend.

---

### User Story 3 - Generate SQL from Natural Language (Priority: P3)

As a user, I want to describe what data I need in plain language so that the system generates a SQL query for me, which I can review, edit, and execute.

**Why this priority**: Natural language query generation expands accessibility to users unfamiliar with SQL. It depends on having metadata (P1) available as context for the LLM, and the execution capability (P2) to run generated queries.

**Independent Test**: Can be fully tested by entering a natural language description (e.g., "show me all users who signed up last month") and verifying that a valid SQL query is generated. Delivers value by reducing the SQL knowledge barrier.

**Acceptance Scenarios**:

1. **Given** a database is connected with cached metadata, **When** the user enters a natural language query description (e.g., "show all orders from last week with customer names"), **Then** the system sends the request to an LLM with table/view metadata as context and returns a generated SQL query.

2. **Given** an LLM-generated SQL query is displayed, **When** the user reviews it, **Then** they can edit the query before execution if needed.

3. **Given** an LLM-generated SQL query is displayed, **When** the user clicks "Execute", **Then** the query goes through the same validation (syntax check, SELECT-only, auto-LIMIT) as manually entered queries.

4. **Given** the LLM cannot generate a valid query from the description, **When** this occurs, **Then** the system displays a message asking the user to rephrase or provide more details.

---

### Edge Cases

- **Empty database**: When a connected database has no tables or views, display a message: "No tables or views found in this database."
- **Very large result sets**: Even with LIMIT 1000, results may be large. Frontend should handle pagination or scrolling gracefully.
- **Connection timeout**: If the database becomes unreachable during query execution, display a timeout error and suggest checking the connection.
- **Special characters in data**: Ensure proper escaping/encoding when displaying data containing special characters, HTML, or JSON strings.
- **Concurrent connections**: If a user adds multiple database connections, ensure each connection's metadata and queries are properly isolated.
- **Schema changes**: If the database schema changes after metadata is cached, provide a way to refresh/resync the metadata.
- **LLM unavailability**: If the LLM service is unavailable, display an error and allow the user to write SQL manually.

## Requirements *(mandatory)*

### Functional Requirements

**Database Connection Management**
- **FR-001**: System MUST accept PostgreSQL connection URLs in standard format (postgresql://user:pass@host:port/dbname)
- **FR-002**: System MUST validate connection URLs before attempting to connect
- **FR-003**: System MUST store connection configurations persistently in a local SQLite database
- **FR-004**: System MUST support multiple database connections per user session

**Metadata Extraction**
- **FR-005**: System MUST extract table and view names from the connected database
- **FR-006**: System MUST extract column names, data types, and constraints for each table/view
- **FR-007**: System MUST cache extracted metadata in the local SQLite database for reuse
- **FR-008**: System MUST provide a mechanism to refresh cached metadata on demand

**SQL Query Execution**
- **FR-009**: System MUST parse all SQL queries using a SQL parser before execution
- **FR-010**: System MUST reject any query that is not a SELECT statement
- **FR-011**: System MUST automatically append LIMIT 1000 to queries without a LIMIT clause
- **FR-012**: System MUST return query results as JSON with camelCase field naming
- **FR-013**: System MUST display syntax errors with helpful messages when query parsing fails

**Natural Language to SQL**
- **FR-014**: System MUST send database metadata (tables, columns, types) as context when generating SQL
- **FR-015**: System MUST display generated SQL for user review before execution
- **FR-016**: System MUST allow users to edit generated SQL before execution
- **FR-017**: Generated SQL MUST go through the same validation as manually entered queries

**User Interface**
- **FR-018**: System MUST display database schema in a browsable hierarchical format
- **FR-019**: System MUST display query results in a tabular format with column headers
- **FR-020**: System MUST provide clear error messages for all failure scenarios

### Key Entities

- **DatabaseConnection**: Represents a saved database connection with its URL (credentials stored securely), display name, and last connected timestamp
- **DatabaseMetadata**: Represents the cached schema information including tables, views, and their columns with types and constraints
- **Table/View**: Represents a database table or view with its name, schema, and list of columns
- **Column**: Represents a table/view column with name, data type, nullability, and constraint information
- **Query**: Represents a SQL query with its text, execution timestamp, and associated connection
- **QueryResult**: Represents the result of a query execution with column headers and row data

### Technical Constraints (from Constitution)

- Backend MUST use Pydantic v2 for all data models
- All JSON responses MUST use camelCase field naming
- Frontend MUST use TypeScript with strict mode enabled
- No authentication required - open access for all users
- All functions MUST have complete type annotations

### Assumptions

- PostgreSQL is the primary (and initially only) supported database type
- Users have valid PostgreSQL credentials and network access to their databases
- The local SQLite database is stored in a standard application data directory
- LLM integration uses an external API service (specific provider to be determined)
- Maximum query result size is 1000 rows by default (can be reduced, not increased)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a database connection and view its schema within 30 seconds of providing a valid URL
- **SC-002**: 100% of non-SELECT queries are blocked before reaching the database
- **SC-003**: Query results display within 5 seconds for typical queries (under 1000 rows)
- **SC-004**: Natural language queries generate valid SQL for 80% of common data exploration requests
- **SC-005**: Users can successfully execute their first query within 2 minutes of adding a database connection
- **SC-006**: All error scenarios produce user-friendly messages (no raw stack traces or technical errors shown to users)
- **SC-007**: Cached metadata persists across application restarts without requiring reconnection
- **SC-008**: Users report the schema browser helps them understand available data (qualitative feedback target: 4/5 satisfaction)
