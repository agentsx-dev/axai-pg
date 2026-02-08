from typing import Dict, Type, TypeVar, Optional, Any
from datetime import datetime
from .base_repository import BaseRepository
from .document_repository import DocumentRepository
from ..models.document import Document

T = TypeVar("T")


class RepositoryMetrics:
    """Metrics tracking for repository operations."""

    def __init__(self):
        self.operation_count: int = 0
        self.error_count: int = 0
        self.slow_query_count: int = 0
        self.last_operation_time: Optional[datetime] = None
        self.avg_operation_time: float = 0.0

    def record_operation(
        self, duration_ms: float, error: bool = False, slow: bool = False
    ):
        """Record metrics for a repository operation."""
        self.operation_count += 1
        if error:
            self.error_count += 1
        if slow:
            self.slow_query_count += 1

        self.last_operation_time = datetime.now()
        # Update running average
        self.avg_operation_time = (
            self.avg_operation_time * (self.operation_count - 1) + duration_ms
        ) / self.operation_count


class RepositoryFactory:
    """Factory for creating and managing repository instances with metrics tracking."""

    _instance: Optional["RepositoryFactory"] = None
    _repositories: Dict[str, BaseRepository] = {}
    _metrics: Dict[str, RepositoryMetrics] = {}

    def __init__(self):
        if RepositoryFactory._instance is not None:
            raise RuntimeError("Use RepositoryFactory.get_instance()")
        self._initialize_repositories()

    @classmethod
    def get_instance(cls) -> "RepositoryFactory":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_repositories(self):
        """Initialize standard repositories."""
        # Initialize document repository
        self._repositories["document"] = DocumentRepository()
        self._metrics["document"] = RepositoryMetrics()

        # Additional repositories will be initialized here as they're implemented

    def get_repository(self, model_class: Type[T]) -> BaseRepository[T]:
        """Get a repository instance for the given model class."""
        # Map model classes to repository keys
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }

        repo_key = model_map.get(model_class)
        if not repo_key or repo_key not in self._repositories:
            raise ValueError(
                f"No repository configured for model: {model_class.__name__}"
            )

        return self._repositories[repo_key]

    def get_metrics(self, model_class: Type[T]) -> RepositoryMetrics:
        """Get metrics for the repository of the given model class."""
        model_map = {
            Document: "document",
            # Add other model mappings as they're implemented
        }

        repo_key = model_map.get(model_class)
        if not repo_key or repo_key not in self._metrics:
            raise ValueError(f"No metrics available for model: {model_class.__name__}")

        return self._metrics[repo_key]

    def reset_metrics(self, model_class: Optional[Type[T]] = None):
        """Reset metrics for a specific repository or all repositories."""
        if model_class:
            model_map = {
                Document: "document",
                # Add other model mappings as they're implemented
            }
            repo_key = model_map.get(model_class)
            if repo_key and repo_key in self._metrics:
                self._metrics[repo_key] = RepositoryMetrics()
        else:
            # Reset all metrics
            for key in self._metrics:
                self._metrics[key] = RepositoryMetrics()
