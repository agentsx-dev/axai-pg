"""
Tests for monitoring and metrics collection.

NOTE: These tests require a real PostgreSQL database.
Run with: pytest tests/unit/config/test_monitoring.py -v --integration
"""
import pytest
from datetime import datetime, timedelta
import time
import asyncio
from unittest.mock import MagicMock
from sqlalchemy import text

from axai_pg.data.monitoring import (
    MetricsCollector,
    AlertManager,
    AlertSeverity,
)
from axai_pg.data.config.database import DatabaseManager, PostgresConnectionConfig, PostgresPoolConfig


@pytest.fixture
def setup_monitoring_db():
    """Setup test database connection."""
    config = PostgresConnectionConfig.from_env()
    pool_config = PostgresPoolConfig(
        pool_size=2,
        max_overflow=1
    )
    DatabaseManager.initialize(config, pool_config)
    return DatabaseManager.get_instance()


@pytest.fixture
def metrics_collector():
    """Get metrics collector instance."""
    return MetricsCollector.get_instance()


@pytest.fixture
def alert_manager():
    """Get alert manager instance."""
    return AlertManager.get_instance()


def test_metrics_collection(metrics_collector):
    """Test basic metrics collection."""
    # Test query logging
    metrics_collector.log_query("SELECT 1", 0.5, {"context": "test"})
    metrics = metrics_collector.get_metrics()

    assert "queries" in metrics["metrics"]
    assert len(metrics["metrics"]["queries"]) > 0

    # Test error logging
    test_error = ValueError("Test error")
    metrics_collector.log_error(test_error, {"context": "test"})
    metrics = metrics_collector.get_metrics()

    assert "errors" in metrics["metrics"]
    assert "ValueError" in metrics["metrics"]["errors"]
    assert metrics["metrics"]["errors"]["ValueError"] > 0


def test_alert_triggering(alert_manager):
    """Test alert triggering system."""
    # Mock alert handler
    mock_handler = MagicMock()
    alert_manager.add_alert_handler(mock_handler)

    # Test pool utilization alert
    pool_status = {
        "size": 5,
        "checkedout": 4,  # 80% utilization should trigger warning
        "checkedin": 1,
        "overflow": 0
    }
    alert_manager.check_pool_utilization(pool_status)

    # Verify alert was triggered
    mock_handler.assert_called_with(
        "High pool utilization detected",
        AlertSeverity.WARNING,
        {"utilization": 0.8, **pool_status}
    )


def test_query_monitoring(metrics_collector):
    """Test query monitoring."""
    # Log a query manually
    metrics_collector.log_query("SELECT 1", 0.1, {"source": "test"})
    metrics = metrics_collector.get_metrics()
    assert len(metrics["metrics"]["queries"]) > 0


def test_log_retention(metrics_collector):
    """Test log retention and cleanup."""
    # Add old metrics
    old_date = (datetime.utcnow() - timedelta(days=8)).isoformat()
    metrics_collector._metrics["queries"][old_date] = {
        "duration": 0.1,
        "slow": False
    }

    # Cleanup old metrics
    metrics_collector.cleanup_old_metrics()

    # Verify old metrics were removed
    assert old_date not in metrics_collector._metrics["queries"]


def test_alert_cooldown(alert_manager):
    """Test alert cooldown period."""
    mock_handler = MagicMock()
    alert_manager.add_alert_handler(mock_handler)

    # Trigger first alert
    alert_manager.check_error_rate(10, 100)  # 10% error rate
    first_call_count = mock_handler.call_count

    # Immediate second alert should be suppressed
    alert_manager.check_error_rate(10, 100)
    assert mock_handler.call_count == first_call_count  # No new alerts


def test_monitoring_integration(setup_monitoring_db, metrics_collector):
    """Test basic monitoring integration."""
    # Execute a query
    with DatabaseManager.get_instance().session_scope() as session:
        session.execute(text("SELECT 1"))

    # Check that metrics are being collected
    metrics = metrics_collector.get_metrics()
    assert "queries" in metrics["metrics"]
    assert "pool" in metrics["metrics"]


if __name__ == '__main__':
    pytest.main([__file__])
