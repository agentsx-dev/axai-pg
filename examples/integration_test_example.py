"""
Integration Test Examples for External Systems

This file demonstrates how external systems can use axai_pg for integration testing.
It shows multiple approaches: programmatic usage, pytest fixtures, and custom setups.

Prerequisites:
1. Install axai-pg with testing extras: pip install axai-pg[testing]
2. Start PostgreSQL: docker-compose -f docker-compose.standalone-test.yml up -d
3. Set environment variables or use defaults (see below)
"""

import os
import pytest
from axai_pg.utils.db_initializer import DatabaseInitializer, DatabaseInitializerConfig
from axai_pg.data.config.database import PostgresConnectionConfig
from axai_pg.data.models import Organization, User, Document


# =============================================================================
# Example 1: Programmatic Usage with Context Manager
# =============================================================================

def test_programmatic_with_context_manager():
    """
    Example: Using DatabaseInitializer programmatically with context manager.

    This approach is useful for:
    - Custom test setups
    - One-off integration tests
    - Non-pytest testing frameworks
    """
    # Configure connection
    conn_config = PostgresConnectionConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database='test_integration_db',  # Use unique DB name
        username=os.getenv('POSTGRES_USER', 'test_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'test_password'),
    )

    # Configure initializer
    db_config = DatabaseInitializerConfig(
        connection_config=conn_config,
        auto_create_db=True,
        auto_drop_on_exit=True,  # Cleanup automatically
        wait_timeout=30,
        retry_attempts=5
    )

    # Use context manager for automatic cleanup
    with DatabaseInitializer(db_config) as db_init:
        # Setup database with schema
        assert db_init.setup_database(load_sample_data=False)

        # Perform your integration tests
        with db_init.session_scope() as session:
            # Create test data
            org = Organization(name="Test Org")
            session.add(org)
            session.flush()

            user = User(username="testuser", email="test@example.com", org_id=org.id)
            session.add(user)
            session.commit()

            # Query and verify
            saved_user = session.query(User).filter_by(username="testuser").first()
            assert saved_user is not None
            assert saved_user.email == "test@example.com"

    # Database is automatically dropped after context manager exits
    print("✓ Programmatic test with context manager completed")


# =============================================================================
# Example 2: Manual Database Lifecycle Management
# =============================================================================

def test_manual_lifecycle():
    """
    Example: Manually managing database lifecycle.

    This approach gives you full control over when setup and teardown occur.
    Useful for complex test scenarios.
    """
    conn_config = PostgresConnectionConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database='test_manual_db',
        username=os.getenv('POSTGRES_USER', 'test_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'test_password'),
    )

    db_config = DatabaseInitializerConfig(
        connection_config=conn_config,
        auto_create_db=True,
        auto_drop_on_exit=False,  # Manual control
    )

    db_init = DatabaseInitializer(db_config)

    try:
        # Setup
        assert db_init.setup_database(load_sample_data=False)

        # Run tests
        with db_init.session_scope() as session:
            org = Organization(name="Manual Test Org")
            session.add(org)
            session.commit()

            assert session.query(Organization).count() == 1

        print("✓ Manual lifecycle test completed")

    finally:
        # Always cleanup
        db_init.teardown_database()


# =============================================================================
# Example 3: Using Pytest Fixtures (Recommended)
# =============================================================================

# Import fixtures from axai_pg
from axai_pg.testing.fixtures import axai_db_session, axai_test_db


@pytest.mark.axai_integration
def test_with_pytest_fixture(axai_db_session):
    """
    Example: Using pytest fixtures for clean, isolated tests.

    This is the recommended approach for most integration tests.
    Benefits:
    - Automatic database setup/teardown
    - Session isolation (rollback after each test)
    - Minimal boilerplate
    """
    # Create test data
    org = Organization(name="Pytest Fixture Org")
    axai_db_session.add(org)
    axai_db_session.flush()

    user = User(
        username="fixtureuser",
        email="fixture@example.com",
        org_id=org.id
    )
    axai_db_session.add(user)
    axai_db_session.commit()

    # Query and verify
    saved_user = axai_db_session.query(User).filter_by(username="fixtureuser").first()
    assert saved_user is not None
    assert saved_user.email == "fixture@example.com"

    # Session automatically rolls back after test
    print("✓ Pytest fixture test completed")


@pytest.mark.axai_integration
def test_with_multiple_operations(axai_db_session):
    """
    Example: More complex test with multiple related entities.
    """
    # Create organization
    org = Organization(name="Complex Test Org")
    axai_db_session.add(org)
    axai_db_session.flush()

    # Create users
    user1 = User(username="user1", email="user1@example.com", org_id=org.id)
    user2 = User(username="user2", email="user2@example.com", org_id=org.id)
    axai_db_session.add_all([user1, user2])
    axai_db_session.flush()

    # Create documents
    doc1 = Document(
        title="Doc 1",
        content="Content 1",
        owner_id=user1.id,
        org_id=org.id,
        document_type="text",
        status="draft"
    )
    doc2 = Document(
        title="Doc 2",
        content="Content 2",
        owner_id=user2.id,
        org_id=org.id,
        document_type="text",
        status="published"
    )
    axai_db_session.add_all([doc1, doc2])
    axai_db_session.commit()

    # Verify relationships
    assert axai_db_session.query(User).filter_by(org_id=org.id).count() == 2
    assert axai_db_session.query(Document).filter_by(org_id=org.id).count() == 2
    assert doc1.owner_id == user1.id
    assert doc2.owner_id == user2.id

    print("✓ Complex operations test completed")


# =============================================================================
# Example 4: Custom Test Configuration
# =============================================================================

def test_with_sqlalchemy_schema():
    """
    Example: Using SQLAlchemy models for schema creation.

    Schema is created programmatically from SQLAlchemy models.
    """
    conn_config = PostgresConnectionConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database='test_sqlalchemy_schema',
        username=os.getenv('POSTGRES_USER', 'test_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'test_password'),
    )

    db_config = DatabaseInitializerConfig(
        connection_config=conn_config,
        auto_create_db=True,
        auto_drop_on_exit=True,
    )

    with DatabaseInitializer(db_config) as db_init:
        # Schema is created from SQLAlchemy models automatically
        assert db_init.setup_database()

        with db_init.session_scope() as session:
            from sqlalchemy import text
            # Verify schema was applied
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        print("✓ SQLAlchemy schema test completed")


# =============================================================================
# Example 5: Database Reset Between Tests
# =============================================================================

def test_database_reset():
    """
    Example: Resetting database to clean state during test.

    Useful for tests that need a completely fresh database.
    """
    conn_config = PostgresConnectionConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432')),
        database='test_reset_db',
        username=os.getenv('POSTGRES_USER', 'test_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'test_password'),
    )

    db_config = DatabaseInitializerConfig(
        connection_config=conn_config,
        auto_create_db=True,
        auto_drop_on_exit=True,
    )

    with DatabaseInitializer(db_config) as db_init:
        # Initial setup
        assert db_init.setup_database()

        # Add some data
        with db_init.session_scope() as session:
            org = Organization(name="Before Reset")
            session.add(org)
            session.commit()

        # Reset database (drops and recreates)
        assert db_init.reset_database()

        # Verify database is clean
        with db_init.session_scope() as session:
            count = session.query(Organization).count()
            assert count == 0, "Database should be empty after reset"

        print("✓ Database reset test completed")


# =============================================================================
# Running the Examples
# =============================================================================

if __name__ == "__main__":
    """
    Run examples directly without pytest.

    Usage:
        python examples/integration_test_example.py

    Or run with pytest:
        pytest examples/integration_test_example.py -v
    """
    print("Running integration test examples...\n")

    # Run non-pytest examples
    try:
        test_programmatic_with_context_manager()
        test_manual_lifecycle()
        test_with_sqlalchemy_schema()
        test_database_reset()

        print("\n✅ All non-pytest examples completed successfully!")
        print("\nTo run pytest examples:")
        print("  pytest examples/integration_test_example.py -v -m axai_integration")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        raise
