from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
import json
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


class MetricsCollector:
    """Collects and manages database metrics and operational monitoring."""

    _instance = None
    METRICS_DIR = "metrics"
    LOGS_DIR = "logs"
    MAX_LOG_DAYS = 7

    def __init__(self):
        self._setup_directories()
        self._setup_logging()
        self._metrics = {"queries": {}, "errors": {}, "pool": {}, "storage": {}}

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        if cls._instance is None:
            cls._instance = MetricsCollector()
        return cls._instance

    def _setup_directories(self):
        """Create necessary directories for metrics and logs."""
        Path(self.METRICS_DIR).mkdir(exist_ok=True)
        Path(self.LOGS_DIR).mkdir(exist_ok=True)

    def _setup_logging(self):
        """Configure logging with rotation."""
        # Query logger
        query_logger = logging.getLogger("query_logger")
        query_logger.setLevel(logging.INFO)
        query_handler = RotatingFileHandler(
            f"{self.LOGS_DIR}/queries.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=self.MAX_LOG_DAYS,
        )
        query_logger.addHandler(query_handler)

        # Error logger
        error_logger = logging.getLogger("error_logger")
        error_logger.setLevel(logging.ERROR)
        error_handler = RotatingFileHandler(
            f"{self.LOGS_DIR}/errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=self.MAX_LOG_DAYS,
        )
        error_logger.addHandler(error_handler)

        # Performance logger
        perf_logger = logging.getLogger("performance_logger")
        perf_logger.setLevel(logging.INFO)
        perf_handler = RotatingFileHandler(
            f"{self.LOGS_DIR}/performance.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=self.MAX_LOG_DAYS,
        )
        perf_logger.addHandler(perf_handler)

        # Audit logger
        audit_logger = logging.getLogger("audit_logger")
        audit_logger.setLevel(logging.INFO)
        audit_handler = RotatingFileHandler(
            f"{self.LOGS_DIR}/audit.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=self.MAX_LOG_DAYS,
        )
        audit_logger.addHandler(audit_handler)

    def log_query(
        self, query: str, duration: float, context: Optional[Dict[str, Any]] = None
    ):
        """Log query execution with timing."""
        if duration > 1.0:  # Slow query threshold (1s)
            logging.getLogger("performance_logger").warning(
                f"Slow query detected: {duration:.2f}s\nQuery: {query}\nContext: {context}"
            )

        logging.getLogger("query_logger").info(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration": duration,
                    "query": query,
                    "context": context,
                }
            )
        )

        # Update query metrics
        self._metrics["queries"][datetime.now(UTC).isoformat()] = {
            "duration": duration,
            "slow": duration > 1.0,
        }

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error with context."""
        logging.getLogger("error_logger").error(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": str(error),
                    "type": type(error).__name__,
                    "context": context,
                }
            )
        )

        # Update error metrics
        error_type = type(error).__name__
        if error_type not in self._metrics["errors"]:
            self._metrics["errors"][error_type] = 0
        self._metrics["errors"][error_type] += 1

    def update_pool_metrics(self, pool_status: Dict[str, Any]):
        """Update connection pool metrics."""
        self._metrics["pool"] = {
            "timestamp": datetime.now(UTC).isoformat(),
            **pool_status,
        }

        # Check for pool alerts
        if pool_status.get("checkedout", 0) / pool_status.get("size", 1) > 0.8:
            logging.getLogger("performance_logger").warning(
                f"High pool utilization: {pool_status}"
            )

    def log_audit(self, action: str, user_id: str, details: Dict[str, Any]):
        """Log audit trail information."""
        logging.getLogger("audit_logger").info(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "action": action,
                    "user_id": user_id,
                    "details": details,
                }
            )
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return {"timestamp": datetime.now(UTC).isoformat(), "metrics": self._metrics}

    def cleanup_old_metrics(self):
        """Clean up metrics older than retention period."""
        cutoff = datetime.now(UTC) - timedelta(days=self.MAX_LOG_DAYS)

        # Cleanup query metrics
        self._metrics["queries"] = {
            k: v
            for k, v in self._metrics["queries"].items()
            if datetime.fromisoformat(k) > cutoff
        }

        # Reset error counts periodically
        if len(self._metrics["errors"]) > 1000:  # Prevent unbounded growth
            self._metrics["errors"] = {}
