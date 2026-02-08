from typing import Optional
import os
from dataclasses import dataclass
from .database import PostgresConnectionConfig, PostgresPoolConfig
from .environments import Environments, EnvironmentConfig


@dataclass
class AppSettings:
    """Application settings including database configuration."""

    environment: str
    conn_config: PostgresConnectionConfig
    env_config: EnvironmentConfig
    debug_mode: bool
    log_sql: bool
    connection_timeout: int

    @classmethod
    def load_from_env(cls) -> "AppSettings":
        """Load and validate all application settings from environment variables."""
        # Determine environment
        environment = os.getenv("APP_ENV", "development").lower()
        if environment not in ("development", "test", "production"):
            raise ValueError(f"Invalid environment: {environment}")

        # Load environment-specific configuration
        env_config = Environments.get_config(environment)

        # Load database configuration
        conn_config = PostgresConnectionConfig(
            host=cls._require_env("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=cls._require_env("POSTGRES_DB"),
            username=cls._require_env("POSTGRES_USER"),
            password=cls._require_env("POSTGRES_PASSWORD"),
            schema=os.getenv("POSTGRES_SCHEMA", "public"),
            ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
        )

        # Load additional settings
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        log_sql = os.getenv("LOG_SQL", "false").lower() == "true"
        connection_timeout = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))

        return cls(
            environment=environment,
            conn_config=conn_config,
            env_config=env_config,
            debug_mode=debug_mode,
            log_sql=log_sql,
            connection_timeout=connection_timeout,
        )

    @staticmethod
    def _require_env(name: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(name)
        if value is None:
            raise ValueError(f"Required environment variable {name} is not set")
        return value

    def validate(self) -> None:
        """Validate the configuration settings."""
        # Validate database configuration
        if not self.conn_config.host:
            raise ValueError("Database host is required")
        if not self.conn_config.database:
            raise ValueError("Database name is required")
        if not self.conn_config.username:
            raise ValueError("Database username is required")

        # Validate pool configuration
        pool_config = self.env_config.pool_config
        if pool_config.pool_size < 1:
            raise ValueError("Pool size must be at least 1")
        if pool_config.max_overflow < 0:
            raise ValueError("Max overflow must be non-negative")
        if pool_config.pool_timeout < 1:
            raise ValueError("Pool timeout must be positive")

        # Validate timeouts
        if self.connection_timeout < 1:
            raise ValueError("Connection timeout must be positive")

    def get_engine_settings(self) -> dict:
        """Get SQLAlchemy engine configuration dictionary."""
        return {
            "pool_size": self.env_config.pool_config.pool_size,
            "max_overflow": self.env_config.pool_config.max_overflow,
            "pool_timeout": self.env_config.pool_config.pool_timeout,
            "pool_recycle": self.env_config.pool_config.pool_recycle,
            "pool_pre_ping": self.env_config.pool_config.pool_pre_ping,
            "echo": self.log_sql,
            "connect_args": {
                "connect_timeout": self.connection_timeout,
                "sslmode": self.conn_config.ssl_mode,
            },
            **self.env_config.extra_settings,
        }


class Settings:
    """Singleton settings manager."""

    _instance: Optional[AppSettings] = None

    @classmethod
    def load(cls) -> AppSettings:
        """Load settings if not already loaded."""
        if cls._instance is None:
            cls._instance = AppSettings.load_from_env()
            cls._instance.validate()
        return cls._instance

    @classmethod
    def get(cls) -> AppSettings:
        """Get current settings or load if not initialized."""
        return cls.load()

    @classmethod
    def reload(cls) -> AppSettings:
        """Force reload settings from environment."""
        cls._instance = None
        return cls.load()
