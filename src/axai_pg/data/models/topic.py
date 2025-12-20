from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, ARRAY, Numeric, Boolean, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..config.database import Base
from .base import DualIdMixin

class Topic(DualIdMixin, Base):
    """
    Topics extracted from document content for categorization and discovery.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'topics'
    
    # Core Fields
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    keywords = Column(ARRAY(Text))
    parent_topic_uuid = Column(UUID(as_uuid=True), ForeignKey('topics.uuid', ondelete='SET NULL'))
    extraction_method = Column(String(50))
    global_importance = Column(Numeric(5, 4))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by_tool = Column(String(100))
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    parent_topic = relationship("Topic", remote_side=[uuid], backref="subtopics")
    documents = relationship("DocumentTopic", back_populates="topic", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("global_importance IS NULL OR (global_importance >= 0 AND global_importance <= 1)",
                       name="topics_valid_importance"),
        CheckConstraint("parent_topic_uuid != uuid",
                       name="topics_no_self_reference"),
    )

    def __repr__(self):
        return f"<Topic(uuid={self.uuid}, id='{self.id}', name='{self.name}')>"

class DocumentTopic(DualIdMixin, Base):
    """
    Junction table connecting documents to their topics with relevance scores.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'document_topics'
    
    # Core Fields
    document_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE'), nullable=False)
    topic_uuid = Column(UUID(as_uuid=True), ForeignKey('topics.uuid', ondelete='CASCADE'), nullable=False)
    relevance_score = Column(Numeric(5, 4), nullable=False)
    context = Column(JSON)
    extracted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    extracted_by_tool = Column(String(100), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="topics_rel")
    topic = relationship("Topic", back_populates="documents")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 1",
                       name="document_topics_valid_relevance"),
    )

    def __repr__(self):
        return f"<DocumentTopic(uuid={self.uuid}, id='{self.id}', document_uuid={self.document_uuid}, topic_uuid={self.topic_uuid}, score={self.relevance_score})>"
