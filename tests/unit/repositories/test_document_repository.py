"""
Tests for document repository operations.

NOTE: These tests require a real PostgreSQL database.
Run with: pytest tests/unit/repositories/test_document_repository.py -v --integration
"""
import pytest
from datetime import datetime
from uuid import uuid4
from axai_pg.data.models import Document, Organization, User
from axai_pg.data.models.topic import Topic, DocumentTopic
from axai_pg.data.models.summary import Summary


@pytest.fixture
def test_org(db_session):
    """Creates a test organization."""
    org = Organization(name="Test Repo Org")
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture
def test_user(db_session, test_org):
    """Creates a test user."""
    user = User(
        username='test_repo_user',
        email='test_repo@example.com',
        org_uuid=test_org.uuid
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def sample_document_data(test_user, test_org):
    """Provides sample document data."""
    return {
        'title': 'Test Document',
        'content': 'Test content for document',
        'owner_uuid': test_user.uuid,
        'org_uuid': test_org.uuid,
        'status': 'draft',
        'document_type': 'text',
        'filename': 'test_doc.txt',
        'file_path': '/test/test_doc.txt',
        'size': 100,
        'content_type': 'text/plain'
    }


@pytest.fixture
def test_document(db_session, sample_document_data):
    """Creates a test document."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()
    return doc


def test_create_document(db_session, sample_document_data):
    """Test creating a document."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()

    assert doc.uuid is not None
    assert doc.id is not None
    assert len(doc.id) == 8  # Short ID is 8 characters
    assert doc.title == sample_document_data['title']
    assert doc.content == sample_document_data['content']


def test_find_by_uuid(db_session, test_document):
    """Test finding a document by UUID."""
    found = db_session.query(Document).filter_by(uuid=test_document.uuid).first()
    assert found is not None
    assert found.uuid == test_document.uuid
    assert found.title == test_document.title


def test_find_by_short_id(db_session, test_document):
    """Test finding a document by short ID."""
    found = db_session.query(Document).filter_by(id=test_document.id).first()
    assert found is not None
    assert found.id == test_document.id
    assert found.title == test_document.title


def test_find_by_organization(db_session, test_document, test_org):
    """Test finding documents by organization UUID."""
    docs = db_session.query(Document).filter_by(org_uuid=test_org.uuid).all()
    assert len(docs) == 1
    assert docs[0].org_uuid == test_org.uuid


def test_update_document(db_session, test_document):
    """Test updating a document."""
    original_title = test_document.title
    test_document.title = 'Updated Title'
    db_session.flush()

    updated = db_session.query(Document).filter_by(uuid=test_document.uuid).first()
    assert updated.title == 'Updated Title'
    assert updated.title != original_title


def test_create_document_with_summary(db_session, sample_document_data):
    """Test creating a document with an associated summary."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()

    summary = Summary(
        document_uuid=doc.uuid,
        content='Test summary content',
        summary_type='auto',
        tool_agent='test-agent'
    )
    db_session.add(summary)
    db_session.flush()

    assert summary.uuid is not None
    assert summary.document_uuid == doc.uuid

    # Query back
    found_summary = db_session.query(Summary).filter_by(document_uuid=doc.uuid).first()
    assert found_summary is not None
    assert found_summary.content == 'Test summary content'


def test_search_by_title(db_session, test_document):
    """Test document search by title."""
    results = db_session.query(Document).filter(
        Document.title.ilike('%Test%')
    ).all()
    assert len(results) >= 1
    assert any(d.uuid == test_document.uuid for d in results)


def test_find_by_status(db_session, test_document, test_org):
    """Test finding documents by status."""
    docs = db_session.query(Document).filter_by(
        status='draft',
        org_uuid=test_org.uuid
    ).all()
    assert len(docs) == 1
    assert docs[0].status == 'draft'


def test_delete_document(db_session, sample_document_data):
    """Test deleting a document."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()

    doc_uuid = doc.uuid
    db_session.delete(doc)
    db_session.flush()

    found = db_session.query(Document).filter_by(uuid=doc_uuid).first()
    assert found is None


def test_document_owner_relationship(db_session, test_document, test_user):
    """Test document owner relationship."""
    assert test_document.owner_uuid == test_user.uuid

    # Query via relationship
    doc = db_session.query(Document).filter_by(uuid=test_document.uuid).first()
    assert doc.owner.uuid == test_user.uuid
    assert doc.owner.username == test_user.username


def test_document_organization_relationship(db_session, test_document, test_org):
    """Test document organization relationship."""
    assert test_document.org_uuid == test_org.uuid

    # Query via relationship
    doc = db_session.query(Document).filter_by(uuid=test_document.uuid).first()
    assert doc.organization.uuid == test_org.uuid
    assert doc.organization.name == test_org.name


def test_multiple_documents_same_org(db_session, test_user, test_org):
    """Test creating multiple documents in same organization."""
    docs = []
    for i in range(3):
        doc = Document(
            title=f'Document {i}',
            content=f'Content {i}',
            owner_uuid=test_user.uuid,
            org_uuid=test_org.uuid,
            document_type='text',
            status='draft',
            filename=f'doc{i}.txt',
            file_path=f'/test/doc{i}.txt',
            size=50,
            content_type='text/plain'
        )
        db_session.add(doc)
        docs.append(doc)
    db_session.flush()

    # All documents should be in same org
    org_docs = db_session.query(Document).filter_by(org_uuid=test_org.uuid).all()
    assert len(org_docs) == 3

    # Each should have unique UUID and short ID
    uuids = {d.uuid for d in org_docs}
    short_ids = {d.id for d in org_docs}
    assert len(uuids) == 3
    assert len(short_ids) == 3


def test_document_version_default(db_session, sample_document_data):
    """Test document version defaults to 1."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()

    assert doc.version == 1


def test_document_timestamps(db_session, sample_document_data):
    """Test document timestamp fields."""
    doc = Document(**sample_document_data)
    db_session.add(doc)
    db_session.flush()

    assert doc.created_at is not None
    assert doc.updated_at is not None


def test_find_by_owner(db_session, test_user, test_document):
    """Test finding documents by owner."""
    docs = db_session.query(Document).filter_by(owner_uuid=test_user.uuid).all()
    assert len(docs) == 1
    assert docs[0].uuid == test_document.uuid
