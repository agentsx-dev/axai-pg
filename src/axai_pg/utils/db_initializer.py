"""
Database Initializer Utility

This module provides utilities for initializing, setting up, and tearing down
PostgreSQL databases. It can be used for both testing and production scenarios.

Usage:
    # Testing scenario with automatic cleanup
    with DatabaseInitializer(config) as db_init:
        db_init.setup_database()
        # Run tests

    # Production scenario
    db_init = DatabaseInitializer(config)
    db_init.setup_database(load_sample_data=False)
"""

import os
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from ..data.config.database import (
    DatabaseManager,
    PostgresConnectionConfig,
    PostgresPoolConfig,
    Base,
)
from .schema_builder import PostgreSQLSchemaBuilder

logger = logging.getLogger(__name__)


@dataclass
class DatabaseInitializerConfig:
    """Configuration for database initialization."""

    connection_config: PostgresConnectionConfig
    pool_config: Optional[PostgresPoolConfig] = None
    schema_file: Optional[str] = None
    sample_data_script: Optional[str] = None
    auto_create_db: bool = True
    auto_drop_on_exit: bool = False
    wait_timeout: int = 30
    retry_attempts: int = 5

    def __post_init__(self):
        """Set default paths if not provided."""
        if self.schema_file is None:
            # Default to the schema file in the package
            package_root = Path(__file__).parent.parent.parent.parent
            self.schema_file = str(package_root / "sql" / "schema" / "schema.sql")

        if self.sample_data_script is None:
            package_root = Path(__file__).parent.parent.parent.parent
            self.sample_data_script = str(package_root / "add_sample_data.py")


class DatabaseInitializer:
    """
    Database initialization and management utility.

    This class handles database creation, schema application, sample data loading,
    and cleanup. It can be used as a context manager for automatic cleanup.

    Examples:
        # Testing with automatic cleanup
        config = DatabaseInitializerConfig(
            connection_config=PostgresConnectionConfig.from_env(),
            auto_drop_on_exit=True
        )
        with DatabaseInitializer(config) as db_init:
            db_init.setup_database(load_sample_data=True)
            # Use database for tests

        # Production setup
        config = DatabaseInitializerConfig(
            connection_config=PostgresConnectionConfig.from_env(),
            auto_drop_on_exit=False
        )
        db_init = DatabaseInitializer(config)
        db_init.setup_database(load_sample_data=False)
    """

    def __init__(self, config: DatabaseInitializerConfig):
        """
        Initialize the database initializer.

        Args:
            config: Configuration for database initialization
        """
        self.config = config
        self._engine: Optional[Engine] = None
        self._db_manager: Optional[DatabaseManager] = None
        self._is_setup = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if self.config.auto_drop_on_exit:
            try:
                self.teardown_database()
            except Exception as e:
                logger.error(f"Error during database teardown: {e}")
        return False

    def _get_admin_engine(self) -> Engine:
        """
        Get an engine connected to the postgres database (for admin operations).

        Returns:
            SQLAlchemy engine connected to postgres database
        """
        conn_config = self.config.connection_config
        admin_url = (
            f"postgresql://{conn_config.username}:{conn_config.password}@"
            f"{conn_config.host}:{conn_config.port}/postgres"
        )
        return create_engine(admin_url, isolation_level="AUTOCOMMIT")

    def _wait_for_database(self) -> bool:
        """
        Wait for PostgreSQL to be ready.

        Returns:
            True if database is ready, False otherwise
        """
        logger.info("Waiting for PostgreSQL to be ready...")

        for attempt in range(self.config.retry_attempts):
            try:
                admin_engine = self._get_admin_engine()
                with admin_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("PostgreSQL is ready!")
                admin_engine.dispose()
                return True
            except OperationalError as e:
                if attempt < self.config.retry_attempts - 1:
                    wait_time = min(2**attempt, 10)  # Exponential backoff, max 10s
                    logger.warning(
                        f"PostgreSQL not ready (attempt {attempt + 1}/{self.config.retry_attempts}). "
                        f"Waiting {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("PostgreSQL did not become ready in time")
                    return False

        return False

    def _database_exists(self) -> bool:
        """
        Check if the target database exists.

        Returns:
            True if database exists, False otherwise
        """
        try:
            admin_engine = self._get_admin_engine()
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": self.config.connection_config.database},
                )
                exists = result.scalar() is not None
            admin_engine.dispose()
            return exists
        except Exception as e:
            logger.error(f"Error checking database existence: {e}")
            return False

    def create_database(self) -> bool:
        """
        Create the database if it doesn't exist.

        Returns:
            True if database was created or already exists, False on error
        """
        if not self._wait_for_database():
            return False

        db_name = self.config.connection_config.database

        if self._database_exists():
            logger.info(f"Database '{db_name}' already exists")
            return True

        try:
            logger.info(f"Creating database '{db_name}'...")
            admin_engine = self._get_admin_engine()
            with admin_engine.connect() as conn:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            admin_engine.dispose()
            logger.info(f"Database '{db_name}' created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            return False

    def drop_database(self) -> bool:
        """
        Drop the database if it exists.

        Returns:
            True if database was dropped or doesn't exist, False on error
        """
        if not self._wait_for_database():
            return False

        db_name = self.config.connection_config.database

        if not self._database_exists():
            logger.info(f"Database '{db_name}' does not exist")
            return True

        try:
            logger.info(f"Dropping database '{db_name}'...")

            # Terminate existing connections
            admin_engine = self._get_admin_engine()
            with admin_engine.connect() as conn:
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pg_stat_activity.pid) "
                        "FROM pg_stat_activity "
                        "WHERE pg_stat_activity.datname = :dbname "
                        "AND pid <> pg_backend_pid()"
                    ),
                    {"dbname": db_name},
                )

                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
            admin_engine.dispose()
            logger.info(f"Database '{db_name}' dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Error dropping database: {e}")
            return False

    def apply_schema(
        self, schema_file: Optional[str] = None, use_sqlalchemy: bool = True
    ) -> bool:
        """
        Apply database schema using SQLAlchemy models or SQL file.

        Args:
            schema_file: Path to schema SQL file (for backward compatibility)
            use_sqlalchemy: If True, use SQLAlchemy models. If False, use SQL file.

        Returns:
            True if schema was applied successfully, False otherwise
        """
        if use_sqlalchemy:
            logger.info("Applying schema using SQLAlchemy models...")
            try:
                conn_config = self.config.connection_config
                db_url = (
                    f"postgresql://{conn_config.username}:{conn_config.password}@"
                    f"{conn_config.host}:{conn_config.port}/{conn_config.database}"
                )

                engine = create_engine(db_url)

                # Use PostgreSQLSchemaBuilder to create complete schema
                # Note: build_complete_schema now raises exceptions instead of returning bool
                PostgreSQLSchemaBuilder.build_complete_schema(engine)

                engine.dispose()

                logger.info("Schema applied successfully using SQLAlchemy")
                return True

            except Exception as e:
                logger.error(f"Error applying schema with SQLAlchemy: {e}")
                return False
        else:
            # Fallback to SQL file approach (for backward compatibility)
            schema_path = schema_file or self.config.schema_file

            if not schema_path or not Path(schema_path).exists():
                logger.error(f"Schema file not found: {schema_path}")
                return False

            logger.info(f"Applying schema from SQL file {schema_path}...")

            try:
                with open(schema_path, "r") as f:
                    schema_sql = f.read()

                conn_config = self.config.connection_config
                db_url = (
                    f"postgresql://{conn_config.username}:{conn_config.password}@"
                    f"{conn_config.host}:{conn_config.port}/{conn_config.database}"
                )

                engine = create_engine(db_url)
                with engine.connect() as conn:
                    # Execute schema in a transaction
                    trans = conn.begin()
                    try:
                        # Split by semicolon and execute each statement
                        statements = [
                            s.strip() for s in schema_sql.split(";") if s.strip()
                        ]
                        for statement in statements:
                            if statement:
                                conn.execute(text(statement))
                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        raise e

                engine.dispose()
                logger.info("Schema applied successfully from SQL file")
                return True
            except Exception as e:
                logger.error(f"Error applying schema from SQL file: {e}")
                return False

    def load_sample_data(self, script_path: Optional[str] = None) -> bool:
        """
        Load sample data using Python script.

        Args:
            script_path: Path to sample data script. Uses config default if not provided.

        Returns:
            True if sample data was loaded successfully, False otherwise
        """
        script = script_path or self.config.sample_data_script

        if not script or not Path(script).exists():
            logger.warning(f"Sample data script not found: {script}")
            return False

        logger.info(f"Loading sample data from {script}...")

        try:
            # Set environment variables for the script
            env = os.environ.copy()
            env.update(
                {
                    "POSTGRES_HOST": self.config.connection_config.host,
                    "POSTGRES_PORT": str(self.config.connection_config.port),
                    "POSTGRES_DB": self.config.connection_config.database,
                    "POSTGRES_USER": self.config.connection_config.username,
                    "POSTGRES_PASSWORD": self.config.connection_config.password,
                }
            )

            result = subprocess.run(
                ["python", script], env=env, capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                logger.info("Sample data loaded successfully")
                return True
            else:
                logger.error(f"Error loading sample data: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error loading sample data: {e}")
            return False

    def setup_database(
        self, load_sample_data: bool = False, apply_schema: bool = True
    ) -> bool:
        """
        Complete database setup: create database, apply schema, optionally load data.

        Args:
            load_sample_data: Whether to load sample data after schema application
            apply_schema: Whether to apply the schema (set False if schema already exists)

        Returns:
            True if setup was successful, False otherwise
        """
        logger.info("Starting database setup...")

        # Create database if configured to do so
        if self.config.auto_create_db:
            if not self.create_database():
                return False

        # Apply schema
        if apply_schema:
            if not self.apply_schema():
                return False

        # Load sample data if requested
        if load_sample_data:
            if not self.load_sample_data():
                logger.warning("Sample data loading failed, but continuing...")

        # Initialize DatabaseManager
        try:
            DatabaseManager.initialize(
                self.config.connection_config, self.config.pool_config
            )
            self._db_manager = DatabaseManager.get_instance()
            self._is_setup = True
            logger.info("Database setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing DatabaseManager: {e}")
            return False

    def teardown_database(self) -> bool:
        """
        Teardown database: close connections and optionally drop database.

        Returns:
            True if teardown was successful, False otherwise
        """
        logger.info("Starting database teardown...")

        # Close database manager connections
        if self._db_manager and self._db_manager._engine:
            self._db_manager._engine.dispose()

        # Drop database if configured to do so
        if self.config.auto_drop_on_exit:
            if not self.drop_database():
                return False

        self._is_setup = False
        logger.info("Database teardown completed successfully")
        return True

    def reset_database(self, load_sample_data: bool = False) -> bool:
        """
        Reset database: drop, recreate, and setup.

        Args:
            load_sample_data: Whether to load sample data after reset

        Returns:
            True if reset was successful, False otherwise
        """
        logger.info("Resetting database...")

        if not self.drop_database():
            return False

        if not self.setup_database(load_sample_data=load_sample_data):
            return False

        logger.info("Database reset completed successfully")
        return True

    def get_connection_config(self) -> PostgresConnectionConfig:
        """
        Get the connection configuration.

        Returns:
            PostgresConnectionConfig instance
        """
        return self.config.connection_config

    def get_database_manager(self) -> DatabaseManager:
        """
        Get the initialized DatabaseManager instance.

        Returns:
            DatabaseManager instance

        Raises:
            RuntimeError: If database is not set up
        """
        if not self._is_setup or not self._db_manager:
            raise RuntimeError("Database not set up. Call setup_database() first.")
        return self._db_manager

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations.

        Yields:
            Database session

        Raises:
            RuntimeError: If database is not set up
        """
        db_manager = self.get_database_manager()
        with db_manager.session_scope() as session:
            yield session
