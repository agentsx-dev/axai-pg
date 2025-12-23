import pytest
from datetime import datetime, timedelta
import time
import logging
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from axai_pg.data.monitoring import (
    initialize_monitoring,
    MetricsCollector,
    AlertManager,
    AlertSeverity,
    monitor_repository,
    monitor_query
)
from axai_pg.data.config.database import DatabaseManager, PostgresConnectionConfig, PostgresPoolConfig

@pytest.fixture
def setup_test_db():
    """Setup test database connection."""
    config = PostgresConnectionConfig(
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_pass"
    )
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

@monitor_repository
class TestRepository:
    """Test repository for monitoring decorator."""
    def test_operation(self):
        return "test"
    
    def failing_operation(self):
        raise ValueError("Test error")

def test_repository_monitoring(metrics_collector):
    """Test repository monitoring decorator."""
    repo = TestRepository()
    
    # Test successful operation
    repo.test_operation()
    metrics = metrics_collector.get_metrics()
    assert len(metrics["metrics"]["queries"]) > 0
    
    # Test failed operation
    with pytest.raises(ValueError):
        repo.failing_operation()
    metrics = metrics_collector.get_metrics()
    assert "ValueError" in metrics["metrics"]["errors"]

@monitor_query
def test_query(query: str):
    """Test query for monitoring decorator."""
    time.sleep(0.1)  # Simulate query execution
    return query

def test_query_monitoring(metrics_collector):
    """Test query monitoring decorator."""
    # Test normal query
    test_query("SELECT 1")
    metrics = metrics_collector.get_metrics()
    assert len(metrics["metrics"]["queries"]) > 0
    
    # Test slow query
    with patch('time.time') as mock_time:
        mock_time.side_effect = [0, 2.0]  # Simulate 2 second query
        test_query("SELECT pg_sleep(2)")
    
    metrics = metrics_collector.get_metrics()
    slow_queries = [q for q in metrics["metrics"]["queries"].values() if q["slow"]]
    assert len(slow_queries) > 0

def test_storage_monitoring(setup_test_db):
    """Test storage usage monitoring."""
    monitor = initialize_monitoring()
    
    # Test storage check
    storage_info = monitor.check_storage_usage()
    assert "used_bytes" in storage_info
    assert "total_bytes" in storage_info
    assert "usage_ratio" in storage_info
    
    # Test organization-specific storage
    org_storage = monitor.check_storage_usage("test_org")
    assert "used_bytes" in org_storage
    assert "total_bytes" in org_storage
    assert "usage_ratio" in org_storage

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

def test_monitoring_integration(setup_test_db, metrics_collector, alert_manager):
    """Test full monitoring integration."""
    monitor = initialize_monitoring()
    
    # Test query monitoring
    with DatabaseManager.get_instance().session_scope() as session:
        session.execute(text("SELECT 1"))
    
    metrics = metrics_collector.get_metrics()
    assert "queries" in metrics["metrics"]
    assert "pool" in metrics["metrics"]
    
    # Test pool monitoring
    pool_metrics = metrics["metrics"]["pool"]
    assert "size" in pool_metrics
    assert "checkedin" in pool_metrics
    assert "checkedout" in pool_metrics
    assert "overflow" in pool_metrics

if __name__ == '__main__':
    pytest.main([__file__])
