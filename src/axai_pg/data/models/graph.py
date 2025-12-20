from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Numeric, Boolean, CheckConstraint, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from ..config.database import Base
from .base import DualIdMixin

class SourceType(enum.Enum):
    """Enum for entity/relationship source types"""
    file = "file"
    collection_generated = "collection_generated"
    document = "document"

class GraphEntity(DualIdMixin, Base):
    """
    Entities for graph representation of document connections.

    Renamed from GraphNode to GraphEntity. Entities can originate from files,
    collections, or documents, and are tracked with source metadata.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'graph_entities'

    # Core Identity Fields (from market-ui)
    entity_id = Column(Text, nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)

    # Entity Data
    name = Column(String(255), nullable=False)
    description = Column(Text)
    properties = Column(JSON)

    # Source Tracking (from market-ui)
    source_type = Column(SQLEnum(SourceType), nullable=True)
    source_file_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE'), nullable=True, index=True)
    source_collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=True, index=True)

    # Legacy document relationship (nullable for non-document entities)
    document_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='SET NULL'), nullable=True)

    # Timestamps and Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by_tool = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    document = relationship("Document", back_populates="graph_entity", foreign_keys=[document_uuid])
    source_file = relationship("Document", back_populates="graph_entities", foreign_keys=[source_file_uuid])
    source_collection = relationship("Collection", back_populates="graph_entities")
    entity_links = relationship("EntityLink", back_populates="graph_entity", lazy="dynamic", cascade="all, delete-orphan")
    outgoing_relationships = relationship("GraphRelationship",
                                       foreign_keys="GraphRelationship.source_entity_uuid",
                                       back_populates="source_entity",
                                       lazy="dynamic")
    incoming_relationships = relationship("GraphRelationship",
                                       foreign_keys="GraphRelationship.target_entity_uuid",
                                       back_populates="target_entity",
                                       lazy="dynamic")
    collection_entities_using = relationship("CollectionEntity", secondary="collection_entity_sources", back_populates="source_entities", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        Index('idx_graph_entities_entity_id', 'entity_id'),
        Index('idx_graph_entities_entity_type', 'entity_type'),
        Index('idx_graph_entities_source_file_uuid', 'source_file_uuid'),
        Index('idx_graph_entities_source_collection_uuid', 'source_collection_uuid'),
        Index('idx_graph_entities_document_uuid', 'document_uuid'),
    )

    def __repr__(self):
        return f"<GraphEntity(uuid={self.uuid}, id='{self.id}', entity_type='{self.entity_type}', name='{self.name}')>"

class GraphRelationship(DualIdMixin, Base):
    """
    Relationships between entities in the document graph structure.

    Updated to reference GraphEntity (formerly GraphNode).
    Supports source tracking from files, collections, or documents.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'graph_relationships'

    # Core Fields (renamed from source_node_id/target_node_id)
    source_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('graph_entities.uuid', ondelete='CASCADE'), nullable=False)
    target_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('graph_entities.uuid', ondelete='CASCADE'), nullable=False)

    # Relationship Identity (from market-ui)
    relationship_id = Column(Text, nullable=True, index=True)
    relationship_type = Column(String(50), nullable=False)

    # Source Tracking (from market-ui)
    source_type = Column(SQLEnum(SourceType), nullable=True)
    source_file_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE'), nullable=True, index=True)
    source_collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=True, index=True)

    # Legacy document relationship (nullable for non-document relationships)
    document_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='SET NULL'), nullable=True)

    # Relationship Metadata
    is_directed = Column(Boolean, nullable=False, default=True)
    weight = Column(Numeric(10, 5))
    confidence_score = Column(Numeric(5, 4))
    properties = Column(JSON)

    # Timestamps and Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by_tool = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    source_entity = relationship("GraphEntity", foreign_keys=[source_entity_uuid], back_populates="outgoing_relationships")
    target_entity = relationship("GraphEntity", foreign_keys=[target_entity_uuid], back_populates="incoming_relationships")
    document = relationship("Document", back_populates="graph_relationships_rel", foreign_keys=[document_uuid])
    source_file = relationship("Document", foreign_keys=[source_file_uuid], overlaps="graph_relationships_rel,document")
    source_collection = relationship("Collection", back_populates="graph_relationships")
    collection_relationships_using = relationship("CollectionRelationship", secondary="collection_relationship_sources", back_populates="source_relationships", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
                       name="graph_relationships_valid_confidence"),
        CheckConstraint("weight IS NULL OR weight > 0",
                       name="graph_relationships_valid_weight"),
        Index('idx_graph_relationships_source_entity_uuid', 'source_entity_uuid'),
        Index('idx_graph_relationships_target_entity_uuid', 'target_entity_uuid'),
        Index('idx_graph_relationships_relationship_id', 'relationship_id'),
        Index('idx_graph_relationships_source_file_uuid', 'source_file_uuid'),
        Index('idx_graph_relationships_source_collection_uuid', 'source_collection_uuid'),
        Index('idx_graph_relationships_document_uuid', 'document_uuid'),
    )

    def __repr__(self):
        return f"<GraphRelationship(uuid={self.uuid}, id='{self.id}', type='{self.relationship_type}', source={self.source_entity_uuid}, target={self.target_entity_uuid})>"
