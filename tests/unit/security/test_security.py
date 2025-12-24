import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from axai_pg.data.models.security import UserRole, RolePermission, AuditLog, RateLimit
from axai_pg.data.security.security_manager import SecurityManager
from axai_pg.data.security.repository_security import SecureRepository, secure_repository
from axai_pg.data.config.database import DatabaseManager
from axai_pg.data.models import User, Document

@pytest.fixture
def db_session():
    """Provides a database session for testing."""
    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        yield session

@pytest.fixture
def security_manager():
    """Provides a SecurityManager instance."""
    return SecurityManager.get_instance()

@pytest.fixture
async def test_user(db_session):
    """Creates a test user with basic role."""
    user = User(username='test_user', email='test@example.com', org_id=1)
    db_session.add(user)
    db_session.flush()
    
    role = UserRole(user_id=user.id, role_name='user')
    db_session.add(role)
    db_session.commit()
    
    return user

@pytest.fixture
async def test_document(db_session, test_user):
    """Creates a test document owned by test_user."""
    doc = Document(
        title='Test Document',
        content='Test Content',
        owner_id=test_user.id,
        org_id=test_user.org_id
    )
    db_session.add(doc)
    db_session.commit()
    return doc

@pytest.mark.asyncio
async def test_permission_loading(security_manager, test_user, db_session):
    """Test permission loading and caching."""
    # Add test permissions
    perms = [
        RolePermission(role_name='user', resource_name='documents', permission_type='READ'),
        RolePermission(role_name='user', resource_name='documents', permission_type='CREATE')
    ]
    db_session.bulk_save_objects(perms)
    db_session.commit()
    
    # Test permission loading
    permissions = await security_manager.load_permissions(test_user.id, test_user.org_id)
    assert 'READ' in permissions
    assert 'CREATE' in permissions
    assert 'DELETE' not in permissions

@pytest.mark.asyncio
async def test_organization_access(security_manager, test_user):
    """Test organization access verification."""
    # Test valid access
    assert security_manager.verify_organization_access(test_user.id, test_user.org_id)
    
    # Test invalid access
    assert not security_manager.verify_organization_access(test_user.id, 999)

@pytest.mark.asyncio
async def test_document_access(security_manager, test_user, test_document):
    """Test document access verification."""
    # Test owner access
    assert security_manager.verify_document_access(
        test_user.id, 
        test_document.id,
        'READ'
    )
    
    # Test non-owner access
    other_user_id = test_user.id + 1
    assert not security_manager.verify_document_access(
        other_user_id,
        test_document.id,
        'READ'
    )

@pytest.mark.asyncio
async def test_rate_limiting(security_manager, test_user, db_session):
    """Test rate limiting functionality."""
    action = 'test_action'
    
    # Test within limits
    assert security_manager.enforce_rate_limit(test_user.id, action, 5, 3600)
    
    # Add rate limit records
    for _ in range(5):
        limit = RateLimit(
            user_id=test_user.id,
            action_type=action,
            window_start=datetime.utcnow()
        )
        db_session.add(limit)
    db_session.commit()
    
    # Test exceeding limits
    assert not security_manager.enforce_rate_limit(test_user.id, action, 5, 3600)

@pytest.mark.asyncio
async def test_secure_repository(test_user, test_document, db_session):
    """Test secure repository wrapper."""
    # Create secure repository
    @secure_repository(test_user.id, test_user.org_id)
    class TestRepo(SecureRepository[Document]):
        pass
    
    repo = TestRepo(Document)
    
    # Test authorized access
    doc = await repo.find_by_id(test_document.id)
    assert doc is not None
    assert doc.id == test_document.id
    
    # Test unauthorized access
    with pytest.raises(PermissionError):
        await repo.delete(test_document.id)  # Should fail without DELETE permission

@pytest.mark.asyncio
async def test_audit_logging(security_manager, test_user, db_session):
    """Test audit logging functionality."""
    # Perform action that should be logged
    security_manager.log_access(
        test_user.id,
        'READ',
        'documents',
        1
    )
    
    # Verify log entry
    log = db_session.query(AccessLog)\
        .filter_by(username=test_user.username)\
        .order_by(AccessLog.id.desc())\
        .first()
    
    assert log is not None
    assert log.action_type == 'READ'
    assert log.table_affected == 'documents'
    assert log.record_id == 1

@pytest.mark.asyncio
async def test_permission_decorator(test_user, db_session):
    """Test the require_permission decorator."""
    from axai_pg.data.security.security_manager import require_permission
    
    @require_permission('TEST_PERMISSION')
    async def test_func(user_id, org_id):
        return True
    
    # Add test permission
    perm = RolePermission(
        role_name='user',
        resource_name='test',
        permission_type='TEST_PERMISSION'
    )
    db_session.add(perm)
    db_session.commit()
    
    # Test with permission
    result = await test_func(test_user.id, test_user.org_id)
    assert result is True
    
    # Test without permission
    db_session.delete(perm)
    db_session.commit()
    
    with pytest.raises(PermissionError):
        await test_func(test_user.id, test_user.org_id)
