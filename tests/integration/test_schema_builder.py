"""
Integration tests for PostgreSQLSchemaBuilder.

These tests verify that the PostgreSQLSchemaBuilder class correctly creates
and manages PostgreSQL-specific schema features (extensions, triggers, indexes, etc.).
"""

import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from src.axai_pg.utils.schema_builder import PostgreSQLSchemaBuilder


@pytest.mark.integration
@pytest.mark.db
class TestPostgreSQLSchemaBuilder:
    """Test the PostgreSQLSchemaBuilder class."""

    def test_build_complete_schema_success(self, test_engine):
        """Test that build_complete_schema creates all schema elements successfully."""
        # Drop existing schema to start fresh
        PostgreSQLSchemaBuilder.drop_complete_schema(test_engine)

        # Build complete schema
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Verify tables exist
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert len(tables) > 0, "Should have created tables"
        assert "organizations" in tables
        assert "users" in tables
        assert "documents" in tables

        # Verify extension exists
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')"
                )
            )
            assert result.scalar() is True, "uuid-ossp extension should exist"
            conn.commit()

        # Verify trigger function exists
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'update_modified_column')"
                )
            )
            assert (
                result.scalar() is True
            ), "update_modified_column function should exist"
            conn.commit()

    def test_build_schema_is_idempotent(self, test_engine):
        """Test that build_complete_schema can run multiple times safely."""
        # Build schema twice - should not fail
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Verify schema still intact
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "organizations" in tables
        assert "users" in tables

    def test_drop_complete_schema(self, test_engine):
        """Test that drop_complete_schema removes all tables and functions."""
        # Ensure schema exists first
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Drop schema
        PostgreSQLSchemaBuilder.drop_complete_schema(test_engine)

        # Verify tables are gone
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert len(tables) == 0, "All tables should be dropped"

        # Verify trigger function is gone
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'update_modified_column')"
                )
            )
            assert (
                result.scalar() is False
            ), "update_modified_column function should be dropped"
            conn.commit()

        # Rebuild for other tests
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

    def test_create_extensions(self, test_engine):
        """Test that create_extensions installs uuid-ossp extension."""
        # Drop extension if exists
        with test_engine.connect() as conn:
            conn.execute(text('DROP EXTENSION IF EXISTS "uuid-ossp"'))
            conn.commit()

        # Create extensions
        PostgreSQLSchemaBuilder.create_extensions(test_engine)

        # Verify extension exists
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')"
                )
            )
            assert result.scalar() is True, "uuid-ossp extension should be created"
            conn.commit()

    def test_create_update_timestamp_trigger(self, test_engine):
        """Test that create_update_timestamp_trigger creates the function."""
        # Drop function if exists
        with test_engine.connect() as conn:
            conn.execute(
                text("DROP FUNCTION IF EXISTS update_modified_column() CASCADE")
            )
            conn.commit()

        # Create trigger function
        PostgreSQLSchemaBuilder.create_update_timestamp_trigger(test_engine)

        # Verify function exists
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'update_modified_column')"
                )
            )
            assert (
                result.scalar() is True
            ), "update_modified_column function should exist"

            # Verify function returns trigger
            result = conn.execute(
                text(
                    "SELECT prorettype::regtype::text FROM pg_proc WHERE proname = 'update_modified_column'"
                )
            )
            return_type = result.scalar()
            assert return_type == "trigger", "Function should return trigger type"
            conn.commit()

    def test_create_table_triggers(self, test_engine):
        """Test that create_table_triggers adds triggers to tables."""
        # Ensure tables and function exist
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Drop triggers
        with test_engine.connect() as conn:
            conn.execute(
                text(
                    "DROP TRIGGER IF EXISTS update_organizations_modtime ON organizations"
                )
            )
            conn.execute(text("DROP TRIGGER IF EXISTS update_users_modtime ON users"))
            conn.commit()

        # Create triggers
        PostgreSQLSchemaBuilder.create_table_triggers(test_engine)

        # Verify triggers exist
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = 'update_organizations_modtime')"
                )
            )
            assert result.scalar() is True, "organizations trigger should exist"

            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_modtime')"
                )
            )
            assert result.scalar() is True, "users trigger should exist"
            conn.commit()

    def test_add_table_comments(self, test_engine):
        """Test that add_table_comments adds descriptions to tables."""
        # Ensure tables exist
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Clear existing comments
        with test_engine.connect() as conn:
            conn.execute(text("COMMENT ON TABLE organizations IS NULL"))
            conn.execute(text("COMMENT ON TABLE users IS NULL"))
            conn.commit()

        # Add comments
        PostgreSQLSchemaBuilder.add_table_comments(test_engine)

        # Verify comments exist
        with test_engine.connect() as conn:
            result = conn.execute(
                text("SELECT obj_description('organizations'::regclass)")
            )
            org_comment = result.scalar()
            assert org_comment is not None, "organizations should have a comment"
            assert "tenant" in org_comment.lower() or "b2b" in org_comment.lower()

            result = conn.execute(text("SELECT obj_description('users'::regclass)"))
            user_comment = result.scalar()
            assert user_comment is not None, "users should have a comment"
            conn.commit()

    def test_create_performance_indexes(self, test_engine):
        """Test that create_performance_indexes creates additional indexes."""
        # Ensure tables exist
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Drop some performance indexes
        with test_engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS idx_documents_org_status"))
            conn.execute(text("DROP INDEX IF EXISTS idx_users_org"))
            conn.commit()

        # Create indexes
        PostgreSQLSchemaBuilder.create_performance_indexes(test_engine)

        # Verify indexes exist
        inspector = inspect(test_engine)
        doc_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
        assert (
            "idx_documents_org_status" in doc_indexes
        ), "documents org_status index should exist"

        user_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        assert "idx_users_org" in user_indexes, "users org index should exist"

    def test_schema_builder_with_empty_database(self, test_engine):
        """Test that schema builder works starting from completely empty database."""
        # Drop everything
        PostgreSQLSchemaBuilder.drop_complete_schema(test_engine)

        # Verify empty
        inspector = inspect(test_engine)
        assert len(inspector.get_table_names()) == 0

        # Build from scratch
        PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

        # Verify complete schema
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "organizations",
            "users",
            "documents",
            "document_versions",
            "summaries",
            "topics",
            "document_topics",
            "graph_entities",
            "graph_relationships",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"

    def test_schema_builder_error_propagation(self, test_engine):
        """Test that schema builder propagates errors instead of swallowing them."""
        from unittest.mock import patch

        # Mock Base.metadata.create_all to raise an exception
        with patch(
            "src.axai_pg.data.config.database.Base.metadata.create_all"
        ) as mock_create:
            mock_create.side_effect = SQLAlchemyError("Test error")

            # Should raise the exception, not return False
            with pytest.raises(SQLAlchemyError) as exc_info:
                PostgreSQLSchemaBuilder.build_complete_schema(test_engine)

            assert "Test error" in str(exc_info.value)
