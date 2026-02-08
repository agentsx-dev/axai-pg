"""
Integration tests for SQLAlchemy-based schema creation.

These tests verify that the SQLAlchemy models create the correct database schema
with all PostgreSQL-specific features (extensions, triggers, constraints, indexes).
"""

import pytest
from sqlalchemy import text, inspect
from src.axai_pg.data.models import (
    Organization,
    User,
    Document,
)
from src.axai_pg.data.models.collection import VisibilityProfile


@pytest.mark.integration
@pytest.mark.db
class TestSchemaCreation:
    """Test that SQLAlchemy creates the complete database schema correctly."""

    def test_all_tables_exist(self, db_session):
        """Test that all expected tables are created."""
        inspector = inspect(db_session.bind)
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
            "collections",
            "collection_entities",
            "collection_relationships",
            "visibility_profiles",
            "entity_links",
            "entity_operations",
            "document_collection_contexts",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"

    def test_uuid_extension_exists(self, db_session):
        """Test that the uuid-ossp extension is installed."""
        result = db_session.execute(
            text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')"
            )
        )
        assert result.scalar() is True, "uuid-ossp extension should be installed"

    def test_uuid_columns_exist(self, db_session):
        """Test that UUID columns are properly created."""
        inspector = inspect(db_session.bind)

        # Check organizations table - uuid is the primary key
        org_columns = {
            col["name"]: col for col in inspector.get_columns("organizations")
        }
        assert "uuid" in org_columns
        assert "UUID" in str(org_columns["uuid"]["type"])

        # Check users table
        user_columns = {col["name"]: col for col in inspector.get_columns("users")}
        assert "uuid" in user_columns
        assert "UUID" in str(user_columns["uuid"]["type"])
        assert "org_uuid" in user_columns
        assert "UUID" in str(user_columns["org_uuid"]["type"])

    def test_timestamp_trigger_function_exists(self, db_session):
        """Test that the update_modified_column trigger function exists."""
        result = db_session.execute(
            text(
                "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'update_modified_column')"
            )
        )
        assert result.scalar() is True, "update_modified_column function should exist"

    def test_timestamp_triggers_exist(self, db_session):
        """Test that timestamp triggers are created for tables."""
        tables_with_triggers = [
            "organizations",
            "users",
            "documents",
            "summaries",
            "topics",
            "collections",
            "visibility_profiles",
        ]

        for table in tables_with_triggers:
            result = db_session.execute(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname = 'update_{table}_modtime')"
                )
            )
            assert result.scalar() is True, f"Trigger for {table} should exist"

    def test_timestamp_trigger_works(self, test_engine):
        """Test that the timestamp trigger actually updates updated_at.

        Note: This test commits to the database and then cleans up manually,
        because triggers don't fire in the ORM cache - we need to test actual
        database behavior.
        """
        import time
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        # Use a direct session that can commit
        session = Session(test_engine)
        try:
            # Create an organization and commit it
            org = Organization(name="Test Org for Trigger")
            session.add(org)
            session.commit()

            original_updated_at = org.updated_at

            # Wait to ensure timestamp difference
            time.sleep(0.1)

            # Update using ORM and commit
            org.name = "Updated Org for Trigger"
            session.commit()

            # Refresh to get new timestamp from database
            session.refresh(org)

            assert (
                org.updated_at > original_updated_at
            ), f"updated_at should be automatically updated by trigger. Original: {original_updated_at}, New: {org.updated_at}"

        finally:
            # Clean up - delete the test org
            session.execute(
                text("DELETE FROM organizations WHERE name LIKE '%Trigger%'")
            )
            session.commit()
            session.close()

    def test_check_constraint_organizations_name(self, db_session):
        """Test that organizations name check constraint works."""
        # Empty name should fail
        org = Organization(name="   ")  # Only whitespace
        db_session.add(org)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "organizations_name_not_empty" in str(exc_info.value)
            or "check constraint" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_check_constraint_users_email(self, db_session):
        """Test that users email validation check constraint works."""
        # Create org first
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        # Invalid email should fail
        user = User(username="testuser", email="invalid-email", org_uuid=org.uuid)
        db_session.add(user)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "users_email_valid" in str(exc_info.value)
            or "check constraint" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_check_constraint_documents_status(self, db_session):
        """Test that documents status check constraint works."""
        # Create required entities
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Invalid status should fail
        content = "Content"
        doc = Document(
            title="Test",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="invalid_status",  # Not in allowed values
            filename="test.txt",
            file_path="/test/path/test.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(doc)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "documents_valid_status" in str(exc_info.value)
            or "check constraint" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_check_constraint_documents_version(self, db_session):
        """Test that documents version check constraint works."""
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Version <= 0 should fail
        content = "Content"
        doc = Document(
            title="Test",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            version=0,  # Should be > 0
            filename="test.txt",
            file_path="/test/path/test.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(doc)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "documents_valid_version" in str(exc_info.value)
            or "check constraint" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_indexes_exist(self, db_session):
        """Test that performance indexes are created."""
        inspector = inspect(db_session.bind)

        # Check some key indexes exist
        doc_indexes = {idx["name"]: idx for idx in inspector.get_indexes("documents")}

        expected_indexes = [
            "idx_documents_org_uuid",
            "idx_documents_owner_uuid",
            "idx_documents_type",
            "idx_documents_status",
        ]

        for idx_name in expected_indexes:
            assert idx_name in doc_indexes, f"Index {idx_name} should exist"

    def test_foreign_key_constraints_exist(self, db_session):
        """Test that foreign key relationships are properly created."""
        inspector = inspect(db_session.bind)

        # Check users table has FK to organizations
        user_fks = inspector.get_foreign_keys("users")
        assert len(user_fks) > 0, "Users should have foreign keys"
        org_fk = next(
            (fk for fk in user_fks if "organizations" in fk["referred_table"]), None
        )
        assert org_fk is not None, "Users should have FK to organizations"

        # Check documents table has FKs to users and organizations
        doc_fks = inspector.get_foreign_keys("documents")
        assert len(doc_fks) >= 2, "Documents should have multiple foreign keys"

    def test_cascade_delete_works(self, db_session):
        """Test that cascade deletes work properly."""
        # Create organization with user and document
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        content = "Content"
        doc = Document(
            title="Test Doc",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test_doc.txt",
            file_path="/test/path/test_doc.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(doc)
        db_session.commit()

        doc_id = doc.id

        # Delete organization should cascade to users and documents
        db_session.delete(org)
        db_session.commit()

        # Document should be deleted
        deleted_doc = db_session.query(Document).filter_by(id=doc_id).first()
        assert deleted_doc is None, "Document should be cascade deleted"

    def test_unique_constraints_work(self, db_session):
        """Test that unique constraints are enforced."""
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        # Create first user
        user1 = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user1)
        db_session.commit()

        # Try to create user with same username
        user2 = User(
            username="testuser", email="different@example.com", org_uuid=org.uuid
        )
        db_session.add(user2)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "unique" in str(exc_info.value).lower()
            or "duplicate" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_jsonb_columns_work(self, db_session):
        """Test that JSONB columns work properly."""
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create document with JSONB metadata
        content = "Content"
        doc = Document(
            title="Test Doc",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            document_metadata={"key": "value", "nested": {"data": 123}},
            filename="test_doc.txt",
            file_path="/test/path/test_doc.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(doc)
        db_session.commit()

        # Retrieve and verify
        retrieved_doc = db_session.query(Document).filter_by(id=doc.id).first()
        assert retrieved_doc.document_metadata == {
            "key": "value",
            "nested": {"data": 123},
        }

    def test_collection_parent_foreign_key(self, db_session):
        """Test that collection self-referential FK is properly created."""
        inspector = inspect(db_session.bind)

        # Check parent_uuid column exists
        collection_columns = {
            col["name"]: col for col in inspector.get_columns("collections")
        }
        assert (
            "parent_uuid" in collection_columns
        ), "Collections should have parent_uuid column"
        assert "UUID" in str(collection_columns["parent_uuid"]["type"])

        # Check self-referential FK exists
        collection_fks = inspector.get_foreign_keys("collections")
        parent_fk = next(
            (fk for fk in collection_fks if "collections" in fk["referred_table"]), None
        )
        assert parent_fk is not None, "Collections should have self-referential FK"
        assert "parent_uuid" in parent_fk["constrained_columns"]

    def test_visibility_profile_foreign_keys(self, db_session):
        """Test that visibility_profile FKs are properly created."""
        inspector = inspect(db_session.bind)

        # Check file_uuid and collection_uuid columns exist
        vp_columns = {
            col["name"]: col for col in inspector.get_columns("visibility_profiles")
        }
        assert (
            "file_uuid" in vp_columns
        ), "VisibilityProfile should have file_uuid column"
        assert (
            "collection_uuid" in vp_columns
        ), "VisibilityProfile should have collection_uuid column"
        assert "UUID" in str(vp_columns["file_uuid"]["type"])
        assert "UUID" in str(vp_columns["collection_uuid"]["type"])

        # Check FKs exist
        vp_fks = inspector.get_foreign_keys("visibility_profiles")
        file_fk = next(
            (fk for fk in vp_fks if "documents" in fk["referred_table"]), None
        )
        collection_fk = next(
            (fk for fk in vp_fks if "collections" in fk["referred_table"]), None
        )
        assert file_fk is not None, "VisibilityProfile should have FK to documents"
        assert (
            collection_fk is not None
        ), "VisibilityProfile should have FK to collections"

    def test_check_constraint_visibility_profile_type(self, db_session):
        """Test that visibility profile type check constraint works."""
        # Create dependencies
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Invalid profile_type should fail
        profile = VisibilityProfile(
            name="Test Profile",
            owner_uuid=user.uuid,
            profile_type="INVALID_TYPE",  # Not in ('FILE', 'COLLECTION', 'GLOBAL')
        )
        db_session.add(profile)

        with pytest.raises(Exception) as exc_info:
            db_session.commit()

        assert (
            "visibility_profiles_valid_profile_type" in str(exc_info.value)
            or "check constraint" in str(exc_info.value).lower()
        )
        db_session.rollback()

    def test_json_columns_visibility_profile(self, db_session):
        """Test that JSON columns work correctly for visibility profiles."""
        # Create dependencies
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create visibility profile with JSON data
        profile = VisibilityProfile(
            name="Test Profile",
            owner_uuid=user.uuid,
            profile_type="GLOBAL",
            visible_entity_types=["Person", "Organization"],
            all_entities=["Person", "Organization", "Location"],
            enabled_entities=["Person"],
            all_relationships=["works_for", "knows"],
            enabled_relationships=["knows"],
        )
        db_session.add(profile)
        db_session.flush()

        # Retrieve and verify JSON fields
        retrieved_profile = (
            db_session.query(VisibilityProfile).filter_by(id=profile.id).first()
        )
        assert retrieved_profile.visible_entity_types == ["Person", "Organization"]
        assert retrieved_profile.all_entities == ["Person", "Organization", "Location"]
        assert retrieved_profile.enabled_entities == ["Person"]
        assert retrieved_profile.all_relationships == ["works_for", "knows"]
        assert retrieved_profile.enabled_relationships == ["knows"]

    def test_table_comments_exist(self, db_session):
        """Test that table comments are added."""
        result = db_session.execute(
            text(
                """
            SELECT obj_description('organizations'::regclass)
            """
            )
        )
        comment = result.scalar()
        assert comment is not None, "Organizations table should have a comment"
        assert "tenant" in comment.lower() or "b2b" in comment.lower()
