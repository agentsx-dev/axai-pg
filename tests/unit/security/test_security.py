"""
Tests for security manager and related functionality.

NOTE: These tests require a real PostgreSQL database.
Run with: pytest tests/unit/security/test_security.py -v --integration
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from axai_pg.data.models.security import UserRole, RolePermission, AuditLog, Role
from axai_pg.data.models import User, Document, Organization


@pytest.fixture
def test_org(db_session):
    """Creates a test organization."""
    org = Organization(name="Test Security Org")
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture
def test_role(db_session):
    """Creates a test role."""
    role = Role(name="test_user_role", description="Test user role")
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def test_user(db_session, test_org):
    """Creates a test user with basic role."""
    user = User(
        username="test_security_user",
        email="test_security@example.com",
        org_uuid=test_org.uuid,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def test_user_role(db_session, test_user, test_role):
    """Assigns a role to the test user."""
    user_role = UserRole(
        user_uuid=test_user.uuid, role_uuid=test_role.uuid, role_name=test_role.name
    )
    db_session.add(user_role)
    db_session.flush()
    return user_role


@pytest.fixture
def test_document(db_session, test_user, test_org):
    """Creates a test document owned by test_user."""
    doc = Document(
        title="Test Security Document",
        content="Test Content",
        owner_uuid=test_user.uuid,
        org_uuid=test_org.uuid,
        document_type="text",
        status="draft",
        filename="security_test.txt",
        file_path="/test/security_test.txt",
        size=100,
        content_type="text/plain",
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def test_user_role_assignment(db_session, test_user, test_role, test_user_role):
    """Test user role assignment."""
    # Verify role was assigned
    assigned_role = (
        db_session.query(UserRole).filter_by(user_uuid=test_user.uuid).first()
    )
    assert assigned_role is not None
    assert assigned_role.role_uuid == test_role.uuid
    assert assigned_role.role_name == test_role.name


def test_role_permission_creation(db_session):
    """Test creating role permissions."""
    perm = RolePermission(
        role_name="test_role", resource_name="documents", permission_type="READ"
    )
    db_session.add(perm)
    db_session.flush()

    assert perm.uuid is not None
    assert perm.permission_type == "READ"


def test_multiple_permissions(db_session):
    """Test creating multiple permissions for a role."""
    perms = [
        RolePermission(
            role_name="multi_role", resource_name="documents", permission_type="READ"
        ),
        RolePermission(
            role_name="multi_role", resource_name="documents", permission_type="CREATE"
        ),
        RolePermission(
            role_name="multi_role", resource_name="documents", permission_type="UPDATE"
        ),
    ]
    for perm in perms:
        db_session.add(perm)
    db_session.flush()

    # Query permissions
    saved_perms = (
        db_session.query(RolePermission).filter_by(role_name="multi_role").all()
    )
    assert len(saved_perms) == 3
    perm_types = {p.permission_type for p in saved_perms}
    assert perm_types == {"READ", "CREATE", "UPDATE"}


def test_audit_log_creation(db_session, test_user):
    """Test audit log creation."""
    log = AuditLog(
        user_uuid=test_user.uuid,
        username=test_user.username,
        action="READ",
        resource_type="documents",
        resource_uuid=None,
        details={"test": "data"},
    )
    db_session.add(log)
    db_session.flush()

    assert log.uuid is not None
    assert log.action == "READ"
    assert log.username == test_user.username


def test_document_ownership(db_session, test_user, test_document, test_org):
    """Test document ownership verification."""
    # Document should be owned by test_user
    assert test_document.owner_uuid == test_user.uuid
    assert test_document.org_uuid == test_org.uuid

    # Query by owner
    owned_docs = db_session.query(Document).filter_by(owner_uuid=test_user.uuid).all()
    assert len(owned_docs) == 1
    assert owned_docs[0].uuid == test_document.uuid


def test_organization_isolation(db_session, test_org, test_user, test_document):
    """Test organization data isolation."""
    # Create another org
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.flush()

    # Create user in other org
    other_user = User(
        username="other_user", email="other@example.com", org_uuid=other_org.uuid
    )
    db_session.add(other_user)
    db_session.flush()

    # Create document in other org
    other_doc = Document(
        title="Other Document",
        content="Other Content",
        owner_uuid=other_user.uuid,
        org_uuid=other_org.uuid,
        document_type="text",
        status="draft",
        filename="other.txt",
        file_path="/other/other.txt",
        size=50,
        content_type="text/plain",
    )
    db_session.add(other_doc)
    db_session.flush()

    # Query documents by org - should be isolated
    org1_docs = db_session.query(Document).filter_by(org_uuid=test_org.uuid).all()
    org2_docs = db_session.query(Document).filter_by(org_uuid=other_org.uuid).all()

    assert len(org1_docs) == 1
    assert len(org2_docs) == 1
    assert org1_docs[0].uuid == test_document.uuid
    assert org2_docs[0].uuid == other_doc.uuid
