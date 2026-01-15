# src/pg_mcp/observability/tracing.py
"""
OpenTelemetry 追踪管理器

提供分布式追踪功能:
- TracingManager: OpenTelemetry 追踪管理器
- 支持 OTLP, Jaeger, Zipkin 导出器
- 优雅降级：当 opentelemetry 依赖缺失时仅记录警告
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Generator

    from pg_mcp.config.models import TracingConfig


logger = structlog.get_logger()


class TracingManager:
    """
    OpenTelemetry 追踪管理器

    职责:
    - 初始化 OpenTelemetry SDK
    - 提供便捷的 span 创建方法
    - 支持多种导出器 (otlp, jaeger, zipkin)
    - 优雅降级：当 opentelemetry 依赖缺失时仅记录警告
    """

    def __init__(self, config: TracingConfig) -> None:
        """
        初始化追踪管理器

        Args:
            config: 追踪配置
        """
        self.config = config
        self._tracer: Any = None
        self._provider: Any = None

        if config.enabled:
            self._setup_tracing()

    def _setup_tracing(self) -> None:
        """初始化追踪"""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

            # 创建资源
            resource = Resource.create(
                {
                    "service.name": self.config.service_name,
                }
            )

            # 创建采样器
            sampler = TraceIdRatioBased(self.config.sample_rate)

            # 创建 TracerProvider
            self._provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )

            # 配置导出器
            self._setup_exporter(self._provider)

            # 设置全局 TracerProvider
            trace.set_tracer_provider(self._provider)

            # 获取 tracer
            self._tracer = trace.get_tracer(__name__)

            logger.info(
                "tracing_initialized",
                exporter=self.config.exporter,
                sample_rate=self.config.sample_rate,
                service_name=self.config.service_name,
            )

        except ImportError as e:
            logger.warning(
                "tracing_disabled_missing_dependency",
                error=str(e),
                hint="Install opentelemetry-sdk to enable tracing",
            )
            self.config.enabled = False

    def _setup_exporter(self, provider: Any) -> None:
        """
        配置导出器 - 支持 otlp, jaeger, zipkin

        Args:
            provider: TracerProvider 实例
        """
        exporter_type = self.config.exporter.lower()

        try:
            if exporter_type == "otlp":
                self._setup_otlp_exporter(provider)
            elif exporter_type == "jaeger":
                self._setup_jaeger_exporter(provider)
            elif exporter_type == "zipkin":
                self._setup_zipkin_exporter(provider)
            else:
                logger.warning(
                    "unknown_exporter_type",
                    exporter=exporter_type,
                    fallback="otlp",
                )
                self._setup_otlp_exporter(provider)
        except ImportError as e:
            logger.warning(
                "exporter_setup_failed",
                exporter=exporter_type,
                error=str(e),
                hint=f"Install opentelemetry-exporter-{exporter_type}",
            )

    def _setup_otlp_exporter(self, provider: Any) -> None:
        """配置 OTLP 导出器"""
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter_kwargs: dict[str, Any] = {}
        if self.config.endpoint:
            exporter_kwargs["endpoint"] = self.config.endpoint

        exporter = OTLPSpanExporter(**exporter_kwargs)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        logger.debug(
            "otlp_exporter_configured",
            endpoint=self.config.endpoint or "default",
        )

    def _setup_jaeger_exporter(self, provider: Any) -> None:
        """配置 Jaeger 导出器"""
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter_kwargs: dict[str, Any] = {}
        if self.config.endpoint:
            # Jaeger expects host:port format, parse endpoint
            endpoint = self.config.endpoint
            if endpoint.startswith(("http://", "https://")):
                # Extract host:port from URL
                from urllib.parse import urlparse

                parsed = urlparse(endpoint)
                exporter_kwargs["agent_host_name"] = parsed.hostname or "localhost"
                exporter_kwargs["agent_port"] = parsed.port or 6831
            else:
                # Assume host:port format
                parts = endpoint.split(":")
                exporter_kwargs["agent_host_name"] = parts[0]
                if len(parts) > 1:
                    exporter_kwargs["agent_port"] = int(parts[1])

        exporter = JaegerExporter(**exporter_kwargs)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        logger.debug(
            "jaeger_exporter_configured",
            endpoint=self.config.endpoint or "localhost:6831",
        )

    def _setup_zipkin_exporter(self, provider: Any) -> None:
        """配置 Zipkin 导出器"""
        from opentelemetry.exporter.zipkin.json import ZipkinExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter_kwargs: dict[str, Any] = {}
        if self.config.endpoint:
            exporter_kwargs["endpoint"] = self.config.endpoint

        exporter = ZipkinExporter(**exporter_kwargs)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        logger.debug(
            "zipkin_exporter_configured",
            endpoint=self.config.endpoint or "http://localhost:9411/api/v2/spans",
        )

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Any]:
        """
        创建追踪 span

        Args:
            name: span 名称
            attributes: span 属性

        Yields:
            span 对象，如果追踪未启用则为 None
        """
        if not self.config.enabled or self._tracer is None:
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    # 转换值为 OpenTelemetry 支持的类型
                    span.set_attribute(key, self._convert_attribute_value(value))
            yield span

    def _convert_attribute_value(self, value: Any) -> str | int | float | bool:
        """
        转换属性值为 OpenTelemetry 支持的类型

        Args:
            value: 原始值

        Returns:
            转换后的值
        """
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    def get_current_trace_id(self) -> str | None:
        """
        获取当前 trace ID

        Returns:
            32 字符的十六进制字符串，如果无活动 trace 则返回 None
        """
        if not self.config.enabled:
            return None

        try:
            from opentelemetry import trace

            current_span = trace.get_current_span()
            span_context = current_span.get_span_context()

            if span_context.is_valid:
                # 转换为 32 字符十六进制字符串
                return format(span_context.trace_id, "032x")

            return None

        except ImportError:
            return None

    def shutdown(self) -> None:
        """关闭追踪管理器，刷新并导出所有待处理的 span"""
        if self._provider is not None:
            try:
                self._provider.shutdown()
                logger.info("tracing_shutdown")
            except Exception as e:
                logger.warning("tracing_shutdown_error", error=str(e))


# 全局 TracingManager 实例
_tracing_manager: TracingManager | None = None


def init_tracing(config: TracingConfig) -> TracingManager:
    """
    初始化全局追踪管理器

    Args:
        config: 追踪配置

    Returns:
        TracingManager 实例
    """
    global _tracing_manager
    _tracing_manager = TracingManager(config)
    return _tracing_manager


def get_tracing_manager() -> TracingManager | None:
    """
    获取全局追踪管理器

    Returns:
        TracingManager 实例，如果未初始化则返回 None
    """
    return _tracing_manager


def shutdown_tracing() -> None:
    """关闭全局追踪管理器"""
    global _tracing_manager
    if _tracing_manager is not None:
        _tracing_manager.shutdown()
        _tracing_manager = None
