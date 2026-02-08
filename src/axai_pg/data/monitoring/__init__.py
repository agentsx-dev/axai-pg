from .metrics_collector import MetricsCollector
from .alert_manager import AlertManager, AlertSeverity
from .database_monitor import DatabaseMonitor

from ..config.database import set_monitoring_handlers


def initialize_monitoring():
    """Initialize all monitoring components."""
    metrics = MetricsCollector.get_instance()
    alerts = AlertManager.get_instance()
    monitor = DatabaseMonitor.get_instance()

    # Set up monitoring handlers in database layer
    set_monitoring_handlers(
        metrics_func=metrics.log_query, alert_func=alerts.check_pool_utilization
    )

    return monitor


# Initialize monitoring singleton
monitor = DatabaseMonitor.get_instance()

# Decorator for monitoring repository classes
monitor_repository = monitor.monitor_repository

# Decorator for monitoring individual queries
monitor_query = monitor.monitor_query

__all__ = [
    "MetricsCollector",
    "AlertManager",
    "AlertSeverity",
    "DatabaseMonitor",
    "initialize_monitoring",
    "monitor_repository",
    "monitor_query",
    "monitor",
]
