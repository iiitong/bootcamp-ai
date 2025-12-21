"""MySQL query execution service."""

import time

import aiomysql

from src.models.query import QueryResult
from src.utils.db_utils import parse_mysql_url


class MySQLQueryExecutor:
    """Execute SQL queries against MySQL."""

    @staticmethod
    async def execute(
        connection_url: str,
        sql: str,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """Execute a SQL query against MySQL and return results.

        Args:
            connection_url: MySQL connection URL
            sql: SQL query to execute (should be pre-processed)
            timeout_seconds: Query timeout in seconds

        Returns:
            QueryResult with columns, rows, and execution time

        Raises:
            ConnectionError: If unable to connect
            TimeoutError: If query exceeds timeout
            Exception: For other execution errors
        """
        params = parse_mysql_url(connection_url)
        start_time = time.perf_counter()

        try:
            conn = await aiomysql.connect(**params)
            try:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # Set query timeout (max_execution_time in milliseconds)
                    # Only works for SELECT queries in MySQL 5.7.8+
                    await cur.execute(f"SET max_execution_time = {timeout_seconds * 1000}")

                    # Execute the query
                    await cur.execute(sql)
                    rows = await cur.fetchall()

                    # Get column names from cursor description
                    columns = [desc[0] for desc in cur.description] if cur.description else []

            finally:
                conn.close()

        except aiomysql.OperationalError as e:
            error_code = e.args[0] if e.args else 0
            error_msg = str(e).lower()

            # MySQL error codes:
            # 3024: Query execution was interrupted, maximum statement execution time exceeded
            # 1317: Query execution was interrupted
            if error_code in (3024, 1317) or "timeout" in error_msg or "interrupt" in error_msg:
                raise TimeoutError("Query execution timed out") from e

            # Connection errors
            if error_code in (2003, 2006, 2013):
                raise ConnectionError(f"Failed to connect to MySQL database: {e}") from e

            raise ConnectionError(f"MySQL database error: {e}") from e

        except aiomysql.ProgrammingError as e:
            # SQL syntax errors
            raise ValueError(f"MySQL query error: {e}") from e

        except aiomysql.Error as e:
            raise ConnectionError(f"MySQL error: {e}") from e

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return QueryResult(
            columns=columns,
            rows=[dict(row) for row in rows],
            row_count=len(rows),
            execution_time_ms=round(execution_time_ms, 2),
        )
