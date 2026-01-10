import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

import structlog

from pg_mcp.config.models import RateLimitConfig
from pg_mcp.models.errors import RateLimitExceededError

logger = structlog.get_logger(__name__)


@dataclass
class TokenBucket:
    """令牌桶实现"""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """消费令牌

        Args:
            tokens: 需要消费的令牌数

        Returns:
            是否成功消费
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def available(self) -> int:
        """获取可用令牌数"""
        self._refill()
        return int(self.tokens)


@dataclass
class SlidingWindowCounter:
    """滑动窗口计数器"""
    window_seconds: int
    max_count: int
    timestamps: deque[float] = field(default_factory=deque)

    def _cleanup(self) -> None:
        """清理过期的时间戳"""
        cutoff = time.time() - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def increment(self) -> bool:
        """增加计数

        Returns:
            是否成功（未超过限制）
        """
        self._cleanup()
        if len(self.timestamps) >= self.max_count:
            return False
        self.timestamps.append(time.time())
        return True

    def count(self) -> int:
        """获取当前计数"""
        self._cleanup()
        return len(self.timestamps)

    def remaining(self) -> int:
        """获取剩余配额"""
        return max(0, self.max_count - self.count())

    def reset_time(self) -> float | None:
        """获取下一次重置时间（最早过期时间）"""
        self._cleanup()
        if self.timestamps:
            return self.timestamps[0] + self.window_seconds
        return None


class RateLimiter:
    """速率限制器"""

    def __init__(self, config: RateLimitConfig) -> None:
        """初始化速率限制器

        Args:
            config: 速率限制配置
        """
        self.config = config
        self._enabled = config.enabled

        # 每分钟请求限制
        self._minute_counter = SlidingWindowCounter(
            window_seconds=60,
            max_count=config.requests_per_minute,
        )

        # 每小时请求限制
        self._hour_counter = SlidingWindowCounter(
            window_seconds=3600,
            max_count=config.requests_per_hour,
        )

        # OpenAI token 限制 (令牌桶)
        self._token_bucket = TokenBucket(
            capacity=config.openai_tokens_per_minute,
            refill_rate=config.openai_tokens_per_minute / 60.0,
        )

        self._lock = asyncio.Lock()
        self._logger = logger

    async def check_request(self) -> None:
        """检查请求是否允许

        Raises:
            RateLimitExceededError: 超过速率限制
        """
        if not self._enabled:
            return

        async with self._lock:
            # 检查每分钟限制
            if not self._minute_counter.increment():
                self._logger.warning(
                    "Rate limit exceeded (per minute)",
                    limit=self.config.requests_per_minute,
                )
                raise RateLimitExceededError(
                    limit_type="requests",
                    limit=self.config.requests_per_minute,
                    window="minute",
                )

            # 检查每小时限制
            if not self._hour_counter.increment():
                # 回滚分钟计数
                self._minute_counter.timestamps.pop()
                self._logger.warning(
                    "Rate limit exceeded (per hour)",
                    limit=self.config.requests_per_hour,
                )
                raise RateLimitExceededError(
                    limit_type="requests",
                    limit=self.config.requests_per_hour,
                    window="hour",
                )

    async def check_tokens(self, tokens: int) -> None:
        """检查 token 使用是否允许

        Args:
            tokens: 预计使用的 token 数

        Raises:
            RateLimitExceededError: 超过 token 限制
        """
        if not self._enabled:
            return

        async with self._lock:
            if not self._token_bucket.consume(tokens):
                self._logger.warning(
                    "Token rate limit exceeded",
                    requested=tokens,
                    available=self._token_bucket.available(),
                )
                raise RateLimitExceededError(
                    limit_type="tokens",
                    limit=self.config.openai_tokens_per_minute,
                    window="minute",
                )

    async def record_tokens(self, tokens: int) -> None:
        """记录实际使用的 token 数

        Args:
            tokens: 实际使用的 token 数
        """
        if not self._enabled:
            return

        # token bucket 在 check_tokens 时已经消费了预估值
        # 这里可以记录实际值用于监控
        self._logger.debug("Tokens used", tokens=tokens)

    def get_status(self) -> dict[str, int | float | None]:
        """获取速率限制状态

        Returns:
            状态信息
        """
        return {
            "enabled": self._enabled,
            "requests_per_minute_remaining": self._minute_counter.remaining(),
            "requests_per_hour_remaining": self._hour_counter.remaining(),
            "tokens_available": self._token_bucket.available(),
            "minute_reset_at": self._minute_counter.reset_time(),
            "hour_reset_at": self._hour_counter.reset_time(),
        }

    def reset(self) -> None:
        """重置所有计数器（用于测试）"""
        self._minute_counter = SlidingWindowCounter(
            window_seconds=60,
            max_count=self.config.requests_per_minute,
        )
        self._hour_counter = SlidingWindowCounter(
            window_seconds=3600,
            max_count=self.config.requests_per_hour,
        )
        self._token_bucket = TokenBucket(
            capacity=self.config.openai_tokens_per_minute,
            refill_rate=self.config.openai_tokens_per_minute / 60.0,
        )
        self._logger.info("Rate limiter reset")
