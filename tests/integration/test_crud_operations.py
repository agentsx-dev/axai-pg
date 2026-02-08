"""
Integration tests for CRUD operations.

These tests verify that all model CRUD operations work correctly with a real
PostgreSQL database, including relationships and queries.
"""

import pytest
import uuid
from axai_pg import (
    Organization,
    User,
    Document,
    Summary,
    Topic,
    DocumentTopic,
    Collection,
    VisibilityProfile,
)


@pytest.mark.integration
@pytest.mark.db
class TestCRUDOperations:
    """Test CRUD operations for all models."""

    def test_create_organization_and_user(self, db_session):
        """Test creating organization and user with relationships."""
        # Create organization
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.flush()

        assert org.uuid is not None
        assert isinstance(org.uuid, uuid.UUID)
        assert org.id is not None  # 8-char string ID
        assert isinstance(org.id, str)
        assert len(org.id) == 8
        assert org.name == "Test Organization"

        # Create user
        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        assert user.uuid is not None
        assert isinstance(user.uuid, uuid.UUID)
        assert isinstance(user.org_uuid, uuid.UUID)
        assert user.org_uuid == org.uuid
        assert user.username == "testuser"

        # Verify relationship
        assert user.organization.uuid == org.uuid
        assert org.users.first().uuid == user.uuid

    def test_create_document_with_summary(self, db_session):
        """Test creating document with summary and relationships."""
        # Create organization and user first
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create document
        content = "This is a test document content"
        document = Document(
            title="Test Document",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test_document.txt",
            file_path="/test/path/test_document.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        assert document.id is not None
        assert isinstance(document.uuid, uuid.UUID)
        assert isinstance(document.owner_uuid, uuid.UUID)
        assert isinstance(document.org_uuid, uuid.UUID)
        assert document.owner_uuid == user.uuid
        assert document.org_uuid == org.uuid

        # Create summary
        summary = Summary(
            document_uuid=document.uuid,
            content="This is a summary of the test document",
            summary_type="abstract",
            tool_agent="test-agent",
            confidence_score=0.95,
        )
        db_session.add(summary)
        db_session.flush()

        assert summary.id is not None
        assert isinstance(summary.uuid, uuid.UUID)
        assert isinstance(summary.document_uuid, uuid.UUID)
        assert summary.document_uuid == document.uuid
        assert summary.confidence_score == 0.95

    def test_create_topic_and_associate_with_document(self, db_session):
        """Test creating topic and associating with document via junction table."""
        # Create organization, user, and document
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        content = "This is a test document content"
        document = Document(
            title="Test Document",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test_document.txt",
            file_path="/test/path/test_document.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        # Create topic
        topic = Topic(
            name="Test Topic",
            description="A test topic",
            keywords=["test", "example"],
            extraction_method="manual",
            global_importance=0.8,
        )
        db_session.add(topic)
        db_session.flush()

        assert topic.id is not None
        assert isinstance(topic.uuid, uuid.UUID)
        assert topic.name == "Test Topic"
        assert topic.keywords == ["test", "example"]

        # Verify document-topic relationship
        doc_topic = DocumentTopic(
            document_uuid=document.uuid,
            topic_uuid=topic.uuid,
            relevance_score=0.9,
            extracted_by_tool="test-tool",
        )
        db_session.add(doc_topic)
        db_session.flush()

        assert doc_topic.id is not None
        assert isinstance(doc_topic.uuid, uuid.UUID)
        assert isinstance(doc_topic.document_uuid, uuid.UUID)
        assert isinstance(doc_topic.topic_uuid, uuid.UUID)
        assert doc_topic.document_uuid == document.uuid
        assert doc_topic.topic_uuid == topic.uuid
        assert doc_topic.relevance_score == 0.9

    def test_query_operations(self, db_session):
        """Test various query operations on models."""
        # Create test data
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        content = "This is a test document content"
        document = Document(
            title="Test Document",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test_document.txt",
            file_path="/test/path/test_document.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        # Test queries
        # Get organization by name
        queried_org = db_session.query(Organization).filter_by(name="Test Org").first()
        assert queried_org.uuid == org.uuid
        assert isinstance(queried_org.uuid, uuid.UUID)

        # Get user by username
        queried_user = db_session.query(User).filter_by(username="testuser").first()
        assert queried_user.uuid == user.uuid
        assert isinstance(queried_user.uuid, uuid.UUID)

        # Get documents for organization
        org_documents = db_session.query(Document).filter_by(org_uuid=org.uuid).all()
        assert len(org_documents) == 1
        assert org_documents[0].uuid == document.uuid
        assert isinstance(org_documents[0].uuid, uuid.UUID)

        # Get documents owned by user
        user_documents = (
            db_session.query(Document).filter_by(owner_uuid=user.uuid).all()
        )
        assert len(user_documents) == 1
        assert user_documents[0].uuid == document.uuid
        assert isinstance(user_documents[0].uuid, uuid.UUID)

    def test_update_user(self, db_session):
        """Test updating user fields."""
        # Create organization and user
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(
            username="original_username",
            email="original@example.com",
            org_uuid=org.uuid,
        )
        db_session.add(user)
        db_session.flush()

        original_id = user.id

        # Update user
        user.username = "updated_username"
        user.email = "updated@example.com"
        db_session.flush()

        # Verify updates persisted
        updated_user = db_session.query(User).filter_by(id=original_id).first()
        assert updated_user.id == original_id
        assert updated_user.username == "updated_username"
        assert updated_user.email == "updated@example.com"
        assert updated_user.org_uuid == org.uuid  # Foreign key unchanged

    def test_update_document_status(self, db_session):
        """Test updating document status and content."""
        # Create organization, user, and document
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        original_content = "Original content"
        document = Document(
            title="Original Title",
            content=original_content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="original.txt",
            file_path="/test/path/original.txt",
            size=len(original_content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        original_id = document.id

        # Update document
        document.title = "Updated Title"
        document.content = "Updated content with more information"
        document.status = "published"
        db_session.flush()

        # Verify updates persisted
        updated_doc = db_session.query(Document).filter_by(id=original_id).first()
        assert updated_doc.id == original_id
        assert updated_doc.title == "Updated Title"
        assert updated_doc.content == "Updated content with more information"
        assert updated_doc.status == "published"
        assert updated_doc.owner_uuid == user.uuid  # Foreign key unchanged
        assert updated_doc.org_uuid == org.uuid  # Foreign key unchanged

    def test_create_collection_with_hierarchy(self, db_session):
        """Test creating hierarchical collections with parent-child relationships."""
        # Create organization and user
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create root collection
        root_collection = Collection(
            name="Root Collection",
            description="Top level collection",
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            parent_uuid=None,  # No parent - this is root
            is_deleted=False,
        )
        db_session.add(root_collection)
        db_session.flush()

        assert root_collection.id is not None
        assert isinstance(root_collection.uuid, uuid.UUID)
        assert root_collection.parent_uuid is None
        assert root_collection.is_deleted is False
        assert root_collection.deleted_at is None

        # Create child collection
        child_collection = Collection(
            name="Child Collection",
            description="Nested collection",
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            parent_uuid=root_collection.uuid,
            is_deleted=False,
        )
        db_session.add(child_collection)
        db_session.flush()

        assert child_collection.id is not None
        assert isinstance(child_collection.uuid, uuid.UUID)
        assert isinstance(child_collection.parent_uuid, uuid.UUID)
        assert child_collection.parent_uuid == root_collection.uuid

        # Verify relationships
        assert child_collection.parent.uuid == root_collection.uuid
        assert root_collection.subcollections.first().uuid == child_collection.uuid
        assert root_collection.owner.uuid == user.uuid

    def test_create_visibility_profile_for_file(self, db_session):
        """Test creating visibility profile linked to a file/document."""
        # Create organization, user, and document
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        content = "Test document content"
        document = Document(
            title="Test Document",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test.txt",
            file_path="/test/path/test.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        # Create visibility profile for file
        profile = VisibilityProfile(
            name="File Visibility Profile",
            description="Controls entity visibility for test file",
            owner_uuid=user.uuid,
            file_uuid=document.uuid,
            collection_uuid=None,
            version_id="DEFAULT",
            profile_type="FILE",
            visible_entity_types=["Person", "Organization"],
            visible_relationship_types=["works_for", "knows"],
            hidden_entities=[],
            hidden_relationships=[],
            all_entities=["Person", "Organization", "Location"],
            enabled_entities=["Person", "Organization"],
            all_relationships=["works_for", "knows", "located_in"],
            enabled_relationships=["works_for", "knows"],
            auto_include_new=True,
            is_active=True,
        )
        db_session.add(profile)
        db_session.flush()

        assert profile.id is not None
        assert isinstance(profile.uuid, uuid.UUID)
        assert isinstance(profile.file_uuid, uuid.UUID)
        assert profile.file_uuid == document.uuid
        assert profile.collection_uuid is None
        assert profile.profile_type == "FILE"
        assert profile.auto_include_new is True
        assert profile.is_active is True
        assert profile.visible_entity_types == ["Person", "Organization"]
        assert profile.enabled_entities == ["Person", "Organization"]

        # Verify relationships
        assert profile.owner.uuid == user.uuid
        assert profile.document.uuid == document.uuid

    def test_create_visibility_profile_for_collection(self, db_session):
        """Test creating visibility profile linked to a collection."""
        # Create organization, user, and collection
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        collection = Collection(
            name="Test Collection",
            description="Test collection for visibility",
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            is_deleted=False,
        )
        db_session.add(collection)
        db_session.flush()

        # Create visibility profile for collection
        profile = VisibilityProfile(
            name="Collection Visibility Profile",
            description="Controls entity visibility for test collection",
            owner_uuid=user.uuid,
            file_uuid=None,
            collection_uuid=collection.uuid,
            version_id=str(collection.id),
            profile_type="COLLECTION",
            visible_entity_types=["Person"],
            visible_relationship_types=["knows"],
            hidden_entities=[],
            hidden_relationships=[],
            all_entities=["Person", "Organization"],
            enabled_entities=["Person"],
            all_relationships=["knows", "works_for"],
            enabled_relationships=["knows"],
            auto_include_new=False,
            is_active=True,
        )
        db_session.add(profile)
        db_session.flush()

        assert profile.id is not None
        assert isinstance(profile.collection_uuid, uuid.UUID)
        assert profile.collection_uuid == collection.uuid
        assert profile.file_uuid is None
        assert profile.profile_type == "COLLECTION"
        assert profile.version_id == str(collection.id)
        assert profile.auto_include_new is False

        # Verify relationships
        assert profile.collection.uuid == collection.uuid

    def test_collection_soft_delete(self, db_session):
        """Test soft delete functionality for collections."""
        # Create organization and user
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create collection
        collection = Collection(
            name="Test Collection",
            description="Collection to be soft deleted",
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            is_deleted=False,
            deleted_at=None,
        )
        db_session.add(collection)
        db_session.flush()

        original_id = collection.id
        assert collection.is_deleted is False
        assert collection.deleted_at is None

        # Soft delete the collection
        from datetime import datetime, timezone

        collection.is_deleted = True
        collection.deleted_at = datetime.now(timezone.utc)
        db_session.flush()

        # Verify soft delete persisted
        deleted_collection = (
            db_session.query(Collection).filter_by(id=original_id).first()
        )
        assert deleted_collection.id == original_id
        assert deleted_collection.is_deleted is True
        assert deleted_collection.deleted_at is not None
        assert isinstance(deleted_collection.deleted_at, datetime)

        # Verify we can query to exclude soft-deleted items
        active_collections = (
            db_session.query(Collection)
            .filter_by(is_deleted=False, owner_uuid=user.uuid)
            .all()
        )
        assert len(active_collections) == 0

    def test_update_visibility_profile(self, db_session):
        """Test updating visibility profile fields."""
        # Create organization and user
        org = Organization(name="Test Org")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        # Create visibility profile
        profile = VisibilityProfile(
            name="Original Profile",
            description="Original description",
            owner_uuid=user.uuid,
            profile_type="GLOBAL",
            visible_entity_types=["Person"],
            enabled_entities=["Person"],
            auto_include_new=True,
            is_active=True,
        )
        db_session.add(profile)
        db_session.flush()

        original_id = profile.id

        # Update profile
        profile.name = "Updated Profile"
        profile.enabled_entities = ["Person", "Organization", "Location"]
        profile.is_active = False
        db_session.flush()

        # Verify updates persisted
        updated_profile = (
            db_session.query(VisibilityProfile).filter_by(id=original_id).first()
        )
        assert updated_profile.id == original_id
        assert updated_profile.name == "Updated Profile"
        assert updated_profile.enabled_entities == [
            "Person",
            "Organization",
            "Location",
        ]
        assert updated_profile.is_active is False
        assert updated_profile.owner_uuid == user.uuid  # Foreign key unchanged
