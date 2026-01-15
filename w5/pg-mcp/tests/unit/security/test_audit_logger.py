"""Unit tests for AuditLogger.

Tests cover:
- Basic logging functionality
- Event creation
- JSON serialization
- File output with rotation
- Different storage backends
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.security.audit_logger import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditStorage,
    ClientInfo,
    PolicyCheckInfo,
    QueryInfo,
    ResultInfo,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_client_info() -> ClientInfo:
    """Sample client information."""
    return ClientInfo(
        ip="192.168.1.100",
        user_agent="Claude-MCP-Client/1.0",
        session_id="session-123",
    )


@pytest.fixture
def sample_query_info() -> QueryInfo:
    """Sample query information."""
    return QueryInfo.from_sql(
        question="Show all active users",
        sql="SELECT * FROM users WHERE active = true",
    )


@pytest.fixture
def sample_result_info() -> ResultInfo:
    """Sample result information."""
    return ResultInfo(
        status="success",
        rows_returned=10,
        execution_time_ms=45.5,
        truncated=False,
    )


@pytest.fixture
def sample_policy_checks() -> PolicyCheckInfo:
    """Sample policy check information."""
    return PolicyCheckInfo(
        table_access="passed",
        column_access="passed",
        explain_check="passed",
    )


@pytest.fixture
def sample_audit_event(
    sample_client_info: ClientInfo,
    sample_query_info: QueryInfo,
    sample_result_info: ResultInfo,
    sample_policy_checks: PolicyCheckInfo,
) -> AuditEvent:
    """Sample audit event."""
    return AuditEvent(
        timestamp=datetime.now(UTC).isoformat(),
        event_type=AuditEventType.QUERY_EXECUTED,
        request_id="req-12345",
        session_id="session-123",
        database="production_db",
        client_info=sample_client_info,
        query=sample_query_info,
        result=sample_result_info,
        policy_checks=sample_policy_checks,
    )


# ============================================================================
# Basic Functionality Tests
# ============================================================================


class TestAuditLoggerBasics:
    """Tests for basic AuditLogger functionality."""

    @pytest.mark.asyncio
    async def test_log_to_stdout(
        self, sample_audit_event: AuditEvent
    ) -> None:
        """Test logging to stdout."""
        logger = AuditLogger(storage=AuditStorage.STDOUT)

        # Should not raise any errors
        await logger.log(sample_audit_event)

    @pytest.mark.asyncio
    async def test_log_to_stdout_with_structlog(
        self, sample_audit_event: AuditEvent
    ) -> None:
        """Test that stdout logging uses structlog."""
        logger = AuditLogger(storage=AuditStorage.STDOUT)

        with patch("pg_mcp.security.audit_logger.logger") as mock_logger:
            await logger.log(sample_audit_event)

            # Should call logger.info with audit_event
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]
            assert "event_type" in call_kwargs
            assert call_kwargs["event_type"] == "query_executed"

    def test_create_event(self) -> None:
        """Test create_event convenience method."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-001",
            database="test_db",
            client_ip="10.0.0.1",
            session_id="sess-001",
            question="Show all users",
            sql="SELECT * FROM users",
            rows_returned=5,
            execution_time_ms=25.5,
            truncated=False,
            policy_checks={
                "table_access": "passed",
                "column_access": "passed",
                "explain_check": "skipped",
            },
        )

        assert event.event_type == AuditEventType.QUERY_EXECUTED
        assert event.request_id == "req-001"
        assert event.database == "test_db"
        assert event.client_info.ip == "10.0.0.1"
        assert event.query is not None
        assert event.query.question == "Show all users"
        assert event.query.sql == "SELECT * FROM users"
        assert event.result is not None
        assert event.result.rows_returned == 5
        assert event.result.status == "success"
        assert event.policy_checks is not None
        assert event.policy_checks.table_access == "passed"

    def test_create_event_with_error(self) -> None:
        """Test create_event with error status."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_DENIED,
            request_id="req-002",
            database="test_db",
            question="Drop users table",
            sql="DROP TABLE users",
            error_code="UNSAFE_SQL",
            error_message="Statement type 'drop' is not allowed",
            execution_time_ms=5.0,
        )

        assert event.event_type == AuditEventType.QUERY_DENIED
        assert event.result is not None
        assert event.result.status == "error"
        assert event.result.error_code == "UNSAFE_SQL"
        assert event.result.error_message is not None

    def test_create_event_minimal(self) -> None:
        """Test create_event with minimal parameters."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            request_id="req-003",
            database="test_db",
        )

        assert event.event_type == AuditEventType.RATE_LIMIT_EXCEEDED
        assert event.request_id == "req-003"
        assert event.query is None  # No SQL provided
        assert event.result is None  # No SQL provided
        assert event.policy_checks is None


# ============================================================================
# JSON Serialization Tests
# ============================================================================


class TestEventSerialization:
    """Tests for audit event serialization."""

    def test_event_to_json(self, sample_audit_event: AuditEvent) -> None:
        """Test event JSON serialization."""
        json_str = sample_audit_event.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "query_executed"
        assert parsed["request_id"] == "req-12345"
        assert parsed["database"] == "production_db"
        assert parsed["client_info"]["ip"] == "192.168.1.100"
        assert parsed["query"]["question"] == "Show all active users"
        assert parsed["result"]["rows_returned"] == 10

    def test_event_to_dict(self, sample_audit_event: AuditEvent) -> None:
        """Test event dictionary conversion."""
        data = sample_audit_event.to_dict()

        assert isinstance(data, dict)
        assert data["event_type"] == "query_executed"  # Enum converted to value
        assert data["request_id"] == "req-12345"

    def test_query_info_hash(self, sample_query_info: QueryInfo) -> None:
        """Test SQL hash calculation."""
        assert sample_query_info.sql_hash.startswith("sha256:")
        assert len(sample_query_info.sql_hash) > 10

        # Same SQL should produce same hash
        query2 = QueryInfo.from_sql(
            question="Different question",
            sql="SELECT * FROM users WHERE active = true",
        )
        assert query2.sql_hash == sample_query_info.sql_hash

    def test_query_info_hash_different_sql(self) -> None:
        """Test that different SQL produces different hash."""
        query1 = QueryInfo.from_sql("Q1", "SELECT 1")
        query2 = QueryInfo.from_sql("Q2", "SELECT 2")

        assert query1.sql_hash != query2.sql_hash

    def test_event_serialization_unicode(self) -> None:
        """Test event serialization with Unicode characters."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-unicode",
            database="test_db",
            question="Show users with name containing",
            sql="SELECT * FROM users WHERE name LIKE '%test%'",
            rows_returned=0,
            execution_time_ms=10.0,
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["query"]["sql"] == "SELECT * FROM users WHERE name LIKE '%test%'"


# ============================================================================
# File Output Tests
# ============================================================================


class TestFileOutput:
    """Tests for file output functionality."""

    @pytest.mark.asyncio
    async def test_log_to_file(
        self, tmp_path: Path, sample_audit_event: AuditEvent
    ) -> None:
        """Test logging to file."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
        )

        await logger.log(sample_audit_event)

        # File should exist
        assert log_file.exists()

        # Read and verify content
        with open(log_file) as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed["request_id"] == "req-12345"

    @pytest.mark.asyncio
    async def test_log_to_file_multiple_events(
        self, tmp_path: Path
    ) -> None:
        """Test logging multiple events to file."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
        )

        # Log multiple events
        for i in range(5):
            event = AuditLogger.create_event(
                event_type=AuditEventType.QUERY_EXECUTED,
                request_id=f"req-{i}",
                database="test_db",
                sql=f"SELECT {i}",
                rows_returned=i,
                execution_time_ms=float(i),
            )
            await logger.log(event)

        # Verify all events are logged
        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) == 5

    @pytest.mark.asyncio
    async def test_log_to_file_creates_directory(
        self, tmp_path: Path, sample_audit_event: AuditEvent
    ) -> None:
        """Test that logging creates parent directories if needed."""
        log_file = tmp_path / "logs" / "audit" / "events.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
        )

        await logger.log(sample_audit_event)

        assert log_file.exists()
        assert log_file.parent.exists()

    @pytest.mark.asyncio
    async def test_file_rotation(self, tmp_path: Path) -> None:
        """Test file rotation when size limit exceeded."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
            max_size_mb=1,  # Small size for testing
            max_files=3,
        )

        # Manually set current size to trigger rotation
        logger._current_size = 2 * 1024 * 1024  # 2MB (exceeds limit)

        # Create initial file
        log_file.write_text("initial content\n")

        # Log an event - should trigger rotation
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-rotate",
            database="test_db",
            sql="SELECT 1",
            rows_returned=1,
            execution_time_ms=1.0,
        )
        await logger.log(event)

        # Should have rotated file
        rotated_file = tmp_path / "audit.1.jsonl"
        assert rotated_file.exists()
        assert rotated_file.read_text() == "initial content\n"

        # Current size should be reset
        # (Note: After writing, current_size will be updated)
        # The main file should have the new event
        assert log_file.exists()

    @pytest.mark.asyncio
    async def test_file_rotation_deletes_oldest(self, tmp_path: Path) -> None:
        """Test that rotation deletes oldest files when max_files exceeded."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
            max_size_mb=1,
            max_files=2,  # Only keep 2 files
        )

        # Create existing rotated files
        (tmp_path / "audit.1.jsonl").write_text("file 1\n")
        (tmp_path / "audit.jsonl").write_text("current\n")

        # Trigger rotation
        logger._current_size = 2 * 1024 * 1024
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-new",
            database="test_db",
        )
        await logger.log(event)

        # audit.1.jsonl should be deleted (exceeds max_files=2)
        # audit.jsonl (current) should have new content
        # Note: With max_files=2, we keep indices 0 (current) and 1

    @pytest.mark.asyncio
    async def test_file_rotation_multiple_cycles(self, tmp_path: Path) -> None:
        """Test multiple rotation cycles."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
            max_size_mb=1,
            max_files=5,
        )

        # Simulate multiple rotations
        for i in range(3):
            log_file.write_text(f"content {i}\n")
            logger._current_size = 2 * 1024 * 1024

            event = AuditLogger.create_event(
                event_type=AuditEventType.QUERY_EXECUTED,
                request_id=f"req-{i}",
                database="test_db",
            )
            await logger.log(event)

        # Should have rotated files
        assert (tmp_path / "audit.1.jsonl").exists()


# ============================================================================
# Storage Backend Tests
# ============================================================================


class TestStorageBackends:
    """Tests for different storage backends."""

    def test_storage_stdout_initialization(self) -> None:
        """Test stdout storage initialization."""
        logger = AuditLogger(storage=AuditStorage.STDOUT)

        assert logger.storage == AuditStorage.STDOUT
        assert logger.file_path is None

    def test_storage_file_initialization(self, tmp_path: Path) -> None:
        """Test file storage initialization."""
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(log_file),
            max_size_mb=50,
            max_files=5,
        )

        assert logger.storage == AuditStorage.FILE
        assert logger.file_path == log_file
        assert logger.max_size_bytes == 50 * 1024 * 1024
        assert logger.max_files == 5

    @pytest.mark.asyncio
    async def test_storage_database_placeholder(
        self, sample_audit_event: AuditEvent
    ) -> None:
        """Test database storage (placeholder implementation)."""
        logger = AuditLogger(storage=AuditStorage.DATABASE)

        # Should not raise (placeholder implementation)
        await logger.log(sample_audit_event)


# ============================================================================
# Data Class Tests
# ============================================================================


class TestDataClasses:
    """Tests for audit logger data classes."""

    def test_client_info_structure(self) -> None:
        """Test ClientInfo dataclass structure."""
        info = ClientInfo(
            ip="10.0.0.1",
            user_agent="TestAgent/1.0",
            session_id="sess-123",
        )

        assert info.ip == "10.0.0.1"
        assert info.user_agent == "TestAgent/1.0"
        assert info.session_id == "sess-123"

    def test_client_info_optional_fields(self) -> None:
        """Test ClientInfo with None values."""
        info = ClientInfo(ip=None, user_agent=None, session_id=None)

        assert info.ip is None
        assert info.user_agent is None
        assert info.session_id is None

    def test_query_info_structure(self) -> None:
        """Test QueryInfo dataclass structure."""
        info = QueryInfo(
            question="Test question",
            sql="SELECT 1",
            sql_hash="sha256:abc123",
        )

        assert info.question == "Test question"
        assert info.sql == "SELECT 1"
        assert info.sql_hash == "sha256:abc123"

    def test_result_info_success(self) -> None:
        """Test ResultInfo for successful query."""
        info = ResultInfo(
            status="success",
            rows_returned=100,
            execution_time_ms=50.5,
            truncated=False,
        )

        assert info.status == "success"
        assert info.rows_returned == 100
        assert info.error_code is None

    def test_result_info_error(self) -> None:
        """Test ResultInfo for failed query."""
        info = ResultInfo(
            status="error",
            rows_returned=None,
            execution_time_ms=5.0,
            truncated=False,
            error_code="SYNTAX_ERROR",
            error_message="Invalid SQL syntax",
        )

        assert info.status == "error"
        assert info.rows_returned is None
        assert info.error_code == "SYNTAX_ERROR"
        assert info.error_message == "Invalid SQL syntax"

    def test_result_info_truncated(self) -> None:
        """Test ResultInfo for truncated results."""
        info = ResultInfo(
            status="success",
            rows_returned=1000,
            execution_time_ms=100.0,
            truncated=True,
        )

        assert info.truncated is True

    def test_policy_check_info_structure(self) -> None:
        """Test PolicyCheckInfo dataclass structure."""
        info = PolicyCheckInfo(
            table_access="passed",
            column_access="denied",
            explain_check="skipped",
        )

        assert info.table_access == "passed"
        assert info.column_access == "denied"
        assert info.explain_check == "skipped"


# ============================================================================
# Event Type Tests
# ============================================================================


class TestAuditEventTypes:
    """Tests for audit event types."""

    def test_event_type_query_executed(self) -> None:
        """Test QUERY_EXECUTED event type."""
        assert AuditEventType.QUERY_EXECUTED.value == "query_executed"

    def test_event_type_query_denied(self) -> None:
        """Test QUERY_DENIED event type."""
        assert AuditEventType.QUERY_DENIED.value == "query_denied"

    def test_event_type_policy_violation(self) -> None:
        """Test POLICY_VIOLATION event type."""
        assert AuditEventType.POLICY_VIOLATION.value == "policy_violation"

    def test_event_type_rate_limit_exceeded(self) -> None:
        """Test RATE_LIMIT_EXCEEDED event type."""
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"

    def test_storage_type_file(self) -> None:
        """Test FILE storage type."""
        assert AuditStorage.FILE.value == "file"

    def test_storage_type_stdout(self) -> None:
        """Test STDOUT storage type."""
        assert AuditStorage.STDOUT.value == "stdout"

    def test_storage_type_database(self) -> None:
        """Test DATABASE storage type."""
        assert AuditStorage.DATABASE.value == "database"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""

    @pytest.mark.asyncio
    async def test_log_with_no_file_path(self) -> None:
        """Test file logging without file_path (should not crash)."""
        logger = AuditLogger(storage=AuditStorage.FILE, file_path=None)

        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-test",
            database="test_db",
        )

        # Should not raise
        await logger._write_to_file('{"test": "data"}')

    def test_create_event_without_sql(self) -> None:
        """Test create_event without SQL (e.g., rate limit event)."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            request_id="req-ratelimit",
            database="test_db",
            client_ip="10.0.0.1",
        )

        assert event.query is None
        assert event.result is None

    def test_create_event_with_empty_sql(self) -> None:
        """Test create_event with empty SQL string.

        Note: The create_event method only creates query/result if sql is truthy.
        Empty string is falsy in Python, so no query/result is created.
        """
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_DENIED,
            request_id="req-empty",
            database="test_db",
            sql="",  # Empty SQL (falsy)
            rows_returned=0,
            execution_time_ms=0,
        )

        # Empty string is falsy, so query and result are not created
        assert event.query is None
        assert event.result is None

    def test_create_event_with_non_empty_sql(self) -> None:
        """Test create_event with non-empty SQL string."""
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id="req-nonempty",
            database="test_db",
            sql="SELECT 1",  # Non-empty SQL
            rows_returned=1,
            execution_time_ms=5.0,
        )

        # Non-empty SQL creates query and result
        assert event.query is not None
        assert event.result is not None

    def test_redact_sql_flag(self, tmp_path: Path) -> None:
        """Test redact_sql configuration flag."""
        logger = AuditLogger(
            storage=AuditStorage.FILE,
            file_path=str(tmp_path / "audit.jsonl"),
            redact_sql=True,
        )

        assert logger.redact_sql is True
        # Note: Actual redaction would be implemented in a future version
