"""HTTP server for Prometheus metrics scraping.

This module provides an async HTTP server that exposes Prometheus metrics
at a configurable endpoint for scraping by Prometheus or other monitoring tools.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

if TYPE_CHECKING:
    from asyncio import Server

logger = structlog.get_logger(__name__)


class MetricsServer:
    """Async HTTP server for exposing Prometheus metrics.

    This server provides a lightweight HTTP endpoint for Prometheus scraping.
    It runs in the background and does not block the main application.

    Usage:
        server = MetricsServer(port=9090, registry=my_registry)
        await server.start()
        # ... application runs ...
        await server.stop()
    """

    def __init__(
        self,
        port: int,
        registry: CollectorRegistry | None = None,
        path: str = "/metrics",
    ) -> None:
        """Initialize the metrics server.

        Args:
            port: The port to listen on
            registry: Optional custom CollectorRegistry. If not provided,
                     the default registry will be used.
            path: The path to expose metrics at (default: /metrics)
        """
        self._port = port
        self._registry = registry
        self._path = path.rstrip("/") if path != "/" else path
        self._server: Server | None = None
        self._started = False

    @property
    def port(self) -> int:
        """Get the configured port."""
        return self._port

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._started and self._server is not None

    async def start(self) -> None:
        """Start the metrics HTTP server.

        This method starts the server in the background and returns immediately.
        The server will continue running until stop() is called.

        Raises:
            RuntimeError: If the server is already running
            OSError: If the port is already in use
        """
        if self._started:
            raise RuntimeError("Metrics server is already running")

        self._server = await asyncio.start_server(
            self._handle_request,
            host="0.0.0.0",  # noqa: S104 - binding to all interfaces is intentional for metrics
            port=self._port,
        )

        self._started = True
        logger.info(
            "Metrics server started",
            port=self._port,
            path=self._path,
        )

    async def stop(self) -> None:
        """Stop the metrics HTTP server.

        This method gracefully shuts down the server and waits for all
        connections to close.
        """
        if not self._started or self._server is None:
            logger.debug("Metrics server not running, nothing to stop")
            return

        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self._started = False

        logger.info("Metrics server stopped")

    async def _handle_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an incoming HTTP request.

        Args:
            reader: The stream reader for the connection
            writer: The stream writer for the connection
        """
        try:
            # Read the request line
            request_line = await reader.readline()
            if not request_line:
                return

            # Parse the request
            request_str = request_line.decode("utf-8", errors="replace").strip()
            parts = request_str.split()

            if len(parts) < 2:
                await self._send_response(writer, 400, b"Bad Request")
                return

            method, path = parts[0], parts[1]

            # Drain remaining headers
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break

            # Only handle GET requests to the metrics path
            if method != "GET":
                await self._send_response(writer, 405, b"Method Not Allowed")
                return

            # Handle metrics endpoint
            if path == self._path or path == f"{self._path}/":
                metrics_output = self._generate_metrics()
                await self._send_response(
                    writer,
                    200,
                    metrics_output,
                    content_type=CONTENT_TYPE_LATEST,
                )
                return

            # Handle health check endpoint
            if path == "/health" or path == "/healthz":
                await self._send_response(writer, 200, b"OK")
                return

            # Not found
            await self._send_response(writer, 404, b"Not Found")

        except (ConnectionResetError, BrokenPipeError):
            # Client disconnected, ignore
            pass
        except Exception:
            logger.exception("Error handling metrics request")
            try:
                await self._send_response(writer, 500, b"Internal Server Error")
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus exposition format metrics as bytes
        """
        if self._registry is not None:
            return generate_latest(self._registry)
        # Use default registry if none provided
        return generate_latest()

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: bytes,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        """Send an HTTP response.

        Args:
            writer: The stream writer
            status_code: HTTP status code
            body: Response body
            content_type: Content-Type header value
        """
        status_messages = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }
        status_message = status_messages.get(status_code, "Unknown")

        response = (
            f"HTTP/1.1 {status_code} {status_message}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        writer.write(response.encode("utf-8"))
        writer.write(body)
        await writer.drain()


# Module-level server instance for convenience functions
_metrics_server: MetricsServer | None = None


async def start_metrics_server(
    port: int,
    registry: CollectorRegistry | None = None,
    path: str = "/metrics",
) -> MetricsServer:
    """Start a metrics HTTP server.

    This is a convenience function that creates and starts a MetricsServer instance.
    The server runs in the background and does not block.

    Args:
        port: The port to listen on
        registry: Optional custom CollectorRegistry
        path: The path to expose metrics at (default: /metrics)

    Returns:
        The started MetricsServer instance

    Raises:
        RuntimeError: If a metrics server is already running
        OSError: If the port is already in use

    Example:
        server = await start_metrics_server(9090)
        # ... later ...
        await stop_metrics_server()
    """
    global _metrics_server

    if _metrics_server is not None and _metrics_server.is_running:
        raise RuntimeError("Metrics server is already running")

    _metrics_server = MetricsServer(port=port, registry=registry, path=path)
    await _metrics_server.start()
    return _metrics_server


async def stop_metrics_server() -> None:
    """Stop the currently running metrics server.

    This is a convenience function that stops the module-level server instance
    started by start_metrics_server().

    If no server is running, this function does nothing.
    """
    global _metrics_server

    if _metrics_server is not None:
        await _metrics_server.stop()
        _metrics_server = None


def get_metrics_server() -> MetricsServer | None:
    """Get the currently running metrics server instance.

    Returns:
        The MetricsServer instance or None if not running
    """
    return _metrics_server
