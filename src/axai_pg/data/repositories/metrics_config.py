"""Configuration for repository metrics collection."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import timedelta


@dataclass
class MetricsProfile:
    """Default metrics collection profiles."""

    enable_operation_counting: bool = True
    enable_error_tracking: bool = True
    enable_timing_stats: bool = True
    enable_memory_tracking: bool = False
    slow_query_threshold: timedelta = timedelta(seconds=1)
    memory_sample_rate: int = 100  # Sample every N operations


@dataclass
class RepositoryMetricsConfig:
    """Configuration for repository metrics collection."""

    enabled: bool = True
    profile: MetricsProfile = None

    def __post_init__(self):
        if self.profile is None:
            self.profile = MetricsProfile()

    custom_settings: Optional[Dict[str, Any]] = None

    @classmethod
    def create_disabled(cls) -> "RepositoryMetricsConfig":
        """Create a configuration with metrics disabled."""
        return cls(enabled=False)

    @classmethod
    def create_minimal(cls) -> "RepositoryMetricsConfig":
        """Create a minimal metrics configuration."""
        return cls(
            enabled=True,
            profile=MetricsProfile(
                enable_operation_counting=True,
                enable_error_tracking=True,
                enable_timing_stats=False,
                enable_memory_tracking=False,
            ),
        )

    @classmethod
    def create_full(cls) -> "RepositoryMetricsConfig":
        """Create a full metrics configuration with all features enabled."""
        return cls(
            enabled=True,
            profile=MetricsProfile(
                enable_operation_counting=True,
                enable_error_tracking=True,
                enable_timing_stats=True,
                enable_memory_tracking=True,
                slow_query_threshold=timedelta(milliseconds=500),
                memory_sample_rate=50,
            ),
        )
