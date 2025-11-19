"""
Performance Profiling Utilities for ZERO Assistant.

This module provides decorators and utilities for measuring and tracking
performance across all components of the assistant.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class TimingStats:
    """Statistics for a timed operation."""

    name: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0

    def record(self, duration: float):
        """Record a new timing measurement."""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'count': self.count,
            'total_ms': round(self.total_time * 1000, 2),
            'avg_ms': round(self.avg_time * 1000, 2),
            'min_ms': round(self.min_time * 1000, 2) if self.min_time != float('inf') else 0,
            'max_ms': round(self.max_time * 1000, 2),
        }


class PerformanceProfiler:
    """
    Global performance profiler for tracking timing across components.

    Singleton pattern - use get_profiler() to access.
    """

    _instance: Optional['PerformanceProfiler'] = None

    def __init__(self):
        """Initialize profiler."""
        self.stats: Dict[str, TimingStats] = defaultdict(lambda: TimingStats(name="unknown"))
        self.enabled = True
        self._current_request_timings: Dict[str, float] = {}
        logger.info("Performance profiler initialized")

    @classmethod
    def get_instance(cls) -> 'PerformanceProfiler':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_timing(self, name: str, duration: float):
        """
        Record a timing measurement.

        Args:
            name: Operation name
            duration: Duration in seconds
        """
        if not self.enabled:
            return

        if name not in self.stats:
            self.stats[name] = TimingStats(name=name)

        self.stats[name].record(duration)
        logger.debug(f"⏱️  {name}: {duration*1000:.2f}ms")

    @contextmanager
    def measure(self, name: str):
        """
        Context manager for measuring code blocks.

        Usage:
            with profiler.measure("my_operation"):
                # code to measure
                pass
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.record_timing(name, duration)

    def start_request_timing(self):
        """Start timing a new request."""
        self._current_request_timings = {}

    def record_request_step(self, step_name: str, duration: float):
        """Record a step in the current request."""
        self._current_request_timings[step_name] = duration

    def get_request_breakdown(self) -> Dict[str, float]:
        """Get timing breakdown for current request."""
        return self._current_request_timings.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get all performance statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            name: stats.to_dict()
            for name, stats in self.stats.items()
        }

    def get_report(self) -> str:
        """
        Generate a human-readable performance report.

        Returns:
            Formatted report string
        """
        if not self.stats:
            return "No performance data collected yet."

        lines = [
            "=" * 70,
            "PERFORMANCE REPORT",
            "=" * 70,
        ]

        # Sort by total time (descending)
        sorted_stats = sorted(
            self.stats.values(),
            key=lambda s: s.total_time,
            reverse=True
        )

        lines.append(f"{'Operation':<40} {'Calls':<8} {'Avg(ms)':<10} {'Total(ms)':<12}")
        lines.append("-" * 70)

        for stat in sorted_stats:
            lines.append(
                f"{stat.name:<40} "
                f"{stat.count:<8} "
                f"{stat.avg_time*1000:<10.2f} "
                f"{stat.total_time*1000:<12.2f}"
            )

        lines.append("=" * 70)

        # Add summary
        total_calls = sum(s.count for s in self.stats.values())
        total_time = sum(s.total_time for s in self.stats.values())

        lines.append(f"Total Operations: {len(self.stats)}")
        lines.append(f"Total Calls: {total_calls}")
        lines.append(f"Total Time: {total_time*1000:.2f}ms")
        lines.append("=" * 70)

        return "\n".join(lines)

    def reset(self):
        """Reset all statistics."""
        self.stats.clear()
        self._current_request_timings.clear()
        logger.info("Performance statistics reset")

    def enable(self):
        """Enable profiling."""
        self.enabled = True

    def disable(self):
        """Disable profiling."""
        self.enabled = False


# Global profiler instance
_profiler = None


def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler.get_instance()
    return _profiler


def profile_method(name: Optional[str] = None):
    """
    Decorator for profiling methods.

    Usage:
        @profile_method()
        def my_function():
            pass

        @profile_method("custom_name")
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                profiler.record_timing(operation_name, duration)

        return wrapper
    return decorator


def profile_async_method(name: Optional[str] = None):
    """
    Decorator for profiling async methods.

    Usage:
        @profile_async_method()
        async def my_async_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            profiler = get_profiler()
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                profiler.record_timing(operation_name, duration)

        return wrapper
    return decorator


@contextmanager
def measure(name: str):
    """
    Convenience context manager for measuring code blocks.

    Usage:
        from src.core.profiler import measure

        with measure("my_operation"):
            # code to measure
            pass
    """
    profiler = get_profiler()
    with profiler.measure(name):
        yield


class PipelineTimer:
    """
    Timer for tracking multi-step pipeline execution.

    Usage:
        timer = PipelineTimer("request_123")
        timer.start("stt")
        # ... STT processing ...
        timer.end("stt")
        timer.start("intent_classification")
        # ... intent classification ...
        timer.end("intent_classification")

        report = timer.get_report()
    """

    def __init__(self, request_id: str):
        """
        Initialize pipeline timer.

        Args:
            request_id: Unique identifier for this request
        """
        self.request_id = request_id
        self.timings: Dict[str, float] = {}
        self._start_times: Dict[str, float] = {}
        self._total_start = time.perf_counter()

    def start(self, step_name: str):
        """Start timing a step."""
        self._start_times[step_name] = time.perf_counter()

    def end(self, step_name: str) -> float:
        """
        End timing a step.

        Args:
            step_name: Name of the step

        Returns:
            Duration in seconds
        """
        if step_name not in self._start_times:
            logger.warning(f"Step '{step_name}' was not started")
            return 0.0

        duration = time.perf_counter() - self._start_times[step_name]
        self.timings[step_name] = duration
        del self._start_times[step_name]

        # Also record in global profiler
        get_profiler().record_timing(f"pipeline.{step_name}", duration)

        return duration

    def get_total_time(self) -> float:
        """Get total pipeline execution time."""
        return time.perf_counter() - self._total_start

    def get_report(self) -> str:
        """Generate a report of pipeline timings."""
        total = self.get_total_time()

        lines = [
            f"Pipeline Timing Report (Request: {self.request_id})",
            "-" * 60,
        ]

        for step, duration in self.timings.items():
            percentage = (duration / total * 100) if total > 0 else 0
            lines.append(f"  {step:<30} {duration*1000:>8.2f}ms ({percentage:>5.1f}%)")

        # Check for unfinished steps
        if self._start_times:
            lines.append("\nUnfinished steps:")
            for step in self._start_times.keys():
                lines.append(f"  - {step}")

        lines.append("-" * 60)
        lines.append(f"  {'TOTAL':<30} {total*1000:>8.2f}ms")

        return "\n".join(lines)

    def get_breakdown(self) -> Dict[str, float]:
        """Get timing breakdown as dictionary (in milliseconds)."""
        breakdown = {
            step: duration * 1000
            for step, duration in self.timings.items()
        }
        breakdown['total'] = self.get_total_time() * 1000
        return breakdown
