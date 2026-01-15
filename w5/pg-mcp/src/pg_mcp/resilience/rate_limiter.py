# src/pg_mcp/resilience/rate_limiter.py
"""
速率限制器实现

提供多层次的速率限制功能：
- 全局请求限制（每分钟/每小时）
- 单客户端请求限制
- Token 消耗限制
- 多种限制策略（拒绝/排队/延迟）
"""

import time
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class RateLimitStrategy(str, Enum):
    """速率限制策略"""
    REJECT = "reject"   # 直接拒绝
    QUEUE = "queue"     # 排队等待
    DELAY = "delay"     # 延迟响应


class ClientIdentifier(str, Enum):
    """客户端标识方式"""
    IP = "ip"           # 使用 IP（仅 SSE 模式）
    SESSION = "session"  # 使用 session_id
    AUTO = "auto"       # 自动选择


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    enabled: bool = True

    # 全局限制
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # 单客户端限制
    per_client_per_minute: int = 20
    client_identifier: ClientIdentifier = ClientIdentifier.AUTO

    # Token 限制
    tokens_per_minute: int = 100000
    tokens_per_hour: int = 1000000

    # 策略
    strategy: RateLimitStrategy = RateLimitStrategy.REJECT
    max_queue_wait: float = 30.0
    include_headers: bool = True


@dataclass
class RateLimitResult:
    """速率限制检查结果"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # Unix timestamp
    retry_after: float | None = None  # 秒


@dataclass
class RateLimitBucket:
    """速率限制桶"""
    count: int = 0
    reset_at: float = 0.0

    def check_and_increment(
        self,
        limit: int,
        window_seconds: float
    ) -> tuple[bool, int, float]:
        """
        检查并增加计数

        Args:
            limit: 限制值
            window_seconds: 时间窗口（秒）

        Returns:
            (是否允许, 剩余配额, 重置时间)
        """
        now = time.time()

        # 检查是否需要重置
        if now >= self.reset_at:
            self.count = 0
            self.reset_at = now + window_seconds

        # 检查是否超限
        if self.count >= limit:
            return False, 0, self.reset_at

        # 增加计数
        self.count += 1
        return True, limit - self.count, self.reset_at


class RateLimiter:
    """
    速率限制器

    职责:
    - 在请求处理前检查速率限制
    - 在请求处理后记录 Token 消耗
    - 支持全局和单客户端限制
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config

        # 全局桶
        self._global_minute_bucket = RateLimitBucket()
        self._global_hour_bucket = RateLimitBucket()

        # Token 桶
        self._token_minute_bucket = RateLimitBucket()
        self._token_hour_bucket = RateLimitBucket()

        # 客户端桶
        self._client_buckets: dict[str, RateLimitBucket] = {}

        self._logger = logger.bind(component="rate_limiter")

    def _get_client_key(
        self,
        client_ip: str | None,
        session_id: str | None
    ) -> str:
        """获取客户端标识键"""
        if self.config.client_identifier == ClientIdentifier.IP:
            return f"ip:{client_ip or 'unknown'}"
        elif self.config.client_identifier == ClientIdentifier.SESSION:
            return f"session:{session_id or 'unknown'}"
        else:  # AUTO
            # SSE 模式优先使用 IP，否则使用 session
            if client_ip:
                return f"ip:{client_ip}"
            return f"session:{session_id or 'unknown'}"

    def check_request(
        self,
        client_ip: str | None = None,
        session_id: str | None = None
    ) -> RateLimitResult:
        """
        检查请求是否被允许

        Args:
            client_ip: 客户端 IP（SSE 模式）
            session_id: 会话 ID

        Returns:
            RateLimitResult
        """
        if not self.config.enabled:
            return RateLimitResult(
                allowed=True,
                limit=self.config.requests_per_minute,
                remaining=self.config.requests_per_minute,
                reset_at=time.time() + 60
            )

        # 检查全局限制（每分钟）
        allowed, remaining, reset_at = self._global_minute_bucket.check_and_increment(
            self.config.requests_per_minute,
            60.0
        )
        if not allowed:
            self._logger.warning(
                "Global rate limit exceeded (per minute)",
                limit=self.config.requests_per_minute,
                reset_at=reset_at
            )
            return RateLimitResult(
                allowed=False,
                limit=self.config.requests_per_minute,
                remaining=0,
                reset_at=reset_at,
                retry_after=reset_at - time.time()
            )

        # 检查全局限制（每小时）
        allowed, _, _ = self._global_hour_bucket.check_and_increment(
            self.config.requests_per_hour,
            3600.0
        )
        if not allowed:
            self._logger.warning(
                "Global rate limit exceeded (per hour)",
                limit=self.config.requests_per_hour,
                reset_at=self._global_hour_bucket.reset_at
            )
            return RateLimitResult(
                allowed=False,
                limit=self.config.requests_per_hour,
                remaining=0,
                reset_at=self._global_hour_bucket.reset_at,
                retry_after=self._global_hour_bucket.reset_at - time.time()
            )

        # 检查单客户端限制
        client_key = self._get_client_key(client_ip, session_id)
        if client_key not in self._client_buckets:
            self._client_buckets[client_key] = RateLimitBucket()

        client_bucket = self._client_buckets[client_key]
        allowed, client_remaining, client_reset = client_bucket.check_and_increment(
            self.config.per_client_per_minute,
            60.0
        )
        if not allowed:
            self._logger.warning(
                "Client rate limit exceeded",
                client_key=client_key,
                limit=self.config.per_client_per_minute,
                reset_at=client_reset
            )
            return RateLimitResult(
                allowed=False,
                limit=self.config.per_client_per_minute,
                remaining=0,
                reset_at=client_reset,
                retry_after=client_reset - time.time()
            )

        return RateLimitResult(
            allowed=True,
            limit=self.config.requests_per_minute,
            remaining=remaining,
            reset_at=reset_at
        )

    def record_tokens(self, tokens_used: int) -> RateLimitResult:
        """
        记录 Token 消耗

        Args:
            tokens_used: 消耗的 Token 数量

        Returns:
            RateLimitResult
        """
        if not self.config.enabled:
            return RateLimitResult(
                allowed=True,
                limit=self.config.tokens_per_minute,
                remaining=self.config.tokens_per_minute,
                reset_at=time.time() + 60
            )

        # 更新 Token 计数（每分钟）
        now = time.time()
        if now >= self._token_minute_bucket.reset_at:
            self._token_minute_bucket.count = 0
            self._token_minute_bucket.reset_at = now + 60
        self._token_minute_bucket.count += tokens_used

        # 更新 Token 计数（每小时）
        if now >= self._token_hour_bucket.reset_at:
            self._token_hour_bucket.count = 0
            self._token_hour_bucket.reset_at = now + 3600
        self._token_hour_bucket.count += tokens_used

        # 检查是否超限
        minute_remaining = max(
            0,
            self.config.tokens_per_minute - self._token_minute_bucket.count
        )

        if minute_remaining == 0:
            self._logger.warning(
                "Token rate limit reached",
                tokens_used=tokens_used,
                limit=self.config.tokens_per_minute,
                reset_at=self._token_minute_bucket.reset_at
            )

        return RateLimitResult(
            allowed=minute_remaining > 0,
            limit=self.config.tokens_per_minute,
            remaining=minute_remaining,
            reset_at=self._token_minute_bucket.reset_at
        )

    def get_headers(self) -> dict[str, str]:
        """获取速率限制响应头"""
        if not self.config.include_headers:
            return {}

        return {
            "X-RateLimit-Limit": str(self.config.requests_per_minute),
            "X-RateLimit-Remaining": str(
                max(0, self.config.requests_per_minute - self._global_minute_bucket.count)
            ),
            "X-RateLimit-Reset": str(int(self._global_minute_bucket.reset_at))
        }

    def cleanup_stale_buckets(self, max_age: float = 3600.0) -> int:
        """
        清理过期的客户端桶

        Args:
            max_age: 最大保留时间（秒）

        Returns:
            清理的桶数量
        """
        now = time.time()
        stale_keys = [
            key for key, bucket in self._client_buckets.items()
            if now - bucket.reset_at > max_age
        ]
        for key in stale_keys:
            del self._client_buckets[key]

        if stale_keys:
            self._logger.debug(
                "Cleaned up stale client buckets",
                count=len(stale_keys)
            )

        return len(stale_keys)

    def get_status(self) -> dict[str, int | float | bool]:
        """
        获取速率限制器状态

        Returns:
            状态信息字典
        """
        return {
            "enabled": self.config.enabled,
            "global_minute_count": self._global_minute_bucket.count,
            "global_minute_remaining": max(
                0, self.config.requests_per_minute - self._global_minute_bucket.count
            ),
            "global_minute_reset_at": self._global_minute_bucket.reset_at,
            "global_hour_count": self._global_hour_bucket.count,
            "global_hour_remaining": max(
                0, self.config.requests_per_hour - self._global_hour_bucket.count
            ),
            "global_hour_reset_at": self._global_hour_bucket.reset_at,
            "token_minute_count": self._token_minute_bucket.count,
            "token_minute_remaining": max(
                0, self.config.tokens_per_minute - self._token_minute_bucket.count
            ),
            "token_hour_count": self._token_hour_bucket.count,
            "token_hour_remaining": max(
                0, self.config.tokens_per_hour - self._token_hour_bucket.count
            ),
            "client_buckets_count": len(self._client_buckets),
        }

    def reset(self) -> None:
        """重置所有计数器（用于测试）"""
        self._global_minute_bucket = RateLimitBucket()
        self._global_hour_bucket = RateLimitBucket()
        self._token_minute_bucket = RateLimitBucket()
        self._token_hour_bucket = RateLimitBucket()
        self._client_buckets.clear()
        self._logger.info("Rate limiter reset")
