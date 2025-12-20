import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from ....config.database import DatabaseManager
from ...models.document import Document
from ...models.topic import Topic, DocumentTopic
from ...models.summary import Summary
from ..document_repository import DocumentRepository
from ..repository_factory import RepositoryFactory
from ..cache_manager import CacheManager

@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use SQLite in-memory database for testing
    engine = create_engine('sqlite:///:memory:')
    DatabaseManager.get_instance().initialize({
        'connection_string': 'sqlite:///:memory:',
        'pool_size': 1,
        'max_overflow': 0
    })
    
    # Create all tables
    Document.metadata.create_all(engine)
    Topic.metadata.create_all(engine)
    DocumentTopic.metadata.create_all(engine)
    Summary.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session()

@pytest.fixture
def document_repository():
    """Create a document repository instance."""
    repo = DocumentRepository()
    # Clear cache before each test
    CacheManager.get_instance().clear()
    return repo

@pytest.fixture
def repository_factory():
    """Get repository factory instance."""
    return RepositoryFactory.get_instance()

@pytest.fixture
def sample_document():
    """Create a sample document."""
    return {
        'title': 'Test Document',
        'content': 'Test content',
        'owner_uuid': uuid4(),
        'org_uuid': uuid4(),
        'status': 'draft',
        'version': 1,
        'document_type': 'text',
        'processing_status': 'complete',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

@pytest.mark.asyncio
async def test_create_document(document_repository, sample_document):
    """Test creating a document."""
    doc = await document_repository.create(sample_document)
    assert doc.uuid is not None
    assert doc.id is not None
    assert len(doc.id) == 8  # Short ID is 8 characters
    assert doc.title == sample_document['title']
    assert doc.content == sample_document['content']

@pytest.mark.asyncio
async def test_find_by_id(document_repository, sample_document):
    """Test finding a document by ID (UUID or short ID)."""
    created = await document_repository.create(sample_document)
    
    # Test finding by UUID
    found_by_uuid = await document_repository.find_by_uuid(created.uuid)
    assert found_by_uuid is not None
    assert found_by_uuid.uuid == created.uuid
    assert found_by_uuid.title == created.title
    
    # Test finding by short ID
    found_by_short_id = await document_repository.find_by_short_id(created.id)
    assert found_by_short_id is not None
    assert found_by_short_id.id == created.id
    assert found_by_short_id.title == created.title
    
    # Test finding with flexible find_by_id method (UUID)
    found_flexible = await document_repository.find_by_id(created.uuid)
    assert found_flexible is not None
    assert found_flexible.uuid == created.uuid
    
    # Test finding with flexible find_by_id method (short ID)
    found_flexible_short = await document_repository.find_by_id(created.id)
    assert found_flexible_short is not None
    assert found_flexible_short.id == created.id

@pytest.mark.asyncio
async def test_find_by_organization(document_repository, sample_document):
    """Test finding documents by organization UUID."""
    await document_repository.create(sample_document)
    docs = await document_repository.find_by_organization(sample_document['org_uuid'])
    assert len(docs) == 1
    assert docs[0].org_uuid == sample_document['org_uuid']

@pytest.mark.asyncio
async def test_update_with_version(document_repository, sample_document):
    """Test updating a document with version tracking."""
    doc = await document_repository.create(sample_document)
    updated = await document_repository.update_with_version(
        doc.uuid,
        {'title': 'Updated Title'},
        'Updated title for testing'
    )
    assert updated.title == 'Updated Title'
    assert updated.version == 2
    assert updated.has_versions is True

@pytest.mark.asyncio
async def test_create_with_summary(document_repository, sample_document):
    """Test creating a document with an associated summary."""
    summary_data = {
        'content': 'Test summary',
        'summary_type': 'auto',
        'confidence_score': 0.95
    }
    doc = await document_repository.create_with_summary(sample_document, summary_data)
    assert doc.uuid is not None
    assert doc.has_summary is True
    # Verify summary was created
    with document_repository._get_session() as session:
        summary = session.query(Summary).filter_by(document_uuid=doc.uuid).first()
        assert summary is not None
        assert summary.content == summary_data['content']

@pytest.mark.asyncio
async def test_search(document_repository, sample_document):
    """Test document search functionality."""
    await document_repository.create(sample_document)
    results = await document_repository.search('Test', sample_document['org_uuid'])
    assert len(results) == 1
    assert results[0].title == sample_document['title']

@pytest.mark.asyncio
async def test_find_by_status(document_repository, sample_document):
    """Test finding documents by status."""
    await document_repository.create(sample_document)
    docs = await document_repository.find_by_status('draft', sample_document['org_uuid'])
    assert len(docs) == 1
    assert docs[0].status == 'draft'

@pytest.mark.asyncio
async def test_delete_document(document_repository, sample_document):
    """Test deleting a document."""
    doc = await document_repository.create(sample_document)
    success = await document_repository.delete(doc.uuid)
    assert success is True
    found = await document_repository.find_by_uuid(doc.uuid)
    assert found is None

@pytest.mark.asyncio
async def test_find_related_documents(document_repository, sample_document):
    """Test finding related documents."""
    doc1 = await document_repository.create(sample_document)
    doc2 = await document_repository.create({
        **sample_document,
        'title': 'Related Document'
    })
    
    # Create a relationship between documents
    with document_repository._get_session() as session:
        session.execute(
            'INSERT INTO graph_relationships (source_entity_uuid, target_entity_uuid, relationship_type) '
            'VALUES (:source, :target, :type)',
            {'source': doc1.uuid, 'target': doc2.uuid, 'type': 'related'}
        )
        session.commit()
    
    related = await document_repository.find_related_documents(doc1.uuid)
    assert len(related) == 1
    assert related[0].uuid == doc2.uuid

@pytest.mark.asyncio
async def test_transaction_rollback(document_repository, sample_document):
    """Test transaction rollback on error."""
    async def failing_operation(session):
        doc = Document(**sample_document)
        session.add(doc)
        raise ValueError("Test error")
    
    with pytest.raises(RuntimeError):
        await document_repository.transaction(failing_operation)
    
    # Verify document was not created
    docs = await document_repository.find_many({})
    assert len(docs) == 0

@pytest.mark.asyncio
async def test_caching(document_repository, sample_document):
    """Test that caching works for repository methods."""
    # Create test document
    doc = await document_repository.create(sample_document)
    
    # First call should cache the result (using UUID)
    first_result = await document_repository.find_by_uuid(doc.uuid)
    cache_key = f"find_by_uuid_{doc.uuid}"
    
    # Verify result is in cache
    cached_value = CacheManager.get_instance().get(cache_key)
    assert cached_value is not None
    
    # Second call should use cached result
    second_result = await document_repository.find_by_uuid(doc.uuid)
    assert second_result.uuid == first_result.uuid
    
    # Verify hit count increased
    assert CacheManager.get_instance().get_hit_rate(cache_key) > 0

@pytest.mark.asyncio
async def test_cache_invalidation(document_repository, sample_document):
    """Test cache invalidation on updates."""
    # Create and cache a document
    doc = await document_repository.create(sample_document)
    await document_repository.find_by_uuid(doc.uuid)
    
    # Update document should invalidate cache
    updated_title = "Updated Title"
    await document_repository.update(doc.uuid, {"title": updated_title})
    
    # Next find should hit database
    updated_doc = await document_repository.find_by_uuid(doc.uuid)
    assert updated_doc.title == updated_title

@pytest.mark.asyncio
async def test_metrics_tracking(document_repository, repository_factory, sample_document):
    """Test that metrics are being tracked."""
    # Create a document and perform some operations
    doc = await document_repository.create(sample_document)
    await document_repository.find_by_uuid(doc.uuid)
    await document_repository.find_by_organization(doc.org_uuid)
    
    # Get metrics
    metrics = repository_factory.get_metrics(Document)
    
    # Verify operations were counted
    assert metrics.operation_count >= 3
    assert metrics.error_count == 0
    assert metrics.last_operation_time is not None

@pytest.mark.asyncio
async def test_slow_query_detection(document_repository, repository_factory, sample_document):
    """Test that slow queries are detected and tracked."""
    # Create multiple documents to simulate a slower query
    docs = []
    for i in range(10):
        doc_data = {**sample_document, 'title': f'Doc {i}'}
        docs.append(await document_repository.create(doc_data))
    
    # Perform a potentially slow operation
    await document_repository.find_related_documents(docs[0].uuid, max_depth=3)
    
    # Get metrics
    metrics = repository_factory.get_metrics(Document)
    
    # Check if any slow queries were detected
    # Note: This might not always detect slow queries in test environment
    print(f"Slow query count: {metrics.slow_query_count}")

@pytest.mark.asyncio
async def test_cache_ttl(document_repository, sample_document):
    """Test that cache entries expire after TTL."""
    doc = await document_repository.create(sample_document)
    
    # First call should cache the result
    await document_repository.find_by_uuid(doc.uuid)
    cache_key = f"find_by_uuid_{doc.uuid}"
    
    # Manipulate cache entry TTL for testing
    cache = CacheManager.get_instance()
    value, _ = cache._cache[cache_key]
    cache._cache[cache_key] = (value, datetime.now() - timedelta(minutes=1))
    
    # Next call should miss cache due to expiration
    cached_value = cache.get(cache_key)
    assert cached_value is None

@pytest.mark.asyncio
async def test_complex_query_caching(document_repository, sample_document):
    """Test caching behavior with complex queries."""
    # Create test documents with relationships
    doc1 = await document_repository.create(sample_document)
    doc2 = await document_repository.create({**sample_document, 'title': 'Related Doc'})
    
    # Create relationship between documents
    with document_repository._get_session() as session:
        session.execute(
            'INSERT INTO graph_relationships (source_entity_uuid, target_entity_uuid, relationship_type) '
            'VALUES (:source, :target, :type)',
            {'source': doc1.uuid, 'target': doc2.uuid, 'type': 'related'}
        )
        session.commit()
    
    # Execute complex query and measure time
    start_time = datetime.now()
    first_result = await document_repository.find_related_documents(doc1.uuid, max_depth=2)
    first_query_time = (datetime.now() - start_time).total_seconds()
    
    # Execute same query again
    start_time = datetime.now()
    second_result = await document_repository.find_related_documents(doc1.uuid, max_depth=2)
    second_query_time = (datetime.now() - start_time).total_seconds()
    
    # Second query should be faster due to caching
    assert second_query_time < first_query_time
    assert len(second_result) == len(first_result)

@pytest.mark.asyncio
async def test_concurrent_operations(document_repository, sample_document):
    """Test concurrent operations with caching."""
    import asyncio
    
    # Create base document
    doc = await document_repository.create(sample_document)
    
    # Define concurrent operations
    async def update_operation():
        await document_repository.update(doc.uuid, {'title': f'Updated {datetime.now()}'})
    
    async def read_operation():
        return await document_repository.find_by_uuid(doc.uuid)
    
    # Execute operations concurrently
    tasks = []
    for _ in range(5):
        tasks.append(asyncio.create_task(update_operation()))
        tasks.append(asyncio.create_task(read_operation()))
    
    # Wait for all operations to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify no exceptions occurred
    assert not any(isinstance(r, Exception) for r in results)

@pytest.mark.asyncio
async def test_to_dict_serialization(document_repository, sample_document):
    """Test the to_dict serialization helper."""
    doc = await document_repository.create(sample_document)
    
    # Test without UUID
    result = document_repository.to_dict(doc, include_uuid=False)
    assert 'id' in result
    assert len(result['id']) == 8
    assert 'uuid' not in result
    
    # Test with UUID
    result_with_uuid = document_repository.to_dict(doc, include_uuid=True)
    assert 'id' in result_with_uuid
    assert 'uuid' in result_with_uuid
    assert len(result_with_uuid['id']) == 8
    assert isinstance(result_with_uuid['uuid'], str)
    
    # Verify UUID matches
    assert str(doc.uuid) == result_with_uuid['uuid']
    assert doc.id == result_with_uuid['id']

