"""Enhanced metrics tracking for repository operations."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading
import psutil
import gc
from .metrics_config import RepositoryMetricsConfig


class RepositoryMetrics:
    """Thread-safe metrics tracking for repository operations."""

    def __init__(self, config: RepositoryMetricsConfig):
        self.config = config
        self._lock = threading.Lock()
        self._operation_count: int = 0
        self._error_count: int = 0
        self._slow_query_count: int = 0
        self._last_operation_time: Optional[datetime] = None
        self._avg_operation_time: float = 0.0
        self._memory_samples: Dict[datetime, float] = {}
        self._last_memory_check: Optional[datetime] = None

    def record_operation(self, duration_ms: float, error: bool = False) -> None:
        """Record metrics for a repository operation in a thread-safe manner."""
        if not self.config.enabled:
            return

        with self._lock:
            profile = self.config.profile

            if profile.enable_operation_counting:
                self._operation_count += 1

            if profile.enable_error_tracking and error:
                self._error_count += 1

            if profile.enable_timing_stats:
                self._last_operation_time = datetime.now()
                is_slow = (
                    duration_ms > profile.slow_query_threshold.total_seconds() * 1000
                )
                if is_slow:
                    self._slow_query_count += 1
                # Update running average
                self._avg_operation_time = (
                    self._avg_operation_time * (self._operation_count - 1) + duration_ms
                ) / self._operation_count

            if (
                profile.enable_memory_tracking
                and self._operation_count % profile.memory_sample_rate == 0
            ):
                self._sample_memory_usage()

    def _sample_memory_usage(self) -> None:
        """Sample current memory usage."""
        now = datetime.now()
        process = psutil.Process()
        memory_info = process.memory_info()

        # Store memory usage in MB
        memory_usage = memory_info.rss / (1024 * 1024)

        # Keep only last hour of samples
        one_hour_ago = now - timedelta(hours=1)
        self._memory_samples = {
            ts: usage for ts, usage in self._memory_samples.items() if ts > one_hour_ago
        }
        self._memory_samples[now] = memory_usage
        self._last_memory_check = now

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics in a thread-safe manner."""
        with self._lock:
            metrics = {}
            profile = self.config.profile

            if profile.enable_operation_counting:
                metrics.update(
                    {
                        "operation_count": self._operation_count,
                    }
                )

            if profile.enable_error_tracking:
                metrics.update(
                    {
                        "error_count": self._error_count,
                        "error_rate": (
                            self._error_count / self._operation_count
                            if self._operation_count > 0
                            else 0
                        ),
                    }
                )

            if profile.enable_timing_stats:
                metrics.update(
                    {
                        "avg_operation_time_ms": self._avg_operation_time,
                        "slow_query_count": self._slow_query_count,
                        "last_operation_time": self._last_operation_time,
                    }
                )

            if profile.enable_memory_tracking:
                metrics.update(
                    {
                        "current_memory_mb": next(
                            iter(self._memory_samples.values()), 0
                        ),
                        "memory_samples": dict(self._memory_samples),
                        "last_memory_check": self._last_memory_check,
                    }
                )

            return metrics

    def reset(self) -> None:
        """Reset all metrics in a thread-safe manner."""
        with self._lock:
            self._operation_count = 0
            self._error_count = 0
            self._slow_query_count = 0
            self._last_operation_time = None
            self._avg_operation_time = 0.0
            self._memory_samples.clear()
            self._last_memory_check = None
            gc.collect()  # Help clean up memory
