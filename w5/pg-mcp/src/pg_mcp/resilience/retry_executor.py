# src/pg_mcp/resilience/retry_executor.py
"""
重试执行器实现

提供带重试功能的异步执行器：
- RetryExecutor: 通用重试执行器
- OpenAIRetryExecutor: OpenAI API 专用重试执行器
- DatabaseRetryExecutor: 数据库操作专用重试执行器
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

import structlog

from pg_mcp.resilience.backoff import (
    BackoffStrategy,
    BackoffStrategyType,
    create_backoff_strategy,
)

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    retryable_errors: set[str] = field(default_factory=lambda: {
        "rate_limit",
        "timeout",
        "server_error",
        "connection_lost"
    })


@dataclass
class OpenAIRetryConfig(RetryConfig):
    """OpenAI API 重试配置"""
    max_retries: int = 3
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 30.0
    retryable_errors: set[str] = field(default_factory=lambda: {
        "rate_limit",
        "timeout",
        "server_error"
    })


@dataclass
class DatabaseRetryConfig(RetryConfig):
    """数据库操作重试配置"""
    max_retries: int = 2
    backoff_strategy: BackoffStrategyType = BackoffStrategyType.FIXED
    initial_delay: float = 0.5
    retryable_errors: set[str] = field(default_factory=lambda: {
        "connection_lost",
        "timeout"
    })


class RetryExecutor:
    """
    带重试的执行器

    职责:
    - 执行操作，失败时按策略重试
    - 支持自定义可重试错误判断
    - 记录重试日志
    """

    def __init__(self, config: RetryConfig):
        self.config = config
        self.backoff: BackoffStrategy = self._create_backoff(config)

    def _create_backoff(self, config: RetryConfig) -> BackoffStrategy:
        """Create backoff strategy based on config."""
        strategy_type = config.backoff_strategy

        if strategy_type == BackoffStrategyType.EXPONENTIAL:
            return create_backoff_strategy(
                strategy_type,
                initial_delay=config.initial_delay,
                max_delay=config.max_delay,
                multiplier=config.multiplier,
            )
        elif strategy_type == BackoffStrategyType.FIXED:
            # FixedBackoff only accepts 'delay' parameter
            return create_backoff_strategy(
                strategy_type,
                delay=config.initial_delay,
            )
        elif strategy_type == BackoffStrategyType.FIBONACCI:
            return create_backoff_strategy(
                strategy_type,
                base_delay=config.initial_delay,
                max_delay=config.max_delay,
            )
        else:
            raise ValueError(f"Unknown backoff strategy: {strategy_type}")

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
        is_retryable: Callable[[Exception], bool] | None = None
    ) -> T:
        """
        执行操作，失败时按策略重试

        Args:
            operation: 要执行的异步操作
            operation_name: 操作名称（用于日志）
            is_retryable: 自定义的可重试判断函数

        Returns:
            操作结果

        Raises:
            最后一次失败的异常
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_retries + 2):  # +1 for initial try
            try:
                return await operation()
            except Exception as e:
                last_exception = e

                # 判断是否可重试
                retryable = is_retryable(e) if is_retryable else self._is_default_retryable(e)

                if not retryable or attempt > self.config.max_retries:
                    logger.warning(
                        "operation_failed_not_retryable",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                        retryable=retryable
                    )
                    raise

                # 计算等待时间
                delay = self.backoff.get_delay(attempt)

                logger.info(
                    "operation_retry",
                    operation=operation_name,
                    attempt=attempt,
                    delay=delay,
                    error=str(e)
                )

                await asyncio.sleep(delay)

        # 不应该到达这里
        raise last_exception  # type: ignore

    def _is_default_retryable(self, error: Exception) -> bool:
        """默认的可重试判断"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        for retryable in self.config.retryable_errors:
            if retryable in error_str or retryable in error_type:
                return True

        return False


class OpenAIRetryExecutor(RetryExecutor):
    """OpenAI API 专用重试执行器"""

    def __init__(self, config: OpenAIRetryConfig | None = None):
        super().__init__(config or OpenAIRetryConfig())

    def _is_default_retryable(self, error: Exception) -> bool:
        """OpenAI 特定的可重试判断"""
        # 检查 OpenAI SDK 特定错误类型
        error_type = type(error).__name__

        # RateLimitError, APITimeoutError, InternalServerError 可重试
        if error_type in ("RateLimitError", "APITimeoutError", "InternalServerError"):
            return True

        # AuthenticationError, InvalidRequestError 不可重试
        if error_type in ("AuthenticationError", "InvalidRequestError"):
            return False

        return super()._is_default_retryable(error)


class DatabaseRetryExecutor(RetryExecutor):
    """数据库操作专用重试执行器"""

    def __init__(self, config: DatabaseRetryConfig | None = None):
        super().__init__(config or DatabaseRetryConfig())

    def _is_default_retryable(self, error: Exception) -> bool:
        """数据库特定的可重试判断"""
        error_type = type(error).__name__
        error_str = str(error).lower()

        # 连接丢失可重试
        if "connection" in error_str and ("lost" in error_str or "closed" in error_str):
            return True

        # 超时可重试
        if "timeout" in error_str or "TimeoutError" in error_type:
            return True

        # 语法错误不可重试
        if "syntax" in error_str or "SyntaxError" in error_type:
            return False

        return super()._is_default_retryable(error)
