from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, Index, Boolean, Table, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from ..config.database import Base
from .base import DualIdMixin

# Association table for many-to-many relationship between documents and collections
file_collection_association = Table(
    'file_collection_association',
    Base.metadata,
    Column('file_id', UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE'), primary_key=True),
    Column('collection_id', UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), primary_key=True),
    Column('added_at', DateTime(timezone=True), nullable=False, server_default=func.now())
)

class Collection(DualIdMixin, Base):
    """
    Collections group documents together for organization and graph generation.

    Supports both organizational (multi-tenant) and non-organizational usage.
    Collections can generate merged entity views and manage visibility profiles.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'collections'

    # Core Fields
    name = Column(Text, nullable=False)
    description = Column(Text)

    # Ownership
    owner_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='CASCADE'), nullable=False)
    org_uuid = Column(UUID(as_uuid=True), ForeignKey('organizations.uuid', ondelete='CASCADE'), nullable=True)

    # Hierarchy (from market-ui)
    parent_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE', use_alter=True, name='fk_collection_parent'), nullable=True)

    # Soft Delete (from market-ui)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Graph Generation Status
    is_graph_generated = Column(Boolean, nullable=False, default=False)
    graph_generated_at = Column(DateTime(timezone=True))

    # Visibility Profile (from market-ui)
    default_visibility_profile_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('visibility_profiles.uuid', ondelete='SET NULL'),
        nullable=True
    )

    # Cache counts for performance
    entity_count = Column(Integer, nullable=False, default=0)
    relationship_count = Column(Integer, nullable=False, default=0)
    document_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Market-ui graph state management
    graph_state = Column(String(20), default='uninitialized', nullable=False)  # uninitialized/initializing/synchronized/out_of_sync/updating/error
    entities_hash = Column(Text, nullable=True)  # MD5 hash of source entities for change detection
    last_sync_timestamp = Column(DateTime(timezone=True), nullable=True)  # When graph was last synchronized

    # Relationships
    owner = relationship("User", back_populates="collections")
    organization = relationship("Organization", back_populates="collections")
    documents = relationship("Document", secondary=file_collection_association, back_populates="collections", lazy="dynamic")
    collection_entities = relationship("CollectionEntity", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    collection_relationships = relationship("CollectionRelationship", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    entity_operations = relationship("EntityOperation", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    document_contexts = relationship("DocumentCollectionContext", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    graph_entities = relationship("GraphEntity", back_populates="source_collection", lazy="dynamic")
    graph_relationships = relationship("GraphRelationship", back_populates="source_collection", lazy="dynamic")
    default_visibility_profile = relationship("VisibilityProfile", foreign_keys=[default_visibility_profile_uuid])

    # Hierarchical relationships (from market-ui)
    parent = relationship("Collection", remote_side="Collection.uuid", back_populates="subcollections")
    subcollections = relationship("Collection", back_populates="parent", lazy="dynamic", cascade="all")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="collections_name_not_empty"),
        Index('idx_collections_owner_uuid', 'owner_uuid'),
        Index('idx_collections_org_uuid', 'org_uuid'),
        Index('idx_collections_is_graph_generated', 'is_graph_generated'),
        Index('idx_collections_parent_uuid', 'parent_uuid'),
        Index('idx_collections_is_deleted', 'is_deleted'),
        Index('idx_collections_default_visibility_profile_uuid', 'default_visibility_profile_uuid'),
    )

    def __repr__(self):
        return f"<Collection(uuid={self.uuid}, id='{self.id}', name='{self.name}')>"

    @property
    def files(self):
        """Alias for documents relationship - backward compatibility with market-ui."""
        return self.documents.all()


class SourceType(enum.Enum):
    """Enum for entity/relationship source types"""
    file = "file"
    collection_generated = "collection_generated"
    document = "document"


class CollectionEntity(DualIdMixin, Base):
    """
    Merged entity views within a collection.

    Entities can be merged from multiple source files within a collection,
    providing a unified view of entities across documents.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'collection_entities'

    # Core Fields
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=False)
    entity_id = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)

    # Merged Data
    name = Column(Text, nullable=False)
    description = Column(Text)
    properties = Column(JSON)

    # Source Tracking
    source_entity_ids = Column(JSON)  # Array of original entity IDs that were merged

    # Market-ui entity lifecycle management fields
    display_name = Column(Text)  # Alternative display name (falls back to name if not set)
    is_merged = Column(Boolean, default=False, nullable=False)  # True if entity is result of merge operation
    created_from_link_uuid = Column(UUID(as_uuid=True), ForeignKey('entity_links.uuid', ondelete='SET NULL', use_alter=True, name='fk_collection_entity_created_from_link'), nullable=True)  # EntityLink that created this merge
    lifecycle_state = Column(String(20), default='individual', nullable=False)  # individual/linked/merging/merged/unmerging/error
    operation_lock = Column(UUID(as_uuid=True), nullable=True)  # UUID of operation currently modifying this entity (for concurrency control)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="collection_entities")
    entity_links = relationship("EntityLink", foreign_keys="[EntityLink.collection_entity_uuid]", back_populates="collection_entity", lazy="dynamic", cascade="all, delete-orphan")
    source_entities = relationship("GraphEntity", secondary="collection_entity_sources", back_populates="collection_entities_using", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(entity_id)) > 0", name="collection_entities_entity_id_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="collection_entities_name_not_empty"),
        Index('idx_collection_entities_collection_uuid', 'collection_uuid'),
        Index('idx_collection_entities_entity_id', 'entity_id'),
        Index('idx_collection_entities_entity_type', 'entity_type'),
    )

    def __repr__(self):
        return f"<CollectionEntity(uuid={self.uuid}, id='{self.id}', entity_id='{self.entity_id}', name='{self.name}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "uuid": str(self.uuid),
            "id": self.id,
            "collection_uuid": str(self.collection_uuid),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "properties": self.properties,
            "is_merged": self.is_merged,
            "created_from_link_uuid": str(self.created_from_link_uuid) if self.created_from_link_uuid else None,
            "lifecycle_state": self.lifecycle_state,
            "operation_lock": str(self.operation_lock) if self.operation_lock else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CollectionRelationship(DualIdMixin, Base):
    """
    Collection-scoped relationships between merged entities.

    Tracks relationships within a collection context,
    potentially merging relationships from multiple source files.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'collection_relationships'

    # Core Fields
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=False)
    source_entity_id = Column(Text, nullable=False)
    target_entity_id = Column(Text, nullable=False)
    relationship_type = Column(Text, nullable=False)

    # Metadata
    description = Column(Text)
    properties = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="collection_relationships")
    source_relationships = relationship("GraphRelationship", secondary="collection_relationship_sources", back_populates="collection_relationships_using", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(source_entity_id)) > 0", name="collection_relationships_source_not_empty"),
        CheckConstraint("length(trim(target_entity_id)) > 0", name="collection_relationships_target_not_empty"),
        Index('idx_collection_relationships_collection_uuid', 'collection_uuid'),
        Index('idx_collection_relationships_source', 'source_entity_id'),
        Index('idx_collection_relationships_target', 'target_entity_id'),
    )

    def __repr__(self):
        return f"<CollectionRelationship(uuid={self.uuid}, id='{self.id}', collection_uuid={self.collection_uuid}, {self.source_entity_id} -> {self.target_entity_id})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "uuid": str(self.uuid),
            "id": self.id,
            "collection_uuid": str(self.collection_uuid),
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Junction table for CollectionEntity sources
class CollectionEntitySource(Base):
    """
    Junction table linking merged collection entities to their source graph entities.
    
    Replaces the JSON array source_entity_ids for better queryability.
    """
    __tablename__ = 'collection_entity_sources'
    
    collection_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('collection_entities.uuid', ondelete='CASCADE'), primary_key=True)
    source_graph_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('graph_entities.uuid', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index('idx_collection_entity_sources_collection_entity', 'collection_entity_uuid'),
        Index('idx_collection_entity_sources_source_entity', 'source_graph_entity_uuid'),
    )


# Junction table for CollectionRelationship sources
class CollectionRelationshipSource(Base):
    """
    Junction table linking merged collection relationships to their source graph relationships.
    
    Replaces the JSON array source_relationship_ids for better queryability.
    """
    __tablename__ = 'collection_relationship_sources'
    
    collection_relationship_uuid = Column(UUID(as_uuid=True), ForeignKey('collection_relationships.uuid', ondelete='CASCADE'), primary_key=True)
    source_graph_relationship_uuid = Column(UUID(as_uuid=True), ForeignKey('graph_relationships.uuid', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index('idx_collection_relationship_sources_collection_rel', 'collection_relationship_uuid'),
        Index('idx_collection_relationship_sources_source_rel', 'source_graph_relationship_uuid'),
    )


class EntityLink(DualIdMixin, Base):
    """
    Cross-file entity linking within collections.

    Links entities from individual files to merged collection entities,
    enabling tracking of which source entities contribute to merged views.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'entity_links'

    # Core Fields
    graph_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('graph_entities.uuid', ondelete='CASCADE'), nullable=True)
    collection_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('collection_entities.uuid', ondelete='CASCADE'), nullable=True)

    # Collection Context (from market-ui)
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=False)

    # Link Metadata
    entity_type = Column(Text, nullable=True)  # Entity type for filtering
    confidence_score = Column(Integer)  # 0-100 confidence in the link
    link_type = Column(Text)  # e.g., "exact_match", "fuzzy_match", "manual"
    linked_entities = Column(JSON)  # Array of linked entity details

    # Merge State (from market-ui)
    is_active = Column(Boolean, nullable=False, default=True)  # Active/inactive state
    merged_entity_uuid = Column(UUID(as_uuid=True), ForeignKey('collection_entities.uuid', ondelete='SET NULL'), nullable=True)  # Result of merge
    common_name = Column(Text, nullable=True)  # Common name for merged entities
    description = Column(Text, nullable=True)  # Description of entity link
    created_by_tool = Column(Text, nullable=True) # tool used to create to mirror entity
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    graph_entity = relationship("GraphEntity", back_populates="entity_links")
    collection_entity = relationship("CollectionEntity", foreign_keys=[collection_entity_uuid], back_populates="entity_links")
    collection = relationship("Collection", foreign_keys=[collection_uuid])
    merged_entity = relationship("CollectionEntity", foreign_keys=[merged_entity_uuid])

    # Table Constraints
    __table_args__ = (
        Index('idx_entity_links_graph_entity_uuid', 'graph_entity_uuid'),
        Index('idx_entity_links_collection_entity_uuid', 'collection_entity_uuid'),
        Index('idx_entity_links_collection_uuid', 'collection_uuid'),
        Index('idx_entity_links_is_active', 'is_active'),
    )

    def get_entity_ids(self):
        """Get list of entity IDs from linked_entities JSON field."""
        if not self.linked_entities:
            return []
        return [le.get('entity_id') for le in self.linked_entities if le.get('entity_id')]

    def __repr__(self):
        return f"<EntityLink(uuid={self.uuid}, id='{self.id}', graph_entity_uuid={self.graph_entity_uuid}, collection_entity_uuid={self.collection_entity_uuid})>"


class OperationType(enum.Enum):
    """Enum for entity operation types"""
    created = "created"
    merged = "merged"
    split = "split"
    deleted = "deleted"
    updated = "updated"
    # From market-ui graph operations
    unmerged = "unmerged"
    link = "link"
    unlink = "unlink"
    initialize_graph = "initialize_graph"
    sync_graph = "sync_graph"


class EntityOperation(DualIdMixin, Base):
    """
    Operation audit trail for entity management.

    Tracks all operations performed on entities within collections,
    including merges, splits, and manual edits.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'entity_operations'

    # Core Fields
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=False)
    operation_type = Column(SQLEnum(OperationType), nullable=False)
    entity_id = Column(Text, nullable=True)  # Nullable for collection-level operations (sync_graph, initialize_graph)

    # Operation Details
    description = Column(Text)
    details = Column(JSON)  # Structured operation details

    # Actor
    performed_by_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid'), nullable=True)

    # Extended fields from market-ui
    entity_ids = Column(JSON)  # Array of affected entity IDs
    operation_data = Column(JSON)  # Additional operation metadata
    user_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid'), nullable=True)  # Alternative user reference
    status = Column(String(20), default='pending')  # pending/in_progress/completed/failed

    # Timestamp
    performed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="entity_operations")
    performed_by = relationship("User", foreign_keys=[performed_by_uuid])

    # Table Constraints
    __table_args__ = (
        Index('idx_entity_operations_collection_uuid', 'collection_uuid'),
        Index('idx_entity_operations_entity_id', 'entity_id'),
        Index('idx_entity_operations_performed_at', 'performed_at'),
        Index('idx_entity_operations_status', 'status'),
    )

    def mark_completed(self):
        """Mark operation as completed."""
        self.status = 'completed'

    def mark_failed(self, error_message: str):
        """Mark operation as failed with error message."""
        self.status = 'failed'
        if not self.operation_data:
            self.operation_data = {}
        self.operation_data['error'] = error_message

    def set_rollback_data(self, data: dict):
        """Store rollback data in operation_data field."""
        if not self.operation_data:
            self.operation_data = {}
        self.operation_data['rollback'] = data

    def __repr__(self):
        return f"<EntityOperation(uuid={self.uuid}, id='{self.id}', operation_type={self.operation_type}, entity_id='{self.entity_id}')>"


class DocumentCollectionContext(DualIdMixin, Base):
    """
    Document-collection context storage.

    Stores collection-specific context and metadata for documents,
    allowing different views or summaries per collection.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'document_collection_contexts'

    # Core Fields
    document_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE'), nullable=False)
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE'), nullable=False)

    # Context Data
    context_summary = Column(Text)
    context_metadata = Column(JSON)

    # Visibility Profile (from market-ui)
    visibility_profile_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('visibility_profiles.uuid', ondelete='SET NULL'),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="collection_contexts")
    collection = relationship("Collection", back_populates="document_contexts")
    visibility_profile = relationship("VisibilityProfile", foreign_keys=[visibility_profile_uuid])

    # Table Constraints
    __table_args__ = (
        Index('idx_document_collection_contexts_document_uuid', 'document_uuid'),
        Index('idx_document_collection_contexts_collection_uuid', 'collection_uuid'),
        Index('idx_document_collection_contexts_visibility_profile_uuid', 'visibility_profile_uuid'),
    )

    def __repr__(self):
        return f"<DocumentCollectionContext(uuid={self.uuid}, id='{self.id}', document_uuid={self.document_uuid}, collection_uuid={self.collection_uuid})>"


class VisibilityProfile(DualIdMixin, Base):
    """
    Graph visibility configuration profiles.

    Defines which entities and relationships are visible in graph visualizations.
    Can be shared across collections or document-specific.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'visibility_profiles'

    # Core Fields
    name = Column(Text, nullable=False)
    description = Column(Text)

    # Ownership
    owner_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='CASCADE'), nullable=False)

    # Scope (from market-ui) - Links to specific file or collection
    file_uuid = Column(UUID(as_uuid=True), ForeignKey('documents.uuid', ondelete='CASCADE', use_alter=True, name='fk_visibility_profile_document'), nullable=True)
    collection_uuid = Column(UUID(as_uuid=True), ForeignKey('collections.uuid', ondelete='CASCADE', use_alter=True, name='fk_visibility_profile_collection'), nullable=True)
    version_id = Column(Text, nullable=True)  # "DEFAULT" or collection_id

    # Profile Type (from market-ui)
    profile_type = Column(String(20), nullable=False)  # 'FILE', 'COLLECTION', 'GLOBAL'

    # Visibility Configuration
    visible_entity_types = Column(JSON)  # Array of entity types to show
    visible_relationship_types = Column(JSON)  # Array of relationship types to show
    hidden_entities = Column(JSON)  # Array of specific entity IDs to hide
    hidden_relationships = Column(JSON)  # Array of specific relationship IDs to hide

    # Extended visibility config (from market-ui)
    all_entities = Column(JSON)  # All available entity types/IDs
    enabled_entities = Column(JSON)  # Currently enabled entity types/IDs
    all_relationships = Column(JSON)  # All available relationship types
    enabled_relationships = Column(JSON)  # Currently enabled relationship types

    # Flags (from market-ui)
    auto_include_new = Column(Boolean, nullable=False, default=True)  # Auto-include new entities
    is_active = Column(Boolean, nullable=False, default=True)  # Active status

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User")
    document = relationship("Document", foreign_keys=[file_uuid])
    collection = relationship("Collection", foreign_keys=[collection_uuid])

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="visibility_profiles_name_not_empty"),
        CheckConstraint(
            "profile_type IN ('FILE', 'COLLECTION', 'GLOBAL')",
            name="visibility_profiles_valid_profile_type"
        ),
        Index('idx_visibility_profiles_owner_uuid', 'owner_uuid'),
        Index('idx_visibility_profiles_file_uuid', 'file_uuid'),
        Index('idx_visibility_profiles_collection_uuid', 'collection_uuid'),
    )

    def __repr__(self):
        return f"<VisibilityProfile(uuid={self.uuid}, id='{self.id}', name='{self.name}')>"
