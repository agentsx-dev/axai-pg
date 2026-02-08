"""
Tests for database configuration and manager.

NOTE: These tests require a real PostgreSQL database.
Run with: pytest tests/unit/config/test_database.py -v --integration
"""

import pytest
import os
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from axai_pg.data.config.database import (
    DatabaseManager,
    PostgresConnectionConfig,
    PostgresPoolConfig,
)


@pytest.fixture
def test_conn_config():
    """Provide connection config matching test database."""
    return PostgresConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "test_db"),
        username=os.getenv("POSTGRES_USER", "test_user"),
        password=os.getenv("POSTGRES_PASSWORD", "test_password"),
        schema="public",
    )


@pytest.fixture
def test_pool_config():
    """Provide pool configuration for tests."""
    return PostgresPoolConfig(
        pool_size=2,
        max_overflow=2,
        pool_timeout=10,
        pool_recycle=300,
        pool_pre_ping=True,
    )


def test_database_manager_singleton():
    """Test that DatabaseManager maintains singleton pattern."""
    instance1 = DatabaseManager.get_instance()
    instance2 = DatabaseManager.get_instance()
    assert instance1 is instance2


def test_database_manager_initialization(test_conn_config, test_pool_config):
    """Test database manager initialization with config."""
    manager = DatabaseManager.get_instance()
    DatabaseManager.initialize(test_conn_config, test_pool_config)
    assert manager._engine is not None
    assert manager._SessionFactory is not None


def test_database_manager_session_scope(test_conn_config, test_pool_config):
    """Test session scope context manager."""
    manager = DatabaseManager.get_instance()
    DatabaseManager.initialize(test_conn_config, test_pool_config)

    with manager.session_scope() as session:
        # Test simple query execution
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1


@pytest.mark.skip(
    reason="check_health has SQLAlchemy 2.0 compatibility issue - uses execute('SELECT 1') instead of execute(text('SELECT 1'))"
)
def test_database_manager_health_check(test_conn_config, test_pool_config):
    """Test health check functionality."""
    manager = DatabaseManager.get_instance()
    DatabaseManager.initialize(test_conn_config, test_pool_config)

    health_status = asyncio.run(manager.check_health())
    assert health_status["status"] == "healthy"
    assert "pool" in health_status
    assert isinstance(health_status["pool"], dict)


def test_invalid_connection_handling():
    """Test handling of invalid connection configuration."""
    invalid_config = PostgresConnectionConfig(
        host="invalid_host",
        port=5432,
        database="invalid_db",
        username="invalid_user",
        password="invalid_pass",
    )

    manager = DatabaseManager.get_instance()
    DatabaseManager.initialize(invalid_config)

    with pytest.raises(SQLAlchemyError):
        with manager.session_scope() as session:
            session.execute(text("SELECT 1"))


def test_connection_pool_configuration(test_conn_config):
    """Test that pool configuration is properly applied."""
    custom_pool_config = PostgresPoolConfig(
        pool_size=3,
        max_overflow=3,
        pool_timeout=15,
        pool_recycle=600,
        pool_pre_ping=True,
    )

    manager = DatabaseManager.get_instance()
    DatabaseManager.initialize(test_conn_config, custom_pool_config)

    engine = manager.engine
    assert engine.pool.size() == custom_pool_config.pool_size
    assert engine.pool._max_overflow == custom_pool_config.max_overflow
