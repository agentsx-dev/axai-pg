from typing import Optional, Type
import functools
import time

from ..config.database import DatabaseManager
from .metrics_collector import MetricsCollector
from .alert_manager import AlertManager


class DatabaseMonitor:
    """Integrates monitoring and alerting with database operations."""

    _instance = None

    def __init__(self):
        self.metrics = MetricsCollector.get_instance()
        self.alerts = AlertManager.get_instance()
        self._setup_monitoring()

    @classmethod
    def get_instance(cls) -> "DatabaseMonitor":
        if cls._instance is None:
            cls._instance = DatabaseMonitor()
        return cls._instance

    def _setup_monitoring(self):
        """Setup SQLAlchemy event listeners and monitoring hooks."""
        self.metrics = MetricsCollector.get_instance()
        self.alerts = AlertManager.get_instance()

        # Defer engine setup until DatabaseManager is initialized
        try:
            from sqlalchemy import event

            engine = DatabaseManager.get_instance().engine

            # Monitor connection pool
            @event.listens_for(engine, "checkout")
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                self._update_pool_metrics()

            @event.listens_for(engine, "checkin")
            def receive_checkin(dbapi_connection, connection_record):
                self._update_pool_metrics()

        except RuntimeError:
            # DatabaseManager not initialized yet, we'll set up events later
            pass

    def _update_pool_metrics(self):
        """Update pool metrics and check thresholds."""
        engine = DatabaseManager.get_instance().engine
        pool_status = {
            "size": engine.pool.size(),
            "checkedin": engine.pool.checkedin(),
            "overflow": engine.pool.overflow(),
            "checkedout": engine.pool.checkedout(),
        }

        self.metrics.update_pool_metrics(pool_status)
        self.alerts.check_pool_utilization(pool_status)

    def monitor_query(self, func):
        """Decorator to monitor query execution."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time

                # Extract query context
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                }

                if error:
                    self.metrics.log_error(error, context)

                # Log query execution
                self.metrics.log_query(
                    query=str(args[0]) if args else "Unknown query",
                    duration=duration,
                    context=context,
                )

                # Check for slow queries
                if duration > 1.0:  # 1 second threshold
                    self.alerts.check_slow_queries(1, 1)

        return wrapper

    def monitor_repository(self, cls: Type):
        """Class decorator to monitor repository operations."""
        original_init = cls.__init__

        @functools.wraps(original_init)
        def init_wrapper(repo_self, *args, **kwargs):
            original_init(repo_self, *args, **kwargs)

            # Wrap repository methods
            for attr_name in dir(repo_self):
                if not attr_name.startswith("_"):  # Only public methods
                    attr = getattr(repo_self, attr_name)
                    if callable(attr):
                        wrapped = self._wrap_repository_method(attr)
                        setattr(repo_self, attr_name, wrapped)

            return repo_self

        cls.__init__ = init_wrapper
        return cls

    def _wrap_repository_method(self, method):
        """Wrap repository methods with monitoring."""

        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            try:
                result = method(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time

                # Extract operation context
                context = {
                    "method": method.__name__,
                    "repository": method.__self__.__class__.__name__,
                    "duration": duration,
                }

                if error:
                    self.metrics.log_error(error, context)
                    # Update error rate metrics
                    self.alerts.check_error_rate(1, 1)

                # Log operation for audit
                self.metrics.log_audit(
                    action=method.__name__,
                    user_id="system",  # Should be replaced with actual user context
                    details=context,
                )

        return wrapper

    def check_storage_usage(self, organization_id: Optional[str] = None):
        """Check storage usage for organization or overall."""
        try:
            with DatabaseManager.get_instance().session_scope() as session:
                if organization_id:
                    # Query organization-specific storage
                    result = session.execute(
                        """
                        SELECT pg_total_relation_size(relid) as used_bytes
                        FROM pg_stat_user_tables
                        WHERE schemaname = current_schema()
                        AND relname LIKE :prefix
                    """,
                        {"prefix": f"{organization_id}%"},
                    )
                else:
                    # Query overall storage
                    result = session.execute(
                        """
                        SELECT pg_database_size(current_database()) as used_bytes
                    """
                    )

                used_bytes = result.scalar()

                # Assume 80% of allocated storage as total_bytes for demo
                # In production, this should come from actual storage limits
                total_bytes = used_bytes * 1.25

                self.alerts.check_storage_usage(used_bytes, total_bytes)

                return {
                    "used_bytes": used_bytes,
                    "total_bytes": total_bytes,
                    "usage_ratio": used_bytes / total_bytes,
                }
        except Exception as e:
            self.metrics.log_error(e, {"context": "storage_check"})
            raise
