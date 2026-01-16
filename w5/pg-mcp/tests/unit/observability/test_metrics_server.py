"""Unit tests for MetricsServer HTTP endpoint.

This module tests the Prometheus metrics HTTP server functionality including:
- Server startup and shutdown
- HTTP endpoint responses
- Metrics accessibility via HTTP
"""

import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from prometheus_client import CollectorRegistry, Counter

from pg_mcp.observability.metrics_server import (
    MetricsServer,
    get_metrics_server,
    start_metrics_server,
    stop_metrics_server,
)


class TestMetricsServer:
    """Tests for MetricsServer class."""

    @pytest.fixture
    def registry(self) -> CollectorRegistry:
        """Create an isolated CollectorRegistry for testing."""
        return CollectorRegistry()

    @pytest.fixture
    def registry_with_metrics(self, registry: CollectorRegistry) -> CollectorRegistry:
        """Create a registry with some test metrics."""
        Counter(
            "test_counter",
            "A test counter",
            registry=registry,
        ).inc()
        return registry

    @pytest_asyncio.fixture
    async def server(self, registry: CollectorRegistry) -> MetricsServer:
        """Create a MetricsServer instance."""
        # Use a high port to avoid conflicts
        server = MetricsServer(port=19090, registry=registry)
        yield server
        # Ensure cleanup
        if server.is_running:
            await server.stop()

    def test_initialization(self, registry: CollectorRegistry) -> None:
        """Test that server initializes with correct configuration."""
        server = MetricsServer(port=9090, registry=registry, path="/metrics")

        assert server.port == 9090
        assert server._path == "/metrics"
        assert server._registry is registry
        assert not server.is_running

    def test_initialization_with_custom_path(self, registry: CollectorRegistry) -> None:
        """Test server initialization with custom path."""
        server = MetricsServer(port=9090, registry=registry, path="/custom/metrics")

        assert server._path == "/custom/metrics"

    def test_initialization_path_normalization(self, registry: CollectorRegistry) -> None:
        """Test that trailing slashes are stripped from path."""
        server = MetricsServer(port=9090, registry=registry, path="/metrics/")

        assert server._path == "/metrics"

    def test_initialization_root_path(self, registry: CollectorRegistry) -> None:
        """Test that root path is preserved."""
        server = MetricsServer(port=9090, registry=registry, path="/")

        assert server._path == "/"

    @pytest.mark.asyncio
    async def test_start_and_stop(self, server: MetricsServer) -> None:
        """Test server starts and stops cleanly."""
        assert not server.is_running

        await server.start()
        assert server.is_running

        await server.stop()
        assert not server.is_running

    @pytest.mark.asyncio
    async def test_start_twice_raises_error(self, server: MetricsServer) -> None:
        """Test that starting an already running server raises an error."""
        await server.start()

        with pytest.raises(RuntimeError, match="already running"):
            await server.start()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, registry: CollectorRegistry) -> None:
        """Test that stopping a non-running server does nothing."""
        server = MetricsServer(port=19091, registry=registry)

        # Should not raise
        await server.stop()
        assert not server.is_running

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(
        self, registry_with_metrics: CollectorRegistry
    ) -> None:
        """Test that /metrics endpoint returns Prometheus format."""
        server = MetricsServer(port=19092, registry=registry_with_metrics)
        await server.start()

        try:
            # Connect and send HTTP request
            reader, writer = await asyncio.open_connection("127.0.0.1", 19092)

            request = b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            # Read response
            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            # Verify response
            assert "HTTP/1.1 200 OK" in response_text
            assert "text/plain" in response_text or "openmetrics" in response_text
            assert "test_counter" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_health_endpoint(self, server: MetricsServer) -> None:
        """Test that /health endpoint returns OK."""
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19090)

            request = b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            assert "HTTP/1.1 200 OK" in response_text
            assert "OK" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_healthz_endpoint(self, server: MetricsServer) -> None:
        """Test that /healthz endpoint returns OK."""
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19090)

            request = b"GET /healthz HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            assert "HTTP/1.1 200 OK" in response_text
            assert "OK" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, server: MetricsServer) -> None:
        """Test that unknown endpoints return 404."""
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19090)

            request = b"GET /unknown HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            assert "HTTP/1.1 404 Not Found" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, server: MetricsServer) -> None:
        """Test that non-GET methods return 405."""
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19090)

            request = b"POST /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            assert "HTTP/1.1 405 Method Not Allowed" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_metrics_with_trailing_slash(self, server: MetricsServer) -> None:
        """Test that /metrics/ also works."""
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19090)

            request = b"GET /metrics/ HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(4096)
            response_text = response.decode("utf-8")

            assert "HTTP/1.1 200 OK" in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def registry(self) -> CollectorRegistry:
        """Create an isolated CollectorRegistry for testing."""
        return CollectorRegistry()

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self) -> None:
        """Ensure module-level server is stopped after each test."""
        yield
        await stop_metrics_server()

    @pytest.mark.asyncio
    async def test_start_and_stop_metrics_server(
        self, registry: CollectorRegistry
    ) -> None:
        """Test start_metrics_server and stop_metrics_server functions."""
        server = await start_metrics_server(port=19093, registry=registry)

        assert server.is_running
        assert get_metrics_server() is server

        await stop_metrics_server()

        assert not server.is_running
        assert get_metrics_server() is None

    @pytest.mark.asyncio
    async def test_start_metrics_server_twice_raises_error(
        self, registry: CollectorRegistry
    ) -> None:
        """Test that starting server twice raises an error."""
        await start_metrics_server(port=19094, registry=registry)

        with pytest.raises(RuntimeError, match="already running"):
            await start_metrics_server(port=19095, registry=registry)

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self) -> None:
        """Test that stop_metrics_server does nothing when not started."""
        # Should not raise
        await stop_metrics_server()
        assert get_metrics_server() is None

    @pytest.mark.asyncio
    async def test_get_metrics_server_returns_none_initially(self) -> None:
        """Test that get_metrics_server returns None when not started."""
        # Reset module state by patching
        with patch(
            "pg_mcp.observability.metrics_server._metrics_server", None
        ):
            assert get_metrics_server() is None


class TestMetricsServerIntegration:
    """Integration tests for MetricsServer with MetricsCollector."""

    @pytest.mark.asyncio
    async def test_server_exposes_collector_metrics(self) -> None:
        """Test that server exposes metrics from MetricsCollector."""
        from pg_mcp.observability.metrics import MetricsCollector

        # Create collector with isolated registry
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        # Record some metrics
        collector.record_request(
            database="testdb",
            status="success",
            duration=0.5,
        )

        # Create and start server with the same registry
        server = MetricsServer(port=19096, registry=registry)
        await server.start()

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 19096)

            request = b"GET /metrics HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request)
            await writer.drain()

            response = await reader.read(8192)
            response_text = response.decode("utf-8")

            # Verify our metrics are present
            assert "pg_mcp_requests_total" in response_text
            assert 'database="testdb"' in response_text
            assert 'status="success"' in response_text

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()
