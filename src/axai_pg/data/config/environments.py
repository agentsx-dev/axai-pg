from typing import Dict, Any
from dataclasses import dataclass
from .database import PostgresPoolConfig


@dataclass
class EnvironmentConfig:
    pool_config: PostgresPoolConfig
    extra_settings: Dict[str, Any]


class Environments:
    @staticmethod
    def get_development_config() -> EnvironmentConfig:
        """Development environment with minimal pool settings."""
        return EnvironmentConfig(
            pool_config=PostgresPoolConfig(
                pool_size=2,
                max_overflow=2,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
            ),
            extra_settings={
                "echo": True,  # SQL query logging
                "echo_pool": True,  # Pool event logging
                "timeout": 60,  # Command timeout
            },
        )

    @staticmethod
    def get_test_config() -> EnvironmentConfig:
        """Test environment with minimal pool settings."""
        return EnvironmentConfig(
            pool_config=PostgresPoolConfig(
                pool_size=1,
                max_overflow=1,
                pool_timeout=10,
                pool_recycle=300,
                pool_pre_ping=True,
            ),
            extra_settings={
                "echo": False,
                "echo_pool": False,
                "timeout": 30,
            },
        )

    @staticmethod
    def get_production_config() -> EnvironmentConfig:
        """Production environment with conservative initial pool settings."""
        return EnvironmentConfig(
            pool_config=PostgresPoolConfig(
                pool_size=5,
                max_overflow=5,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
            ),
            extra_settings={
                "echo": False,
                "echo_pool": False,
                "timeout": 60,
                "pool_reset_on_return": "commit",  # Reset transaction state on return  # noqa: E501
                "max_identifier_length": 63,  # PostgreSQL maximum identifier length
            },
        )

    @classmethod
    def get_config(cls, environment: str) -> EnvironmentConfig:
        """Get configuration for specified environment."""
        env_map = {
            "development": cls.get_development_config,
            "test": cls.get_test_config,
            "production": cls.get_production_config,
        }

        config_getter = env_map.get(environment.lower())
        if not config_getter:
            raise ValueError(f"Unknown environment: {environment}")

        return config_getter()
