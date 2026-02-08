"""Tests for the enhanced repository factory implementation."""

import pytest
import threading
from datetime import datetime, timedelta
from typing import List
from axai_pg.data.repositories.enhanced_factory import RepositoryFactory
from axai_pg.data.repositories.metrics_config import RepositoryMetricsConfig
from axai_pg.data.models.document import Document
from axai_pg.data.repositories.document_repository import DocumentRepository


@pytest.fixture(autouse=True)
def factory():
    """Get a clean instance of the repository factory before each test."""
    # Reset the singleton between tests
    RepositoryFactory._instance = None
    factory = RepositoryFactory.get_instance()
    # Reset all metrics to ensure clean state
    factory.reset_metrics()
    return factory


def test_singleton_pattern():
    """Test that factory properly implements singleton pattern."""
    factory1 = RepositoryFactory.get_instance()
    factory2 = RepositoryFactory.get_instance()
    assert factory1 is factory2

    # Verify direct instantiation is prevented
    with pytest.raises(RuntimeError):
        RepositoryFactory()


def test_thread_safety():
    """Test thread-safe repository and metrics access."""
    factory = RepositoryFactory.get_instance()

    def worker():
        # Get repository and record some operations
        factory.get_repository(Document)
        metrics = factory._metrics["document"]
        for _ in range(100):
            metrics.record_operation(duration_ms=10.0)

    threads: List[threading.Thread] = []
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify operation count is correct (10 threads * 100 operations)
    metrics = factory.get_metrics(Document)
    assert metrics["operation_count"] == 1000


def test_metrics_configuration():
    """Test metrics configuration and collection."""
    factory = RepositoryFactory.get_instance()

    # Configure full metrics for document repository
    config = RepositoryMetricsConfig.create_full()
    factory.configure_metrics(Document, config)

    # Perform some operations
    factory.get_repository(Document)
    metrics = factory._metrics["document"]

    # Fast operation
    metrics.record_operation(duration_ms=10.0)

    # Slow operation
    metrics.record_operation(duration_ms=2000.0)

    # Error operation
    metrics.record_operation(duration_ms=50.0, error=True)

    # Verify metrics
    current_metrics = factory.get_metrics(Document)
    assert current_metrics["operation_count"] == 3
    assert current_metrics["error_count"] == 1
    assert current_metrics["slow_query_count"] == 1
    assert current_metrics["error_rate"] == 1 / 3
    assert "current_memory_mb" in current_metrics


def test_resource_cleanup():
    """Test proper resource cleanup and memory management."""
    factory = RepositoryFactory.get_instance()

    # Configure memory tracking
    config = RepositoryMetricsConfig.create_full()
    factory.configure_metrics(Document, config)

    # Record operations to trigger memory sampling
    metrics = factory._metrics["document"]
    for _ in range(200):  # Trigger multiple memory samples
        metrics.record_operation(duration_ms=10.0)

    # Verify memory samples are being collected and cleaned up
    current_metrics = factory.get_metrics(Document)
    samples = current_metrics["memory_samples"]

    # Should have samples but not too many (due to cleanup of old samples)
    assert len(samples) > 0
    assert len(samples) <= 60  # Maximum samples for 1 hour at default rate

    # Verify samples are recent
    oldest_sample = min(samples.keys())
    assert datetime.now() - oldest_sample < timedelta(hours=1)


def test_repository_session():
    """Test repository session context manager."""
    factory = RepositoryFactory.get_instance()

    with factory.repository_session(Document) as repo:
        # Session should be active
        assert isinstance(repo, DocumentRepository)

    # Verify metrics were recorded
    metrics = factory.get_metrics(Document)
    assert metrics["operation_count"] == 1


def test_metrics_reset():
    """Test metrics reset functionality."""
    factory = RepositoryFactory.get_instance()
    metrics = factory._metrics["document"]

    # Record some operations
    metrics.record_operation(duration_ms=10.0)
    metrics.record_operation(duration_ms=20.0, error=True)

    # Verify metrics were recorded
    current_metrics = factory.get_metrics(Document)
    assert current_metrics["operation_count"] == 2
    assert current_metrics["error_count"] == 1

    # Reset metrics
    factory.reset_metrics(Document)

    # Verify metrics were reset
    reset_metrics = factory.get_metrics(Document)
    assert reset_metrics["operation_count"] == 0
    assert reset_metrics["error_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__])
