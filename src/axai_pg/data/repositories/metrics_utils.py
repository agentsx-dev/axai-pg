"""Utilities for metrics tracking in repositories."""

import functools
from datetime import datetime
from typing import Callable, TypeVar, Type, Any
from ..models.document import Document

T = TypeVar("T")


def track_metrics(model_class: Type[T]):
    """
    Decorator for tracking repository operation metrics.

    Args:
        model_class: The model class associated with the repository operation
    """

    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not args:
                return await func(*args, **kwargs)

            repository = args[0]
            if not hasattr(repository, "_metrics"):
                return await func(*args, **kwargs)

            model_map = {
                Document: "document",
                # Add other model mappings as they're implemented
            }
            repo_key = model_map.get(model_class)

            if not repo_key:
                return await func(*args, **kwargs)

            start_time = datetime.now()
            error_occurred = False

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = True
                raise
            finally:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                metrics = repository._metrics
                if metrics:
                    metrics.record_operation(
                        duration_ms=duration_ms, error=error_occurred
                    )

        return wrapper

    return decorator


def with_metrics(cls: Type[T]) -> Type[T]:
    """
    Class decorator for tracking metrics on repository operations.

    Args:
        cls: The repository class to track metrics for
    """
    original_init = cls.__init__

    @functools.wraps(original_init)
    def init_wrapper(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._metrics = None  # Initialize metrics to None

    cls.__init__ = init_wrapper
    return cls
