"""Unit tests for MetricsCollector."""

import pytest
from prometheus_client import CollectorRegistry

from pg_mcp.observability.metrics import MetricsCollector


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a MetricsCollector with isolated registry."""
        return MetricsCollector(registry=CollectorRegistry())

    def test_initialization(self, collector: MetricsCollector) -> None:
        """Test that collector initializes correctly."""
        assert collector.registry is not None
        assert collector.requests_total is not None
        assert collector.request_duration is not None
        assert collector.requests_in_flight is not None

    def test_record_request(self, collector: MetricsCollector) -> None:
        """Test recording request metrics."""
        collector.record_request(
            database="testdb",
            status="success",
            duration=0.5,
        )

        # Verify counter was incremented
        assert (
            collector.requests_total.labels(
                database="testdb",
                status="success",
                error_code="",
            )._value.get()
            == 1.0
        )

    def test_record_request_with_error(self, collector: MetricsCollector) -> None:
        """Test recording request with error code."""
        collector.record_request(
            database="testdb",
            status="error",
            duration=0.1,
            error_code="UNSAFE_SQL",
        )

        assert (
            collector.requests_total.labels(
                database="testdb",
                status="error",
                error_code="UNSAFE_SQL",
            )._value.get()
            == 1.0
        )

    def test_record_sql_generation(self, collector: MetricsCollector) -> None:
        """Test recording SQL generation metrics."""
        collector.record_sql_generation(
            database="testdb",
            status="success",
            duration=1.5,
        )

        assert (
            collector.sql_generation_total.labels(
                database="testdb",
                status="success",
            )._value.get()
            == 1.0
        )

    def test_record_sql_retry(self, collector: MetricsCollector) -> None:
        """Test recording SQL retry metrics."""
        collector.record_sql_retry(database="testdb", reason="syntax_error")
        collector.record_sql_retry(database="testdb", reason="syntax_error")

        assert (
            collector.sql_retries_total.labels(
                database="testdb",
                reason="syntax_error",
            )._value.get()
            == 2.0
        )

    def test_record_db_query(self, collector: MetricsCollector) -> None:
        """Test recording database query metrics."""
        collector.record_db_query(database="testdb", duration=0.05)
        # Histogram observation doesn't have a simple getter,
        # but we can check the sum
        assert collector.db_query_duration.labels(database="testdb")._sum.get() == 0.05

    def test_record_openai_request(self, collector: MetricsCollector) -> None:
        """Test recording OpenAI request metrics."""
        collector.record_openai_request(
            status="success",
            duration=2.0,
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert collector.openai_requests_total.labels(status="success")._value.get() == 1.0
        assert collector.openai_tokens_total.labels(type="prompt")._value.get() == 100.0
        assert collector.openai_tokens_total.labels(type="completion")._value.get() == 50.0

    def test_record_rate_limit_exceeded(self, collector: MetricsCollector) -> None:
        """Test recording rate limit exceeded events."""
        collector.record_rate_limit_exceeded(limit_type="requests_minute")

        assert (
            collector.rate_limit_exceeded_total.labels(limit_type="requests_minute")._value.get()
            == 1.0
        )

    def test_record_policy_check(self, collector: MetricsCollector) -> None:
        """Test recording policy check results."""
        collector.record_policy_check(check_type="table_access", result="allowed")
        collector.record_policy_check(check_type="table_access", result="denied")

        assert (
            collector.policy_check_total.labels(
                check_type="table_access",
                result="allowed",
            )._value.get()
            == 1.0
        )
        assert (
            collector.policy_check_total.labels(
                check_type="table_access",
                result="denied",
            )._value.get()
            == 1.0
        )

    def test_update_pool_stats(self, collector: MetricsCollector) -> None:
        """Test updating pool statistics."""
        collector.update_pool_stats(database="testdb", size=10, available=5)

        assert collector.db_pool_size.labels(database="testdb")._value.get() == 10.0
        assert collector.db_pool_available.labels(database="testdb")._value.get() == 5.0

    def test_update_rate_limit_stats(self, collector: MetricsCollector) -> None:
        """Test updating rate limit statistics."""
        collector.update_rate_limit_stats(
            requests_minute=30,
            requests_hour=500,
            tokens_minute=5000,
        )

        assert (
            collector.rate_limit_current.labels(limit_type="requests_minute")._value.get() == 30.0
        )
        assert collector.rate_limit_current.labels(limit_type="requests_hour")._value.get() == 500.0
        assert (
            collector.rate_limit_current.labels(limit_type="tokens_minute")._value.get() == 5000.0
        )

    def test_set_service_info(self, collector: MetricsCollector) -> None:
        """Test setting service information."""
        collector.set_service_info(
            version="1.0.0",
            environment="production",
            instance="node-1",
        )

        # Verify via generate_metrics output
        output = collector.generate_metrics()
        assert b"pg_mcp_service_info" in output
        assert b'version="1.0.0"' in output
        assert b'environment="production"' in output
        assert b'instance="node-1"' in output

    def test_generate_metrics(self, collector: MetricsCollector) -> None:
        """Test generating Prometheus metrics output."""
        collector.record_request(database="testdb", status="success", duration=0.5)

        output = collector.generate_metrics()
        assert isinstance(output, bytes)
        assert b"pg_mcp_requests_total" in output
        assert b"testdb" in output

    def test_get_content_type(self, collector: MetricsCollector) -> None:
        """Test getting Prometheus content type."""
        content_type = collector.get_content_type()
        assert "text/plain" in content_type or "openmetrics" in content_type


class TestRequestTracker:
    """Tests for the request tracker context manager."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a MetricsCollector with isolated registry."""
        return MetricsCollector(registry=CollectorRegistry())

    def test_track_request_success(self, collector: MetricsCollector) -> None:
        """Test tracking a successful request."""
        with collector.track_request("testdb") as tracker:
            tracker.set_status("success")

        assert (
            collector.requests_total.labels(
                database="testdb",
                status="success",
                error_code="",
            )._value.get()
            == 1.0
        )
        # In-flight should be back to 0
        assert collector.requests_in_flight.labels(database="testdb")._value.get() == 0.0

    def test_track_request_error(self, collector: MetricsCollector) -> None:
        """Test tracking an error request."""
        with collector.track_request("testdb") as tracker:
            tracker.set_status("error", "UNSAFE_SQL")

        assert (
            collector.requests_total.labels(
                database="testdb",
                status="error",
                error_code="UNSAFE_SQL",
            )._value.get()
            == 1.0
        )

    def test_track_request_exception(self, collector: MetricsCollector) -> None:
        """Test that request is still tracked on exception."""
        try:
            with collector.track_request("testdb"):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Default status is "error" when no explicit set_status call
        assert (
            collector.requests_total.labels(
                database="testdb",
                status="error",
                error_code="",
            )._value.get()
            == 1.0
        )

    def test_track_request_duration(self, collector: MetricsCollector) -> None:
        """Test that request duration is recorded."""
        import time

        with collector.track_request("testdb") as tracker:
            time.sleep(0.1)  # Sleep for 100ms
            tracker.set_status("success")

        # Duration should be >= 0.1 seconds
        duration_sum = collector.request_duration.labels(database="testdb")._sum.get()
        assert duration_sum >= 0.1

    def test_in_flight_tracking(self, collector: MetricsCollector) -> None:
        """Test that in-flight requests are tracked correctly."""
        # Initially should be 0
        assert collector.requests_in_flight.labels(database="testdb")._value.get() == 0.0

        # Enter the context - should be 1
        tracker = collector.track_request("testdb")
        tracker.__enter__()
        assert collector.requests_in_flight.labels(database="testdb")._value.get() == 1.0

        # Exit - should be back to 0
        tracker.__exit__(None, None, None)
        assert collector.requests_in_flight.labels(database="testdb")._value.get() == 0.0
