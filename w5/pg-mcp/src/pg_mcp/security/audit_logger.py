"""Audit logging module for pg-mcp server.

This module provides comprehensive audit logging for all query operations,
supporting multiple storage backends and log rotation.
"""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Audit event types."""

    QUERY_EXECUTED = "query_executed"
    QUERY_DENIED = "query_denied"
    POLICY_VIOLATION = "policy_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class AuditStorage(str, Enum):
    """Audit log storage backends."""

    FILE = "file"
    STDOUT = "stdout"
    DATABASE = "database"


@dataclass
class ClientInfo:
    """Client information for audit events.

    Attributes:
        ip: Client IP address (only available in SSE mode)
        user_agent: HTTP User-Agent header value
        session_id: Session identifier for tracking
    """

    ip: str | None
    user_agent: str | None
    session_id: str | None


@dataclass
class QueryInfo:
    """Query information for audit events.

    Attributes:
        question: Natural language question from the user
        sql: Generated SQL query
        sql_hash: SHA256 hash of the SQL for deduplication/tracking
    """

    question: str
    sql: str
    sql_hash: str

    @classmethod
    def from_sql(cls, question: str, sql: str) -> "QueryInfo":
        """Create QueryInfo with auto-generated hash.

        Args:
            question: Natural language question
            sql: Generated SQL query

        Returns:
            QueryInfo instance with computed SQL hash
        """
        sql_hash = f"sha256:{hashlib.sha256(sql.encode()).hexdigest()}"
        return cls(question=question, sql=sql, sql_hash=sql_hash)


@dataclass
class ResultInfo:
    """Query result information for audit events.

    Attributes:
        status: Execution status (success, error, denied)
        rows_returned: Number of rows returned (if successful)
        execution_time_ms: Query execution time in milliseconds
        truncated: Whether results were truncated due to row limits
        error_code: Error code (if status is error)
        error_message: Error description (if status is error)
    """

    status: str  # success, error, denied
    rows_returned: int | None
    execution_time_ms: float
    truncated: bool
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class PolicyCheckInfo:
    """Policy check results for audit events.

    Attributes:
        table_access: Table access policy result (passed, denied, skipped)
        column_access: Column access policy result (passed, denied, skipped)
        explain_check: EXPLAIN validation result (passed, denied, skipped)
    """

    table_access: str  # passed, denied, skipped
    column_access: str
    explain_check: str


@dataclass
class AuditEvent:
    """Complete audit event record.

    Contains all information about a query execution attempt,
    including client context, query details, results, and policy checks.
    """

    timestamp: str
    event_type: AuditEventType
    request_id: str
    session_id: str | None
    database: str
    client_info: ClientInfo
    query: QueryInfo | None
    result: ResultInfo | None
    policy_checks: PolicyCheckInfo | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with enum values converted to strings
        """
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON string representation of the audit event
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """Audit log recorder for query operations.

    Responsibilities:
    - Record all query requests and results
    - Support multiple storage backends
    - Implement log rotation (file mode)

    Example:
        >>> logger = AuditLogger(storage=AuditStorage.FILE, file_path="audit.jsonl")
        >>> event = AuditLogger.create_event(
        ...     event_type=AuditEventType.QUERY_EXECUTED,
        ...     request_id="req-123",
        ...     database="mydb",
        ...     question="Show all users",
        ...     sql="SELECT * FROM users",
        ...     rows_returned=10,
        ...     execution_time_ms=45.2
        ... )
        >>> await logger.log(event)
    """

    def __init__(
        self,
        storage: AuditStorage = AuditStorage.STDOUT,
        file_path: str | None = None,
        max_size_mb: int = 100,
        max_files: int = 10,
        redact_sql: bool = False,
    ):
        """Initialize audit logger.

        Args:
            storage: Storage backend type (FILE, STDOUT, DATABASE)
            file_path: Path for file storage (required if storage is FILE)
            max_size_mb: Maximum file size before rotation (default: 100MB)
            max_files: Maximum number of rotated files to keep (default: 10)
            redact_sql: Whether to redact SQL content for privacy (default: False)
        """
        self.storage = storage
        self.file_path = Path(file_path) if file_path else None
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_files = max_files
        self.redact_sql = redact_sql

        self._file_handle = None
        self._current_size = 0

    async def log(self, event: AuditEvent) -> None:
        """Record an audit event.

        Args:
            event: Audit event to record
        """
        json_line = event.to_json()

        if self.storage == AuditStorage.STDOUT:
            logger.info("audit_event", **event.to_dict())
        elif self.storage == AuditStorage.FILE:
            await self._write_to_file(json_line)
        elif self.storage == AuditStorage.DATABASE:
            # Future extension: write to database
            pass

    async def _write_to_file(self, line: str) -> None:
        """Write to file with rotation support.

        Uses asyncio.to_thread to avoid blocking the event loop.

        Args:
            line: JSON line to write
        """
        if self.file_path is None:
            return

        # Check if rotation is needed
        if self._current_size > self.max_size_bytes:
            await self._rotate()

        # Execute synchronous write in thread pool to avoid blocking
        def _sync_write() -> None:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        await asyncio.to_thread(_sync_write)
        self._current_size += len(line) + 1

    async def _rotate(self) -> None:
        """Rotate log files.

        Implements a numbered rotation scheme:
        - Current file -> .1.jsonl
        - .1.jsonl -> .2.jsonl
        - ... up to max_files
        - Oldest file is deleted when limit reached
        """
        if self.file_path is None or not self.file_path.exists():
            return

        # Rename existing files (from oldest to newest)
        for i in range(self.max_files - 1, 0, -1):
            old_path = self.file_path.with_suffix(f".{i}.jsonl")
            new_path = self.file_path.with_suffix(f".{i + 1}.jsonl")
            if old_path.exists():
                if i + 1 >= self.max_files:
                    old_path.unlink()
                else:
                    old_path.rename(new_path)

        # Current file becomes .1.jsonl
        if self.file_path.exists():
            self.file_path.rename(self.file_path.with_suffix(".1.jsonl"))

        self._current_size = 0

    @staticmethod
    def create_event(
        event_type: AuditEventType,
        request_id: str,
        database: str,
        client_ip: str | None = None,
        session_id: str | None = None,
        question: str | None = None,
        sql: str | None = None,
        rows_returned: int | None = None,
        execution_time_ms: float = 0,
        truncated: bool = False,
        error_code: str | None = None,
        error_message: str | None = None,
        policy_checks: dict[str, str] | None = None,
    ) -> AuditEvent:
        """Create an audit event with the given parameters.

        This is a convenience factory method that handles the creation
        of nested objects and sets appropriate defaults.

        Args:
            event_type: Type of audit event
            request_id: Unique request identifier
            database: Target database name
            client_ip: Client IP address (optional)
            session_id: Session identifier (optional)
            question: Natural language question (optional)
            sql: Generated SQL query (optional)
            rows_returned: Number of rows returned (optional)
            execution_time_ms: Execution time in milliseconds (default: 0)
            truncated: Whether results were truncated (default: False)
            error_code: Error code if failed (optional)
            error_message: Error message if failed (optional)
            policy_checks: Policy check results dict (optional)

        Returns:
            Fully constructed AuditEvent instance
        """
        return AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type=event_type,
            request_id=request_id,
            session_id=session_id,
            database=database,
            client_info=ClientInfo(
                ip=client_ip,
                user_agent=None,
                session_id=session_id,
            ),
            query=QueryInfo.from_sql(question or "", sql or "") if sql else None,
            result=ResultInfo(
                status="success" if error_code is None else "error",
                rows_returned=rows_returned,
                execution_time_ms=execution_time_ms,
                truncated=truncated,
                error_code=error_code,
                error_message=error_message,
            )
            if sql
            else None,
            policy_checks=PolicyCheckInfo(
                table_access=policy_checks.get("table_access", "skipped"),
                column_access=policy_checks.get("column_access", "skipped"),
                explain_check=policy_checks.get("explain_check", "skipped"),
            )
            if policy_checks
            else None,
        )
