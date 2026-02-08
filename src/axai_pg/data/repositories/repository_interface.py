"""Repository interfaces and common types."""

from typing import Dict, TypeVar, Type, Protocol, runtime_checkable

T = TypeVar("T")

# Model mappings for metrics tracking
MODEL_MAPPINGS: Dict[Type, str] = {
    "Document": "document",
    # Add other model mappings as they're implemented
}


@runtime_checkable
class Repository(Protocol[T]):
    """Base protocol for repositories."""

    model_class: Type[T]
