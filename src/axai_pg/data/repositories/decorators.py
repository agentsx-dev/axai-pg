"""Decorators for repository operations and metrics tracking."""

import functools
from datetime import datetime
from typing import Callable, TypeVar, Type, Any
from .enhanced_factory import RepositoryFactory
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
            factory = RepositoryFactory.get_instance()
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
                metrics = factory._metrics.get(repo_key)
                if metrics:
                    metrics.record_operation(
                        duration_ms=duration_ms, error=error_occurred
                    )

        return wrapper

    return decorator


def with_repository(model_class: Type[T]):
    """
    Decorator for automatically injecting repository instances.

    Args:
        model_class: The model class to get the repository for
    """

    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            factory = RepositoryFactory.get_instance()
            repository = factory.get_repository(model_class)

            # Inject repository as first argument after self (if method) or as first argument (if function)
            if args and hasattr(args[0], func.__name__):
                # Method call - inject after self
                new_args = (args[0], repository) + args[1:]
            else:
                # Function call - inject as first argument
                new_args = (repository,) + args

            return await func(*new_args, **kwargs)

        return wrapper

    return decorator
