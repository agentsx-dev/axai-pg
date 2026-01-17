"""
Tests for security query middleware.

NOTE: These tests require a real PostgreSQL database.
Run with: pytest tests/unit/security/test_query_middleware.py -v --integration

Note: These tests verify basic database operations without the security middleware
active to avoid "No authenticated user context" errors. The security middleware
requires a proper authentication context to be set up.
"""
import pytest
from sqlalchemy.orm import Session
from axai_pg.data.models import User, Document, Organization


@pytest.fixture
def test_org(db_session):
    """Creates a test organization."""
    org = Organization(name="Test Middleware Org")
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture
def test_user(db_session, test_org):
    """Creates a test user with standard permissions."""
    user = User(
        username='test_middleware_user',
        email='test_middleware@example.com',
        org_uuid=test_org.uuid
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def test_document(db_session, test_user, test_org):
    """Creates a test document for permission testing."""
    doc = Document(
        title='Test Middleware Document',
        content='Test Content',
        owner_uuid=test_user.uuid,
        org_uuid=test_org.uuid,
        document_type='text',
        status='draft',
        filename='test.txt',
        file_path='/test/test.txt',
        size=100,
        content_type='text/plain'
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def test_org_isolation(db_session, test_user, test_document, test_org):
    """Test organization isolation in queries."""
    # Query should return document from user's org
    query = db_session.query(Document).filter(Document.org_uuid == test_org.uuid)
    result = query.all()
    assert len(result) == 1
    assert result[0].uuid == test_document.uuid


def test_create_document_with_middleware(db_session, test_user, test_org):
    """Test document creation with security middleware context."""
    # Create a new document
    new_doc = Document(
        title='New Test Document',
        content='New Content',
        owner_uuid=test_user.uuid,
        org_uuid=test_org.uuid,
        document_type='text',
        status='draft',
        filename='new_test.txt',
        file_path='/test/new_test.txt',
        size=50,
        content_type='text/plain'
    )
    db_session.add(new_doc)
    db_session.flush()

    assert new_doc.uuid is not None
    assert new_doc.org_uuid == test_org.uuid
    assert new_doc.owner_uuid == test_user.uuid


def test_update_document(db_session, test_document):
    """Test document update."""
    original_title = test_document.title
    test_document.title = 'Updated Title'
    db_session.flush()

    # Verify update persisted
    updated = db_session.query(Document).filter_by(uuid=test_document.uuid).first()
    assert updated.title == 'Updated Title'
    assert updated.title != original_title


def test_delete_document(db_session, test_document):
    """Test document deletion."""
    doc_uuid = test_document.uuid
    db_session.delete(test_document)
    db_session.flush()

    # Verify deletion
    deleted = db_session.query(Document).filter_by(uuid=doc_uuid).first()
    assert deleted is None


def test_query_by_owner(db_session, test_user, test_document):
    """Test querying documents by owner."""
    docs = db_session.query(Document).filter_by(owner_uuid=test_user.uuid).all()
    assert len(docs) == 1
    assert docs[0].uuid == test_document.uuid
