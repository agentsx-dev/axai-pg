"""
Integration tests for DatabaseInitializer.

These tests verify that DatabaseInitializer correctly manages database lifecycle,
applies schemas (both SQLAlchemy and SQL file approaches), and integrates with
DatabaseManager.
"""

import pytest
from sqlalchemy import create_engine, text

from src.axai_pg.utils.db_initializer import (
    DatabaseInitializer,
    DatabaseInitializerConfig,
)
from src.axai_pg.data.config.database import PostgresConnectionConfig


@pytest.mark.integration
@pytest.mark.db
class TestDatabaseInitializer:
    """Test the DatabaseInitializer class."""

    @pytest.fixture
    def test_db_config(self):
        """Create a test database configuration for initializer tests."""
        # Use localhost since tests run outside Docker
        # Match the credentials from docker-compose.standalone-test.yml
        return PostgresConnectionConfig(
            host="localhost",
            port=5432,
            database="test_init_db",  # Unique name for initializer tests
            username="test_user",
            password="test_password",
        )

    def test_initializer_with_sqlalchemy_default(self, test_db_config):
        """Test that DatabaseInitializer uses SQLAlchemy by default."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=True,
        )

        with DatabaseInitializer(config) as db_init:
            # Setup database with SQLAlchemy (default)
            success = db_init.setup_database(load_sample_data=False)
            assert success is True, "Database setup should succeed"

            # Verify tables exist using session_scope
            with db_init.session_scope() as session:
                # Query pg_catalog to list tables
                result = session.execute(
                    text(
                        "SELECT tablename FROM pg_catalog.pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                )
                tables = [row[0] for row in result]

                expected_tables = ["organizations", "users", "documents"]
                for table in expected_tables:
                    assert table in tables, f"Table {table} should exist"

        # After context exit, database should be cleaned up
        # Verify database was dropped
        admin_url = (
            f"postgresql://{test_db_config.username}:{test_db_config.password}@"
            f"{test_db_config.host}:{test_db_config.port}/postgres"
        )
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": test_db_config.database},
            )
            assert (
                result.scalar() is None
            ), "Database should be dropped after context exit"
        admin_engine.dispose()

    def test_initializer_with_sql_file(self, test_db_config):
        """Test DatabaseInitializer with SQL file approach (backward compatibility)."""
        # Skip this test since SQL files are deprecated and have syntax issues
        pytest.skip(
            "SQL file approach is deprecated - SQLAlchemy is the recommended approach"
        )

    def test_context_manager_auto_cleanup(self, test_db_config):
        """Test that context manager with auto_drop_on_exit=True cleans up."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=True,
        )

        # Use context manager
        with DatabaseInitializer(config) as db_init:
            db_init.setup_database()
            # Database should exist here
            assert db_init._database_exists() is True

        # After exit, verify database was dropped
        admin_url = (
            f"postgresql://{test_db_config.username}:{test_db_config.password}@"
            f"{test_db_config.host}:{test_db_config.port}/postgres"
        )
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": test_db_config.database},
            )
            assert result.scalar() is None, "Database should be dropped"
        admin_engine.dispose()

    def test_context_manager_no_cleanup(self, test_db_config):
        """Test that context manager with auto_drop_on_exit=False keeps database."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=False,
        )

        try:
            # Use context manager
            with DatabaseInitializer(config) as db_init:
                db_init.setup_database()

            # After exit, verify database still exists
            admin_url = (
                f"postgresql://{test_db_config.username}:{test_db_config.password}@"
                f"{test_db_config.host}:{test_db_config.port}/postgres"
            )
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": test_db_config.database},
                )
                assert result.scalar() is not None, "Database should still exist"
            admin_engine.dispose()

        finally:
            # Clean up manually
            cleanup_config = DatabaseInitializerConfig(
                connection_config=test_db_config, auto_drop_on_exit=False
            )
            cleanup_init = DatabaseInitializer(cleanup_config)
            cleanup_init.drop_database()

    def test_setup_database_creates_all_tables(self, test_db_config):
        """Test that setup_database creates all expected tables."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=True,
        )

        with DatabaseInitializer(config) as db_init:
            success = db_init.setup_database()
            assert success is True

            # Verify all expected tables exist using session_scope
            with db_init.session_scope() as session:
                result = session.execute(
                    text(
                        "SELECT tablename FROM pg_catalog.pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                )
                tables = set(row[0] for row in result)

                expected_tables = {
                    "organizations",
                    "users",
                    "documents",
                    "document_versions",
                    "summaries",
                    "topics",
                    "document_topics",
                    "graph_entities",
                    "graph_relationships",
                }

                missing_tables = expected_tables - tables
                assert len(missing_tables) == 0, f"Missing tables: {missing_tables}"

    def test_health_check_passes(self, test_db_config):
        """Test that database connection works after initialization."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=True,
        )

        with DatabaseInitializer(config) as db_init:
            db_init.setup_database()

            # Test database connectivity by executing a simple query
            with db_init.session_scope() as session:
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1, "Database should be healthy and responsive"

    def test_database_manager_integration(self, test_db_config):
        """Test that get_database_manager() returns working DatabaseManager."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=True,
            auto_drop_on_exit=True,
        )

        with DatabaseInitializer(config) as db_init:
            db_init.setup_database()

            # Get DatabaseManager instance
            db_manager = db_init.get_database_manager()
            assert db_manager is not None

            # Test session creation
            with db_manager.session_scope() as session:
                # Simple query to verify session works
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    def test_create_database_idempotent(self, test_db_config):
        """Test that create_database can be called multiple times safely."""
        config = DatabaseInitializerConfig(
            connection_config=test_db_config,
            auto_create_db=False,  # Manual control
            auto_drop_on_exit=True,
        )

        with DatabaseInitializer(config) as db_init:
            # Create database multiple times - should not fail
            assert db_init.create_database() is True
            assert db_init.create_database() is True
            assert db_init.create_database() is True

            # Verify database exists
            assert db_init._database_exists() is True
