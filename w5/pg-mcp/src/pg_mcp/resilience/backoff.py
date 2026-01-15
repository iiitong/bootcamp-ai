# src/pg_mcp/resilience/backoff.py
"""
退避策略实现

提供多种退避策略用于重试机制：
- ExponentialBackoff: 指数退避（推荐用于网络请求）
- FixedBackoff: 固定间隔退避
- FibonacciBackoff: 斐波那契退避
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BackoffStrategyType(str, Enum):
    """退避策略类型"""
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class BackoffStrategy(ABC):
    """退避策略接口"""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        计算第 N 次重试前的等待时间

        Args:
            attempt: 重试次数（从 1 开始）

        Returns:
            等待时间（秒）
        """
        pass


@dataclass
class ExponentialBackoff(BackoffStrategy):
    """
    指数退避策略

    delay = min(initial_delay * (multiplier ^ attempt) + jitter, max_delay)
    """
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True  # 添加随机抖动

    def get_delay(self, attempt: int) -> float:
        delay = self.initial_delay * (self.multiplier ** attempt)

        if self.jitter:
            # 添加 ±25% 随机抖动
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return min(delay, self.max_delay)


@dataclass
class FixedBackoff(BackoffStrategy):
    """固定间隔退避策略"""
    delay: float = 1.0

    def get_delay(self, attempt: int) -> float:
        return self.delay


@dataclass
class FibonacciBackoff(BackoffStrategy):
    """
    斐波那契退避策略

    delay = fib(attempt) * base_delay
    """
    base_delay: float = 1.0
    max_delay: float = 30.0

    def get_delay(self, attempt: int) -> float:
        # 计算斐波那契数
        a, b = 1, 1
        for _ in range(attempt - 1):
            a, b = b, a + b

        delay = a * self.base_delay
        return min(delay, self.max_delay)


def create_backoff_strategy(
    strategy_type: BackoffStrategyType,
    **kwargs
) -> BackoffStrategy:
    """工厂方法：创建退避策略"""
    if strategy_type == BackoffStrategyType.EXPONENTIAL:
        return ExponentialBackoff(**kwargs)
    elif strategy_type == BackoffStrategyType.FIXED:
        return FixedBackoff(**kwargs)
    elif strategy_type == BackoffStrategyType.FIBONACCI:
        return FibonacciBackoff(**kwargs)
    else:
        raise ValueError(f"Unknown backoff strategy: {strategy_type}")
