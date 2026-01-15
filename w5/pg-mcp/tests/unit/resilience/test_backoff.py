"""Unit tests for backoff strategies module."""

import random
from unittest.mock import patch

import pytest

from pg_mcp.resilience.backoff import (
    BackoffStrategy,
    BackoffStrategyType,
    ExponentialBackoff,
    FibonacciBackoff,
    FixedBackoff,
    create_backoff_strategy,
)


class TestExponentialBackoff:
    """Tests for ExponentialBackoff strategy."""

    def test_exponential_delay_progression(self) -> None:
        """Test that delay increases exponentially with attempts."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=2.0,
            jitter=False,
        )

        # Expected: 1 * 2^1 = 2, 1 * 2^2 = 4, 1 * 2^3 = 8, 1 * 2^4 = 16
        assert backoff.get_delay(1) == 2.0
        assert backoff.get_delay(2) == 4.0
        assert backoff.get_delay(3) == 8.0
        assert backoff.get_delay(4) == 16.0

    def test_exponential_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=10.0,
            multiplier=2.0,
            jitter=False,
        )

        # 1 * 2^5 = 32, but should be capped at 10
        assert backoff.get_delay(5) == 10.0
        # Even higher attempts should still be capped
        assert backoff.get_delay(10) == 10.0
        assert backoff.get_delay(100) == 10.0

    def test_exponential_jitter_range(self) -> None:
        """Test that jitter is within reasonable range (+-25%)."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=2.0,
            jitter=True,
        )

        # For attempt 2: base delay = 1 * 2^2 = 4
        # With jitter: 4 +/- 25% = [3, 5]
        base_delay = 4.0
        min_expected = base_delay * 0.75
        max_expected = base_delay * 1.25

        # Run multiple times to verify jitter range
        delays = [backoff.get_delay(2) for _ in range(100)]

        for delay in delays:
            assert min_expected <= delay <= max_expected, (
                f"Delay {delay} not in range [{min_expected}, {max_expected}]"
            )

        # Verify there's actual variance (not all the same)
        unique_delays = len(set(delays))
        assert unique_delays > 1, "Jitter should produce varying delays"

    def test_exponential_no_jitter(self) -> None:
        """Test that disabling jitter produces consistent delays."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=2.0,
            jitter=False,
        )

        # Should always return exactly the same value
        delays = [backoff.get_delay(3) for _ in range(10)]
        assert all(d == 8.0 for d in delays)

    def test_exponential_custom_multiplier(self) -> None:
        """Test exponential backoff with custom multiplier."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=3.0,
            jitter=False,
        )

        # 1 * 3^1 = 3, 1 * 3^2 = 9, 1 * 3^3 = 27
        assert backoff.get_delay(1) == 3.0
        assert backoff.get_delay(2) == 9.0
        assert backoff.get_delay(3) == 27.0

    def test_exponential_default_values(self) -> None:
        """Test exponential backoff with default values."""
        backoff = ExponentialBackoff()
        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 30.0
        assert backoff.multiplier == 2.0
        assert backoff.jitter is True

    def test_exponential_first_attempt(self) -> None:
        """Test delay for first attempt."""
        backoff = ExponentialBackoff(
            initial_delay=0.5,
            multiplier=2.0,
            jitter=False,
        )
        # 0.5 * 2^1 = 1.0
        assert backoff.get_delay(1) == 1.0


class TestFixedBackoff:
    """Tests for FixedBackoff strategy."""

    def test_fixed_constant_delay(self) -> None:
        """Test that delay is constant."""
        backoff = FixedBackoff(delay=5.0)

        assert backoff.get_delay(1) == 5.0
        assert backoff.get_delay(2) == 5.0
        assert backoff.get_delay(3) == 5.0

    def test_fixed_different_attempts(self) -> None:
        """Test that different attempt numbers return same delay."""
        backoff = FixedBackoff(delay=2.5)

        delays = [backoff.get_delay(i) for i in range(1, 101)]
        assert all(d == 2.5 for d in delays)

    def test_fixed_default_delay(self) -> None:
        """Test default delay value."""
        backoff = FixedBackoff()
        assert backoff.delay == 1.0
        assert backoff.get_delay(1) == 1.0

    def test_fixed_zero_delay(self) -> None:
        """Test fixed backoff with zero delay."""
        backoff = FixedBackoff(delay=0.0)
        assert backoff.get_delay(1) == 0.0
        assert backoff.get_delay(5) == 0.0

    def test_fixed_fractional_delay(self) -> None:
        """Test fixed backoff with fractional delay."""
        backoff = FixedBackoff(delay=0.1)
        assert backoff.get_delay(1) == 0.1
        assert backoff.get_delay(10) == 0.1


class TestFibonacciBackoff:
    """Tests for FibonacciBackoff strategy."""

    def test_fibonacci_progression(self) -> None:
        """Test that delay follows Fibonacci sequence."""
        backoff = FibonacciBackoff(base_delay=1.0, max_delay=100.0)

        # Fibonacci: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55...
        # For attempt n, we get fib(n) * base_delay
        # The implementation starts with (1,1) and iterates attempt-1 times
        # attempt 1: fib(1) = 1
        # attempt 2: fib(2) = 1
        # attempt 3: fib(3) = 2
        # attempt 4: fib(4) = 3
        # attempt 5: fib(5) = 5
        assert backoff.get_delay(1) == 1.0
        assert backoff.get_delay(2) == 1.0
        assert backoff.get_delay(3) == 2.0
        assert backoff.get_delay(4) == 3.0
        assert backoff.get_delay(5) == 5.0
        assert backoff.get_delay(6) == 8.0
        assert backoff.get_delay(7) == 13.0

    def test_fibonacci_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        backoff = FibonacciBackoff(base_delay=1.0, max_delay=10.0)

        # fib(8) = 21, fib(9) = 34, but should be capped at 10
        assert backoff.get_delay(8) == 10.0
        assert backoff.get_delay(9) == 10.0
        assert backoff.get_delay(20) == 10.0

    def test_fibonacci_custom_base_delay(self) -> None:
        """Test Fibonacci backoff with custom base delay."""
        backoff = FibonacciBackoff(base_delay=2.0, max_delay=100.0)

        # 2 * fib(n)
        assert backoff.get_delay(1) == 2.0
        assert backoff.get_delay(2) == 2.0
        assert backoff.get_delay(3) == 4.0
        assert backoff.get_delay(4) == 6.0
        assert backoff.get_delay(5) == 10.0

    def test_fibonacci_default_values(self) -> None:
        """Test Fibonacci backoff with default values."""
        backoff = FibonacciBackoff()
        assert backoff.base_delay == 1.0
        assert backoff.max_delay == 30.0

    def test_fibonacci_large_attempt(self) -> None:
        """Test Fibonacci for larger attempt numbers (should hit max)."""
        backoff = FibonacciBackoff(base_delay=0.5, max_delay=50.0)

        # fib(15) = 610, so 0.5 * 610 = 305, should be capped at 50
        assert backoff.get_delay(15) == 50.0


class TestCreateBackoffStrategy:
    """Tests for create_backoff_strategy factory function."""

    def test_create_exponential_strategy(self) -> None:
        """Test creating exponential strategy."""
        strategy = create_backoff_strategy(BackoffStrategyType.EXPONENTIAL)
        assert isinstance(strategy, ExponentialBackoff)
        assert isinstance(strategy, BackoffStrategy)

    def test_create_exponential_strategy_with_kwargs(self) -> None:
        """Test creating exponential strategy with custom parameters."""
        strategy = create_backoff_strategy(
            BackoffStrategyType.EXPONENTIAL,
            initial_delay=2.0,
            max_delay=60.0,
            multiplier=3.0,
            jitter=False,
        )
        assert isinstance(strategy, ExponentialBackoff)
        assert strategy.initial_delay == 2.0
        assert strategy.max_delay == 60.0
        assert strategy.multiplier == 3.0
        assert strategy.jitter is False

    def test_create_fixed_strategy(self) -> None:
        """Test creating fixed strategy."""
        strategy = create_backoff_strategy(BackoffStrategyType.FIXED)
        assert isinstance(strategy, FixedBackoff)
        assert isinstance(strategy, BackoffStrategy)

    def test_create_fixed_strategy_with_kwargs(self) -> None:
        """Test creating fixed strategy with custom delay."""
        strategy = create_backoff_strategy(
            BackoffStrategyType.FIXED,
            delay=5.0,
        )
        assert isinstance(strategy, FixedBackoff)
        assert strategy.delay == 5.0

    def test_create_fibonacci_strategy(self) -> None:
        """Test creating Fibonacci strategy."""
        strategy = create_backoff_strategy(BackoffStrategyType.FIBONACCI)
        assert isinstance(strategy, FibonacciBackoff)
        assert isinstance(strategy, BackoffStrategy)

    def test_create_fibonacci_strategy_with_kwargs(self) -> None:
        """Test creating Fibonacci strategy with custom parameters."""
        strategy = create_backoff_strategy(
            BackoffStrategyType.FIBONACCI,
            base_delay=0.5,
            max_delay=20.0,
        )
        assert isinstance(strategy, FibonacciBackoff)
        assert strategy.base_delay == 0.5
        assert strategy.max_delay == 20.0

    def test_create_invalid_strategy(self) -> None:
        """Test that invalid strategy type raises ValueError."""
        # Test with an invalid string value that's not in the enum
        with pytest.raises(ValueError) as exc_info:
            # We need to simulate an invalid strategy type
            # Since BackoffStrategyType is an enum, we'll mock an invalid case
            create_backoff_strategy("invalid_strategy")  # type: ignore

        assert "Unknown backoff strategy" in str(exc_info.value)


class TestBackoffStrategyInterface:
    """Tests for BackoffStrategy interface compliance."""

    @pytest.mark.parametrize("strategy_class,kwargs", [
        (ExponentialBackoff, {"jitter": False}),
        (FixedBackoff, {}),
        (FibonacciBackoff, {}),
    ])
    def test_strategy_implements_interface(
        self,
        strategy_class: type[BackoffStrategy],
        kwargs: dict,
    ) -> None:
        """Test that all strategies implement the BackoffStrategy interface."""
        strategy = strategy_class(**kwargs)
        assert isinstance(strategy, BackoffStrategy)
        assert hasattr(strategy, "get_delay")
        assert callable(strategy.get_delay)

        # Should return a float
        delay = strategy.get_delay(1)
        assert isinstance(delay, float)
        assert delay >= 0

    @pytest.mark.parametrize("strategy_class,kwargs", [
        (ExponentialBackoff, {"jitter": False}),
        (FixedBackoff, {}),
        (FibonacciBackoff, {}),
    ])
    def test_strategy_returns_non_negative(
        self,
        strategy_class: type[BackoffStrategy],
        kwargs: dict,
    ) -> None:
        """Test that all strategies return non-negative delays."""
        strategy = strategy_class(**kwargs)

        for attempt in range(1, 20):
            delay = strategy.get_delay(attempt)
            assert delay >= 0, f"Delay for attempt {attempt} should be non-negative"


class TestBackoffEdgeCases:
    """Tests for edge cases in backoff strategies."""

    def test_exponential_very_large_attempt(self) -> None:
        """Test exponential backoff with very large attempt number."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=30.0,
            jitter=False,
        )
        # Should be capped at max_delay, not overflow
        delay = backoff.get_delay(1000)
        assert delay == 30.0

    def test_fibonacci_very_large_attempt(self) -> None:
        """Test Fibonacci backoff with very large attempt number."""
        backoff = FibonacciBackoff(base_delay=1.0, max_delay=30.0)
        # Should be capped at max_delay, not overflow
        delay = backoff.get_delay(100)
        assert delay == 30.0

    def test_exponential_jitter_deterministic_with_seed(self) -> None:
        """Test that jitter is deterministic when random is seeded."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=2.0,
            jitter=True,
        )

        random.seed(42)
        delay1 = backoff.get_delay(3)

        random.seed(42)
        delay2 = backoff.get_delay(3)

        assert delay1 == delay2

    def test_all_strategies_callable_multiple_times(self) -> None:
        """Test that strategies can be called multiple times."""
        strategies = [
            ExponentialBackoff(jitter=False),
            FixedBackoff(),
            FibonacciBackoff(),
        ]

        for strategy in strategies:
            delays = [strategy.get_delay(i) for i in range(1, 10)]
            assert len(delays) == 9
            assert all(d >= 0 for d in delays)
