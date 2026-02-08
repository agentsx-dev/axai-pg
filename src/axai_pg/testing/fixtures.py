"""
Pytest fixtures for testing with axai_pg.

These fixtures can be imported by external systems to simplify integration testing.

Usage in external test file:
    from axai_pg.testing.fixtures import axai_db_session

    def test_my_feature(axai_db_session):
        # Use session for testing
        # Automatic rollback after test
        pass
"""

import os
import pytest
from typing import Generator

from ..utils.db_initializer import DatabaseInitializer, DatabaseInitializerConfig
from ..data.config.database import PostgresConnectionConfig, DatabaseManager


@pytest.fixture(scope="session")
def axai_db_config() -> PostgresConnectionConfig:
    """
    Provide PostgreSQL connection configuration for tests.

    This fixture reads from environment variables with sensible defaults
    for testing. Can be overridden by setting environment variables:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: test_db)
    - POSTGRES_USER (default: test_user)
    - POSTGRES_PASSWORD (default: test_password)

    Returns:
        PostgresConnectionConfig instance
    """
    return PostgresConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "test_db"),
        username=os.getenv("POSTGRES_USER", "test_user"),
        password=os.getenv("POSTGRES_PASSWORD", "test_password"),
        schema=os.getenv("POSTGRES_SCHEMA", "public"),
    )


@pytest.fixture(scope="session")
def axai_test_db(
    axai_db_config: PostgresConnectionConfig,
) -> Generator[DatabaseInitializer, None, None]:
    """
    Session-scoped fixture that sets up and tears down the test database.

    This fixture:
    - Creates the database
    - Applies the schema
    - Initializes DatabaseManager
    - Tears down the database after all tests complete

    The database is NOT dropped after tests by default. To enable automatic
    cleanup, set the environment variable AXAI_AUTO_DROP_DB=true.

    Args:
        axai_db_config: Database connection configuration

    Yields:
        DatabaseInitializer instance
    """
    auto_drop = os.getenv("AXAI_AUTO_DROP_DB", "false").lower() == "true"

    config = DatabaseInitializerConfig(
        connection_config=axai_db_config,
        auto_create_db=True,
        auto_drop_on_exit=auto_drop,
        wait_timeout=30,
        retry_attempts=5,
    )

    db_init = DatabaseInitializer(config)

    # Setup database
    load_sample = os.getenv("AXAI_LOAD_SAMPLE_DATA", "false").lower() == "true"
    success = db_init.setup_database(load_sample_data=load_sample)

    if not success:
        pytest.fail("Failed to setup test database")

    yield db_init

    # Teardown
    db_init.teardown_database()


@pytest.fixture(scope="function")
def axai_db_session(axai_test_db: DatabaseInitializer) -> Generator:
    """
    Function-scoped fixture providing a database session with automatic rollback.

    Each test gets a fresh session that is rolled back after the test completes,
    ensuring test isolation without recreating the database.

    Args:
        axai_test_db: Session-scoped database initializer

    Yields:
        SQLAlchemy session
    """
    db_manager = axai_test_db.get_database_manager()

    # Create a connection and begin a transaction
    connection = db_manager.engine.connect()
    transaction = connection.begin()

    # Create a session bound to this connection
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Rollback and cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def axai_db_manager(axai_test_db: DatabaseInitializer) -> DatabaseManager:
    """
    Function-scoped fixture providing the DatabaseManager instance.

    This gives direct access to the DatabaseManager for tests that need
    to manage their own sessions or access engine properties.

    Args:
        axai_test_db: Session-scoped database initializer

    Returns:
        DatabaseManager instance
    """
    return axai_test_db.get_database_manager()


# Additional utility fixtures for common testing scenarios


@pytest.fixture(scope="function")
def axai_clean_db_session(axai_test_db: DatabaseInitializer) -> Generator:
    """
    Function-scoped fixture providing a clean database session without rollback.

    Unlike axai_db_session, this fixture commits changes. Useful for tests
    that need to verify data persistence across operations.

    WARNING: Changes are NOT rolled back. Use with caution.

    Args:
        axai_test_db: Session-scoped database initializer

    Yields:
        SQLAlchemy session
    """
    with axai_test_db.session_scope() as session:
        yield session


@pytest.fixture(scope="function")
def axai_reset_db(axai_test_db: DatabaseInitializer):
    """
    Function-scoped fixture to reset the database to a clean state.

    This fixture can be used as a parameter to force a database reset
    before a specific test. Useful for tests that need a completely
    clean database state.

    Args:
        axai_test_db: Session-scoped database initializer
    """
    load_sample = os.getenv("AXAI_LOAD_SAMPLE_DATA", "false").lower() == "true"
    axai_test_db.reset_database(load_sample_data=load_sample)


# Markers for test categorization


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "axai_integration: mark test as requiring axai_pg database"
    )
    config.addinivalue_line(
        "markers", "axai_slow: mark test as slow (uses database resets)"
    )
