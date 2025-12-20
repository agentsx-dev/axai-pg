from typing import List, Optional, Dict, Any
from datetime import timedelta
from uuid import UUID
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload
from .base_repository import BaseRepository
from .cache_manager import cache_query
from .metrics_utils import track_metrics, with_metrics
from ..models.document import Document
from ..models.topic import DocumentTopic
from ..models.summary import Summary

@with_metrics
class DocumentRepository(BaseRepository[Document]):
    """Repository for managing Document entities with specialized document operations."""
    model_class = Document
    
    def __init__(self):
        super().__init__(Document)
    
    @cache_query(ttl=timedelta(minutes=15))
    @track_metrics(Document)
    async def find_by_organization(self, org_uuid: UUID, options: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Find documents by organization UUID."""
        try:
            with self._get_session() as session:
                query = session.query(Document).filter(Document.org_uuid == org_uuid)
                query = self._apply_document_options(query, options)
                return query.all()
        except Exception as e:
            raise RuntimeError(f"Error finding documents by organization: {str(e)}") from e
    
    @cache_query(ttl=timedelta(minutes=15))
    @track_metrics(Document)
    async def find_by_owner(self, owner_uuid: UUID, options: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Find documents by owner UUID."""
        try:
            with self._get_session() as session:
                query = session.query(Document).filter(Document.owner_uuid == owner_uuid)
                query = self._apply_document_options(query, options)
                return query.all()
        except Exception as e:
            raise RuntimeError(f"Error finding documents by owner: {str(e)}") from e
    
    @cache_query(ttl=timedelta(minutes=30))
    @track_metrics(Document)
    async def find_by_topic(self, topic_uuid: UUID, options: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Find documents by topic UUID."""
        try:
            with self._get_session() as session:
                query = session.query(Document)\
                    .join(DocumentTopic)\
                    .filter(DocumentTopic.topic_uuid == topic_uuid)
                query = self._apply_document_options(query, options)
                return query.all()
        except Exception as e:
            raise RuntimeError(f"Error finding documents by topic: {str(e)}") from e
    
    @cache_query(ttl=timedelta(minutes=30))
    @track_metrics(Document)
    async def find_related_documents(self, document_uuid: UUID, max_depth: int = 2) -> List[Document]:
        """Find related documents using graph relationships up to max_depth."""
        try:
            with self._get_session() as session:
                # This uses a recursive CTE query to traverse the graph
                query = """
                WITH RECURSIVE related_docs AS (
                    -- Base case: direct relationships
                    SELECT DISTINCT d.uuid, d.title, 1 as depth
                    FROM documents d
                    JOIN graph_relationships gr ON gr.source_entity_uuid = :doc_uuid 
                        AND gr.target_entity_uuid = d.uuid
                    WHERE d.uuid != :doc_uuid
                    
                    UNION
                    
                    -- Recursive case: traverse relationships
                    SELECT DISTINCT d.uuid, d.title, rd.depth + 1
                    FROM related_docs rd
                    JOIN graph_relationships gr ON gr.source_entity_uuid = rd.uuid
                    JOIN documents d ON gr.target_entity_uuid = d.uuid
                    WHERE d.uuid != :doc_uuid AND rd.depth < :max_depth
                )
                SELECT DISTINCT d.*
                FROM documents d
                JOIN related_docs rd ON rd.uuid = d.uuid
                ORDER BY rd.depth;
                """
                result = session.execute(query, {"doc_uuid": document_uuid, "max_depth": max_depth})
                return [Document(**row) for row in result]
        except Exception as e:
            raise RuntimeError(f"Error finding related documents: {str(e)}") from e
    
    @track_metrics(Document)
    async def create_with_summary(self, document: Dict[str, Any], summary: Dict[str, Any]) -> Document:
        """Create a document and its summary in a single transaction."""
        async def _create_both(session: Session):
            # Create document
            db_document = Document(**document)
            session.add(db_document)
            session.flush()  # Flush to get the document UUID
            
            # Create summary with document reference
            summary['document_uuid'] = db_document.uuid
            db_summary = Summary(**summary)
            session.add(db_summary)
            
            # Update document flag
            db_document.has_summary = True
            
            return db_document
        
        return await self.transaction(_create_both)
    
    @track_metrics(Document)
    async def update_with_version(self, uuid: UUID, document: Dict[str, Any], change_description: Optional[str] = None) -> Document:
        """Update document while creating a new version record."""
        async def _update_with_version(session: Session):
            # Get current document
            current = session.query(Document).filter_by(uuid=uuid).first()
            if not current:
                raise ValueError(f"Document {uuid} not found")
            
            # Create version record
            version = {
                'document_uuid': uuid,
                'version': current.version + 1,
                'content': current.content,
                'title': current.title,
                'change_description': change_description,
                'created_by_uuid': current.owner_uuid,
                'file_path': current.file_path,
                'content_type': current.content_type
            }
            session.execute(
                'INSERT INTO document_versions (document_uuid, version, content, title, change_description, '
                'created_by_uuid, file_path, content_type) '
                'VALUES (:document_uuid, :version, :content, :title, :change_description, '
                ':created_by_uuid, :file_path, :content_type)',
                version
            )
            
            # Update document
            for key, value in document.items():
                setattr(current, key, value)
            current.version += 1
            current.has_versions = True
            
            return current
        
        return await self.transaction(_update_with_version)
    
    @cache_query(ttl=timedelta(minutes=5))
    @track_metrics(Document)
    async def search(self, query: str, org_uuid: UUID, options: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Search documents using full-text search capabilities."""
        try:
            with self._get_session() as session:
                search_query = session.query(Document)\
                    .filter(Document.org_uuid == org_uuid)\
                    .filter(
                        or_(
                            Document.title.ilike(f"%{query}%"),
                            Document.content.ilike(f"%{query}%")
                        )
                    )
                search_query = self._apply_document_options(search_query, options)
                return search_query.all()
        except Exception as e:
            raise RuntimeError(f"Error searching documents: {str(e)}") from e
    
    @cache_query(ttl=timedelta(minutes=15))
    @track_metrics(Document)
    async def find_by_status(self, status: str, org_uuid: UUID, options: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Find documents by status within an organization."""
        try:
            with self._get_session() as session:
                query = session.query(Document)\
                    .filter(Document.org_uuid == org_uuid)\
                    .filter(Document.status == status)
                query = self._apply_document_options(query, options)
                return query.all()
        except Exception as e:
            raise RuntimeError(f"Error finding documents by status: {str(e)}") from e
    
    def _apply_document_options(self, query, options: Optional[Dict[str, Any]] = None):
        """Apply document-specific query options."""
        if not options:
            return query
            
        if options.get('include_summaries'):
            query = query.options(joinedload(Document.summaries))
            
        if options.get('include_topics'):
            query = query.options(joinedload(Document.topics))
            
        if 'offset' in options:
            query = query.offset(options['offset'])
            
        if 'limit' in options:
            query = query.limit(options['limit'])
            
        if 'order_by' in options:
            for field, direction in options['order_by'].items():
                column = getattr(Document, field)
                if direction == 'DESC':
                    column = column.desc()
                query = query.order_by(column)
                
        return query
