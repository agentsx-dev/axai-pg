import pytest
from sqlalchemy.orm import Session
from axai_pg.data.models import User, Document
from axai_pg.data.security.query_middleware import SecurityQueryMiddleware
from axai_pg.data.security.security_config import SecurityConfigFactory
from axai_pg.data.config.database import DatabaseManager

@pytest.fixture
def db_session():
    """Provides a database session for testing."""
    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        yield session

@pytest.fixture
def security_middleware():
    """Provides a configured security middleware."""
    config = SecurityConfigFactory.create_test_config()
    return SecurityQueryMiddleware(config)

@pytest.fixture
async def test_user(db_session):
    """Creates a test user with standard permissions."""
    user = User(username='test_middleware_user', email='test_middleware@example.com', org_id=1)
    db_session.add(user)
    db_session.commit()
    
    # Add user role and permissions via security manager
    from axai_pg.data.security.security_manager import SecurityManager
    security = SecurityManager.get_instance()
    await security.load_permissions(user.id, user.org_id)
    
    return user

@pytest.fixture
def test_document(db_session, test_user):
    """Creates a test document for permission testing."""
    doc = Document(
        title='Test Middleware Document',
        content='Test Content',
        owner_id=test_user.id,
        org_id=test_user.org_id
    )
    db_session.add(doc)
    db_session.commit()
    return doc

@pytest.mark.asyncio
async def test_org_isolation(security_middleware, db_session, test_user, test_document):
    """Test organization isolation in queries."""
    # Set session context
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Query should return document from user's org
    query = db_session.query(Document)
    security_middleware._apply_org_isolation(query)
    result = query.all()
    assert len(result) == 1
    assert result[0].id == test_document.id
    
    # Query with different org should return nothing
    db_session.info.org_id = 999
    query = db_session.query(Document)
    security_middleware._apply_org_isolation(query)
    result = query.all()
    assert len(result) == 0

@pytest.mark.asyncio
async def test_create_permission(security_middleware, db_session, test_user):
    """Test create permission enforcement."""
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Test allowed creation
    new_doc = Document(
        title='New Test Document',
        content='New Content'
    )
    db_session.add(new_doc)
    security_middleware._check_create_permission(db_session, new_doc)
    assert new_doc.org_id == test_user.org_id
    
    # Test creation without permission
    db_session.info.user_id = 999  # User without permissions
    new_doc2 = Document(
        title='Unauthorized Document',
        content='Unauthorized Content'
    )
    db_session.add(new_doc2)
    with pytest.raises(PermissionError):
        security_middleware._check_create_permission(db_session, new_doc2)

@pytest.mark.asyncio
async def test_update_permission(security_middleware, db_session, test_user, test_document):
    """Test update permission enforcement."""
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Test allowed update
    test_document.title = 'Updated Title'
    security_middleware._check_update_permission(db_session, test_document)
    
    # Test update without permission
    db_session.info.user_id = 999  # User without permissions
    with pytest.raises(PermissionError):
        security_middleware._check_update_permission(db_session, test_document)

@pytest.mark.asyncio
async def test_delete_permission(security_middleware, db_session, test_user, test_document):
    """Test delete permission enforcement."""
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Test allowed deletion
    security_middleware._check_delete_permission(db_session, test_document)
    
    # Test deletion without permission
    db_session.info.user_id = 999  # User without permissions
    with pytest.raises(PermissionError):
        security_middleware._check_delete_permission(db_session, test_document)

@pytest.mark.asyncio
async def test_rate_limiting(security_middleware, db_session, test_user):
    """Test query rate limiting."""
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Test within rate limit
    query = db_session.query(Document)
    security_middleware._check_rate_limits(query)
    
    # Test exceeding rate limit
    # Add rate limit records via security manager
    from axai_pg.data.security.security_manager import SecurityManager
    security = SecurityManager.get_instance()
    
    # Artificially exceed rate limit
    for _ in range(10000):  # Exceed test config limit
        security.log_access(test_user.id, 'query_documents', 'documents')
    
    with pytest.raises(ValueError, match="Rate limit exceeded"):
        security_middleware._check_rate_limits(query)

@pytest.mark.asyncio
async def test_before_flush_hooks(security_middleware, db_session, test_user):
    """Test before_flush event hooks."""
    db_session.info.user_id = test_user.id
    db_session.info.org_id = test_user.org_id
    
    # Test create
    new_doc = Document(title='Flush Test Doc', content='Test Content')
    db_session.add(new_doc)
    security_middleware._before_flush(db_session, None, None)
    assert new_doc.org_id == test_user.org_id
    
    # Test update
    new_doc.title = 'Updated Flush Test Doc'
    security_middleware._before_flush(db_session, None, None)
    
    # Test delete
    db_session.delete(new_doc)
    security_middleware._before_flush(db_session, None, None)
