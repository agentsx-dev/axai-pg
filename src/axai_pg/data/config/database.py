from typing import Dict, Optional, Callable
from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine import Engine
from contextlib import contextmanager
import os
import time


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Monitoring hooks - will be set by monitoring system
_metrics_handler: Optional[Callable] = None
_alert_handler: Optional[Callable] = None


def set_monitoring_handlers(metrics_func: Callable, alert_func: Callable):
    """Set monitoring handlers after initialization to avoid circular imports."""
    global _metrics_handler, _alert_handler
    _metrics_handler = metrics_func
    _alert_handler = alert_func


@dataclass
class PostgresPoolConfig:
    pool_size: int = 5
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True


@dataclass
class PostgresConnectionConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: str = "public"
    ssl_mode: str = "prefer"

    @classmethod
    def from_env(cls) -> "PostgresConnectionConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "documents"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            schema=os.getenv("POSTGRES_SCHEMA", "public"),
            ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
        )


class DatabaseManager:
    _instance = None
    _engine: Optional[Engine] = None
    _SessionFactory = None

    def __init__(self):
        raise RuntimeError("Use DatabaseManager.get_instance()")

    @classmethod
    def get_instance(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._engine = None
            cls._instance._SessionFactory = None
        return cls._instance

    @classmethod
    def initialize(
        cls,
        conn_config: PostgresConnectionConfig,
        pool_config: Optional[PostgresPoolConfig] = None,
    ) -> None:
        instance = cls.get_instance()
        if pool_config is None:
            pool_config = PostgresPoolConfig()

        # Construct connection URL
        url = (
            f"postgresql://{conn_config.username}:{conn_config.password}"
            f"@{conn_config.host}:{conn_config.port}/{conn_config.database}"
        )

        # Configure engine with retry mechanism
        instance._engine = create_engine(
            url,
            pool_size=pool_config.pool_size,
            max_overflow=pool_config.max_overflow,
            pool_timeout=pool_config.pool_timeout,
            pool_recycle=pool_config.pool_recycle,
            pool_pre_ping=pool_config.pool_pre_ping,
            execution_options={"schema_translate_map": {None: conn_config.schema}},
        )

        instance._SessionFactory = sessionmaker(bind=instance._engine)

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError(
                "DatabaseManager not initialized. Call initialize() first."
            )
        return self._engine

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        if self._SessionFactory is None:
            raise RuntimeError(
                "DatabaseManager not initialized. Call initialize() first."
            )

        session = self._SessionFactory()
        start_time = time.time()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            # Monitor will catch and log the error
            raise
        finally:
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow transactions
                if _metrics_handler:
                    _metrics_handler(
                        "Transaction",
                        duration,
                        {
                            "type": "transaction",
                            "status": "commit" if not session.is_active else "rollback",
                        },
                    )
            session.close()

    async def check_health(self) -> Dict[str, any]:
        """Check database connectivity and return health metrics."""

        try:
            with self.session_scope() as session:
                # Execute simple query to verify connection
                session.execute("SELECT 1")

                # Get connection pool status
                pool_status = {
                    "size": self.engine.pool.size(),
                    "checkedin": self.engine.pool.checkedin(),
                    "overflow": self.engine.pool.overflow(),
                    "checkedout": self.engine.pool.checkedout(),
                }

                # Update monitoring metrics if handler is set
                if _metrics_handler:
                    _metrics_handler("pool_metrics", None, pool_status)

                return {
                    "status": "healthy",
                    "pool": pool_status,
                    "message": "Database connection successful",
                }
        except Exception as e:
            if _metrics_handler:
                _metrics_handler(
                    "error", None, {"error": str(e), "context": "health_check"}
                )
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed",
            }
