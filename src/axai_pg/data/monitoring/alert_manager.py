from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta, UTC
import logging
from dataclasses import dataclass
from enum import Enum


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertThreshold:
    warning_threshold: float
    critical_threshold: float
    measurement_period: timedelta = timedelta(minutes=5)
    cooldown_period: timedelta = timedelta(minutes=15)


class AlertManager:
    """Manages database-related alerts and thresholds."""

    _instance = None

    def __init__(self):
        self._thresholds = {
            "pool_utilization": AlertThreshold(0.8, 0.9),
            "error_rate": AlertThreshold(0.05, 0.1),
            "slow_query_rate": AlertThreshold(0.1, 0.2),
            "storage_usage": AlertThreshold(0.8, 0.9),
        }
        self._last_alerts: Dict[str, datetime] = {}
        self._alert_handlers: List[
            Callable[[str, AlertSeverity, Dict[str, Any]], None]
        ] = [self._log_alert]

    @classmethod
    def get_instance(cls) -> "AlertManager":
        if cls._instance is None:
            cls._instance = AlertManager()
        return cls._instance

    def _log_alert(
        self, message: str, severity: AlertSeverity, context: Dict[str, Any]
    ):
        """Default alert handler that logs alerts."""
        logger = logging.getLogger("alert_logger")
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.error,
        }[severity]

        log_method(f"ALERT [{severity.value}]: {message}\nContext: {context}")

    def add_alert_handler(
        self, handler: Callable[[str, AlertSeverity, Dict[str, Any]], None]
    ):
        """Add a new alert handler."""
        self._alert_handlers.append(handler)

    def _should_alert(self, alert_type: str) -> bool:
        """Check if we should send an alert based on cooldown period."""
        now = datetime.now(UTC)
        if alert_type in self._last_alerts:
            threshold = self._thresholds.get(alert_type)
            if (
                threshold
                and now - self._last_alerts[alert_type] < threshold.cooldown_period
            ):
                return False
        return True

    def _trigger_alert(
        self,
        alert_type: str,
        message: str,
        severity: AlertSeverity,
        context: Dict[str, Any],
    ):
        """Trigger alert across all handlers if cooldown period has passed."""
        if self._should_alert(alert_type):
            self._last_alerts[alert_type] = datetime.now(UTC)
            for handler in self._alert_handlers:
                try:
                    handler(message, severity, context)
                except Exception as e:
                    logging.getLogger("error_logger").error(
                        f"Error in alert handler: {str(e)}\nAlert: {message}"
                    )

    def check_pool_utilization(self, pool_status: Dict[str, Any]):
        """Check connection pool metrics and trigger alerts if needed."""
        if not pool_status:
            return

        utilization = pool_status.get("checkedout", 0) / pool_status.get("size", 1)
        threshold = self._thresholds["pool_utilization"]

        if utilization >= threshold.critical_threshold:
            self._trigger_alert(
                "pool_utilization",
                "Critical pool utilization threshold exceeded",
                AlertSeverity.CRITICAL,
                {"utilization": utilization, **pool_status},
            )
        elif utilization >= threshold.warning_threshold:
            self._trigger_alert(
                "pool_utilization",
                "High pool utilization detected",
                AlertSeverity.WARNING,
                {"utilization": utilization, **pool_status},
            )

    def check_error_rate(self, error_count: int, total_operations: int):
        """Check error rate and trigger alerts if needed."""
        if total_operations == 0:
            return

        error_rate = error_count / total_operations
        threshold = self._thresholds["error_rate"]

        if error_rate >= threshold.critical_threshold:
            self._trigger_alert(
                "error_rate",
                "Critical error rate threshold exceeded",
                AlertSeverity.CRITICAL,
                {
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "total_operations": total_operations,
                },
            )
        elif error_rate >= threshold.warning_threshold:
            self._trigger_alert(
                "error_rate",
                "High error rate detected",
                AlertSeverity.WARNING,
                {
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "total_operations": total_operations,
                },
            )

    def check_slow_queries(self, slow_count: int, total_queries: int):
        """Check slow query rate and trigger alerts if needed."""
        if total_queries == 0:
            return

        slow_rate = slow_count / total_queries
        threshold = self._thresholds["slow_query_rate"]

        if slow_rate >= threshold.critical_threshold:
            self._trigger_alert(
                "slow_query_rate",
                "Critical slow query rate threshold exceeded",
                AlertSeverity.CRITICAL,
                {
                    "slow_rate": slow_rate,
                    "slow_count": slow_count,
                    "total_queries": total_queries,
                },
            )
        elif slow_rate >= threshold.warning_threshold:
            self._trigger_alert(
                "slow_query_rate",
                "High slow query rate detected",
                AlertSeverity.WARNING,
                {
                    "slow_rate": slow_rate,
                    "slow_count": slow_count,
                    "total_queries": total_queries,
                },
            )

    def check_storage_usage(self, used_bytes: int, total_bytes: int):
        """Check storage usage and trigger alerts if needed."""
        if total_bytes == 0:
            return

        usage_ratio = used_bytes / total_bytes
        threshold = self._thresholds["storage_usage"]

        if usage_ratio >= threshold.critical_threshold:
            self._trigger_alert(
                "storage_usage",
                "Critical storage usage threshold exceeded",
                AlertSeverity.CRITICAL,
                {
                    "usage_ratio": usage_ratio,
                    "used_bytes": used_bytes,
                    "total_bytes": total_bytes,
                },
            )
        elif usage_ratio >= threshold.warning_threshold:
            self._trigger_alert(
                "storage_usage",
                "High storage usage detected",
                AlertSeverity.WARNING,
                {
                    "usage_ratio": usage_ratio,
                    "used_bytes": used_bytes,
                    "total_bytes": total_bytes,
                },
            )
