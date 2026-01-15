"""Unit tests for logging utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestSlowQueryLogger:
    """Tests for SlowQueryLogger class."""

    def test_default_threshold_value(self) -> None:
        """Test that default threshold is 5.0 seconds."""
        from pg_mcp.observability.logging import SlowQueryLogger

        logger = SlowQueryLogger()
        assert logger.threshold == 5.0
        assert logger.log_sql is False

    def test_custom_threshold_value(self) -> None:
        """Test custom threshold value."""
        from pg_mcp.observability.logging import SlowQueryLogger

        logger = SlowQueryLogger(threshold=10.0, log_sql=True)
        assert logger.threshold == 10.0
        assert logger.log_sql is True

    def test_log_if_slow_does_not_log_below_threshold(self) -> None:
        """Test log_if_slow() does NOT log when duration < threshold."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=5.0)
        logger.logger = mock_logger

        logger.log_if_slow(
            duration=4.9,  # Below 5.0 threshold
            database="testdb",
            sql="SELECT * FROM users",
            rows=100,
        )

        mock_logger.warning.assert_not_called()

    def test_log_if_slow_logs_at_threshold(self) -> None:
        """Test log_if_slow() logs when duration == threshold."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=5.0)
        logger.logger = mock_logger

        logger.log_if_slow(
            duration=5.0,  # Exactly at threshold
            database="testdb",
            sql="SELECT * FROM users",
            rows=100,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "slow_query_detected"
        assert call_args[1]["database"] == "testdb"
        assert call_args[1]["duration_seconds"] == 5.0
        assert call_args[1]["rows_returned"] == 100

    def test_log_if_slow_logs_above_threshold(self) -> None:
        """Test log_if_slow() logs when duration > threshold."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=5.0)
        logger.logger = mock_logger

        logger.log_if_slow(
            duration=6.5,
            database="analytics",
            sql="SELECT * FROM large_table",
            rows=10000,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "slow_query_detected"
        assert call_args[1]["database"] == "analytics"
        assert call_args[1]["duration_seconds"] == 6.5
        assert call_args[1]["rows_returned"] == 10000

    def test_log_if_slow_truncates_long_sql_when_log_sql_true(self) -> None:
        """Test log_if_slow() truncates SQL when log_sql=True and SQL > 500 chars."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=1.0, log_sql=True)
        logger.logger = mock_logger

        # Create a SQL string longer than 500 characters
        long_sql = "SELECT " + "a" * 600 + " FROM table"

        logger.log_if_slow(
            duration=2.0,
            database="testdb",
            sql=long_sql,
            rows=50,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        # SQL should be truncated to 500 characters
        assert len(call_args[1]["sql"]) == 500
        assert call_args[1]["sql_truncated"] is True

    def test_log_if_slow_does_not_truncate_short_sql(self) -> None:
        """Test log_if_slow() does not truncate SQL when <= 500 chars."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=1.0, log_sql=True)
        logger.logger = mock_logger

        short_sql = "SELECT * FROM users WHERE id = 1"

        logger.log_if_slow(
            duration=2.0,
            database="testdb",
            sql=short_sql,
            rows=1,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        # SQL should not be truncated
        assert call_args[1]["sql"] == short_sql
        assert "sql_truncated" not in call_args[1]

    def test_log_if_slow_only_logs_sql_length_when_log_sql_false(self) -> None:
        """Test log_if_slow() only logs sql_length when log_sql=False."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=5.0, log_sql=False)
        logger.logger = mock_logger

        sql = "SELECT * FROM users WHERE id = 1"

        logger.log_if_slow(
            duration=6.0,
            database="testdb",
            sql=sql,
            rows=1,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        # Should have sql_length but not sql
        assert "sql" not in call_args[1]
        assert call_args[1]["sql_length"] == len(sql)

    def test_log_if_slow_rounds_duration(self) -> None:
        """Test that duration is rounded to 3 decimal places."""
        from pg_mcp.observability.logging import SlowQueryLogger

        mock_logger = MagicMock()
        logger = SlowQueryLogger(threshold=5.0)
        logger.logger = mock_logger

        logger.log_if_slow(
            duration=5.123456789,
            database="testdb",
            sql="SELECT 1",
            rows=1,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["duration_seconds"] == 5.123


class TestAddTraceId:
    """Tests for add_trace_id function."""

    def test_adds_trace_id_when_tracing_manager_returns_valid_id(self) -> None:
        """Test that it adds trace_id when TracingManager returns a valid trace_id."""
        from pg_mcp.observability.logging import add_trace_id

        # Mock the tracing manager
        mock_manager = MagicMock()
        mock_manager.get_current_trace_id.return_value = "abc123def456"

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            return_value=mock_manager,
        ):
            event_dict: dict = {"event": "test_event", "level": "info"}
            result = add_trace_id(None, "info", event_dict)

            assert result["trace_id"] == "abc123def456"
            assert result["event"] == "test_event"

    def test_does_not_add_trace_id_when_manager_is_none(self) -> None:
        """Test that it doesn't add trace_id when TracingManager is None."""
        from pg_mcp.observability.logging import add_trace_id

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            return_value=None,
        ):
            event_dict: dict = {"event": "test_event", "level": "info"}
            result = add_trace_id(None, "info", event_dict)

            assert "trace_id" not in result
            assert result["event"] == "test_event"

    def test_does_not_add_trace_id_when_trace_id_is_none(self) -> None:
        """Test that it doesn't add trace_id when get_current_trace_id returns None."""
        from pg_mcp.observability.logging import add_trace_id

        mock_manager = MagicMock()
        mock_manager.get_current_trace_id.return_value = None

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            return_value=mock_manager,
        ):
            event_dict: dict = {"event": "test_event"}
            result = add_trace_id(None, "info", event_dict)

            assert "trace_id" not in result

    def test_does_not_add_trace_id_when_trace_id_is_empty_string(self) -> None:
        """Test that it doesn't add trace_id when get_current_trace_id returns empty string."""
        from pg_mcp.observability.logging import add_trace_id

        mock_manager = MagicMock()
        mock_manager.get_current_trace_id.return_value = ""

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            return_value=mock_manager,
        ):
            event_dict: dict = {"event": "test_event"}
            result = add_trace_id(None, "info", event_dict)

            assert "trace_id" not in result

    def test_handles_import_error_gracefully(self) -> None:
        """Test that it handles ImportError gracefully."""
        import sys

        from pg_mcp.observability.logging import add_trace_id

        # Temporarily remove the tracing module to simulate ImportError
        # We need to use patch.dict to simulate the module not being available
        with patch.dict(sys.modules, {"pg_mcp.observability.tracing": None}):
            event_dict: dict = {"event": "test_event"}
            result = add_trace_id(None, "info", event_dict)

            # Should return event_dict unchanged without trace_id
            assert "trace_id" not in result
            assert result["event"] == "test_event"

    def test_handles_general_exception_gracefully(self) -> None:
        """Test that it handles exceptions gracefully."""
        from pg_mcp.observability.logging import add_trace_id

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            side_effect=RuntimeError("Unexpected error"),
        ):
            event_dict: dict = {"event": "test_event"}
            result = add_trace_id(None, "info", event_dict)

            # Should return event_dict unchanged without trace_id
            assert "trace_id" not in result
            assert result["event"] == "test_event"

    def test_handles_exception_from_get_current_trace_id(self) -> None:
        """Test that it handles exceptions from get_current_trace_id gracefully."""
        from pg_mcp.observability.logging import add_trace_id

        mock_manager = MagicMock()
        mock_manager.get_current_trace_id.side_effect = RuntimeError("Tracing error")

        with patch(
            "pg_mcp.observability.tracing.get_tracing_manager",
            return_value=mock_manager,
        ):
            event_dict: dict = {"event": "test_event"}
            result = add_trace_id(None, "info", event_dict)

            # Should return event_dict unchanged without trace_id
            assert "trace_id" not in result
            assert result["event"] == "test_event"


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_with_json_format(self) -> None:
        """Test setup_logging with json format."""
        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure") as mock_configure:
            setup_logging(level="INFO", format="json", include_trace_id=False)

            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]

            # Check that processors list contains JSONRenderer
            processors = call_kwargs["processors"]
            processor_types = [type(p).__name__ for p in processors]
            assert "JSONRenderer" in processor_types

    def test_setup_logging_with_text_format(self) -> None:
        """Test setup_logging with text format."""
        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure") as mock_configure:
            setup_logging(level="INFO", format="text", include_trace_id=False)

            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]

            # Check that processors list contains ConsoleRenderer
            processors = call_kwargs["processors"]
            processor_types = [type(p).__name__ for p in processors]
            assert "ConsoleRenderer" in processor_types

    def test_setup_logging_with_debug_level(self) -> None:
        """Test setup_logging with DEBUG log level."""
        import logging

        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure"), patch("logging.basicConfig") as mock_basic_config:
            setup_logging(level="DEBUG", format="json", include_trace_id=False)

            # Verify basicConfig was called with DEBUG level
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG

    def test_setup_logging_with_warning_level(self) -> None:
        """Test setup_logging with WARNING log level."""
        import logging

        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure"), patch("logging.basicConfig") as mock_basic_config:
            setup_logging(level="WARNING", format="json", include_trace_id=False)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.WARNING

    def test_setup_logging_with_error_level(self) -> None:
        """Test setup_logging with ERROR log level."""
        import logging

        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure"), patch("logging.basicConfig") as mock_basic_config:
            setup_logging(level="ERROR", format="json", include_trace_id=False)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.ERROR

    def test_setup_logging_includes_trace_id_processor(self) -> None:
        """Test setup_logging includes add_trace_id processor when include_trace_id=True."""
        from pg_mcp.observability.logging import add_trace_id, setup_logging

        with patch("structlog.configure") as mock_configure:
            setup_logging(level="INFO", format="json", include_trace_id=True)

            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]

            # Check that add_trace_id is in the processors list
            processors = call_kwargs["processors"]
            assert add_trace_id in processors

    def test_setup_logging_excludes_trace_id_processor(self) -> None:
        """Test setup_logging excludes add_trace_id processor when include_trace_id=False."""
        from pg_mcp.observability.logging import add_trace_id, setup_logging

        with patch("structlog.configure") as mock_configure:
            setup_logging(level="INFO", format="json", include_trace_id=False)

            mock_configure.assert_called_once()
            call_kwargs = mock_configure.call_args[1]

            # Check that add_trace_id is NOT in the processors list
            processors = call_kwargs["processors"]
            assert add_trace_id not in processors

    def test_setup_logging_case_insensitive_level(self) -> None:
        """Test setup_logging handles lowercase level strings."""
        import logging

        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure"), patch("logging.basicConfig") as mock_basic_config:
            setup_logging(level="info", format="json", include_trace_id=False)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.INFO

    def test_setup_logging_invalid_level_defaults_to_info(self) -> None:
        """Test setup_logging defaults to INFO for invalid level."""
        import logging

        from pg_mcp.observability.logging import setup_logging

        with patch("structlog.configure"), patch("logging.basicConfig") as mock_basic_config:
            setup_logging(level="INVALID_LEVEL", format="json", include_trace_id=False)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            # getattr with default INFO should be used for invalid level
            assert call_kwargs["level"] == logging.INFO

    def test_setup_logging_default_values(self) -> None:
        """Test setup_logging with default parameter values."""
        import logging

        from pg_mcp.observability.logging import add_trace_id, setup_logging

        with patch("structlog.configure") as mock_configure, patch(
            "logging.basicConfig"
        ) as mock_basic_config:
            # Call with no arguments to test defaults
            setup_logging()

            # Default level is INFO
            mock_basic_config.assert_called_once()
            basic_config_kwargs = mock_basic_config.call_args[1]
            assert basic_config_kwargs["level"] == logging.INFO

            # Default format is json, include_trace_id is True
            mock_configure.assert_called_once()
            configure_kwargs = mock_configure.call_args[1]
            processors = configure_kwargs["processors"]

            # Should have add_trace_id (include_trace_id=True by default)
            assert add_trace_id in processors

            # Should have JSONRenderer (format="json" by default)
            processor_types = [type(p).__name__ for p in processors]
            assert "JSONRenderer" in processor_types
