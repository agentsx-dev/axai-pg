"""Enhanced repository factory with thread safety and configurable metrics."""

from typing import Dict, Type, TypeVar, Optional, Any
import threading
from datetime import datetime
from contextlib import contextmanager
from .repository_metrics import RepositoryMetrics
from .metrics_config import RepositoryMetricsConfig, MetricsProfile
from .base_repository import BaseRepository
from ..config.database import DatabaseManager
from ..models.document import Document
from .document_repository import DocumentRepository

T = TypeVar("T")


class RepositoryFactory:
    """Thread-safe factory for managing repository instances with configurable metrics."""

    _instance: Optional["RepositoryFactory"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        if RepositoryFactory._instance is not None:
            raise RuntimeError("Use RepositoryFactory.get_instance()")

        self._repositories_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._config_lock = threading.Lock()

        self._repositories: Dict[str, BaseRepository] = {}
        self._metrics: Dict[str, RepositoryMetrics] = {}
        self._metrics_configs: Dict[str, RepositoryMetricsConfig] = {}

        # Default metrics configuration
        self._default_metrics_config = RepositoryMetricsConfig.create_minimal()

        # Initialize repositories
        self._initialize_repositories()

    @classmethod
    def get_instance(cls) -> "RepositoryFactory":
        """Get or create the singleton instance in a thread-safe manner."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize_repositories(self) -> None:
        """Initialize standard repositories with default configurations."""
        # Initialize document repository
        self.register_repository(
            "document", DocumentRepository(), self._default_metrics_config
        )

        # Additional repositories will be registered here as they're implemented

    def register_repository(
        self,
        key: str,
        repository: BaseRepository,
        metrics_config: Optional[RepositoryMetricsConfig] = None,
    ) -> None:
        """Register a new repository with optional metrics configuration."""
        config = metrics_config or self._default_metrics_config

        with self._repositories_lock, self._metrics_lock, self._config_lock:
            self._repositories[key] = repository
            self._metrics_configs[key] = config
            self._metrics[key] = RepositoryMetrics(config)

    def get_repository(self, model_class: Type[T]) -> BaseRepository[T]:
        """Get a repository instance for the given model class."""
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }

        repo_key = model_map.get(model_class)
        if not repo_key:
            raise ValueError(
                f"No repository configured for model: {model_class.__name__}"
            )

        with self._repositories_lock:
            if repo_key not in self._repositories:
                raise ValueError(
                    f"Repository not initialized for model: {model_class.__name__}"
                )
            return self._repositories[repo_key]

    def get_metrics(self, model_class: Type[T]) -> Dict[str, Any]:
        """Get current metrics for the repository of the given model class."""
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }

        repo_key = model_map.get(model_class)
        if not repo_key:
            raise ValueError(f"No metrics available for model: {model_class.__name__}")

        with self._metrics_lock:
            if repo_key not in self._metrics:
                raise ValueError(
                    f"Metrics not initialized for model: {model_class.__name__}"
                )
            return self._metrics[repo_key].get_metrics()

    def configure_metrics(
        self, model_class: Type[T], config: RepositoryMetricsConfig
    ) -> None:
        """Configure metrics collection for a specific repository."""
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }

        repo_key = model_map.get(model_class)
        if not repo_key:
            raise ValueError(
                f"No repository configured for model: {model_class.__name__}"
            )

        with self._config_lock, self._metrics_lock:
            self._metrics_configs[repo_key] = config
            self._metrics[repo_key] = RepositoryMetrics(config)

    def reset_metrics(self, model_class: Optional[Type[T]] = None) -> None:
        """Reset metrics for a specific repository or all repositories."""
        with self._metrics_lock:
            if model_class:
                model_map = {
                    Document: "document",
                    # Add other model mappings as they're implemented
                }
                repo_key = model_map.get(model_class)
                if repo_key and repo_key in self._metrics:
                    self._metrics[repo_key].reset()
            else:
                # Reset all metrics
                for metrics in self._metrics.values():
                    metrics.reset()

    @contextmanager
    def repository_session(self, model_class: Type[T]):
        """Context manager for repository operations with automatic metrics recording."""
        repository = self.get_repository(model_class)
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }
        repo_key = model_map[model_class]

        start_time = datetime.now()
        error_occurred = False

        try:
            yield repository
        except Exception as e:
            error_occurred = True
            raise
        finally:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            with self._metrics_lock:
                if repo_key in self._metrics:
                    self._metrics[repo_key].record_operation(
                        duration_ms=duration_ms, error=error_occurred
                    )
