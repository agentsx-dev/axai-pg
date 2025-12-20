from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, Index, Boolean, Table, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from ..config.database import Base

# Association table for many-to-many relationship between documents and collections
document_collection_association = Table(
    'document_collection_association',
    Base.metadata,
    Column('document_id', UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), primary_key=True),
    Column('collection_id', UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True),
    Column('added_at', DateTime(timezone=True), nullable=False, server_default=func.now())
)

class Collection(Base):
    """
    Collections group documents together for organization and graph generation.

    Supports both organizational (multi-tenant) and non-organizational usage.
    Collections can generate merged entity views and manage visibility profiles.
    """
    __tablename__ = 'collections'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    name = Column(Text, nullable=False)
    description = Column(Text)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)

    # Hierarchy (from market-ui)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE', use_alter=True, name='fk_collection_parent'), nullable=True)

    # Soft Delete (from market-ui)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Graph Generation Status
    is_graph_generated = Column(Boolean, nullable=False, default=False)
    graph_generated_at = Column(DateTime(timezone=True))

    # Visibility Profile (from market-ui)
    default_visibility_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey('visibility_profiles.id', ondelete='SET NULL'),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="collections")
    organization = relationship("Organization", back_populates="collections")
    documents = relationship("Document", secondary=document_collection_association, back_populates="collections", lazy="dynamic")
    collection_entities = relationship("CollectionEntity", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    collection_relationships = relationship("CollectionRelationship", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    entity_operations = relationship("EntityOperation", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    document_contexts = relationship("DocumentCollectionContext", back_populates="collection", lazy="dynamic", cascade="all, delete-orphan")
    graph_entities = relationship("GraphEntity", back_populates="source_collection", lazy="dynamic")
    graph_relationships = relationship("GraphRelationship", back_populates="source_collection", lazy="dynamic")
    default_visibility_profile = relationship("VisibilityProfile", foreign_keys=[default_visibility_profile_id])

    # Hierarchical relationships (from market-ui)
    parent = relationship("Collection", remote_side=[id], back_populates="subcollections")
    subcollections = relationship("Collection", back_populates="parent", lazy="dynamic", cascade="all")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="collections_name_not_empty"),
        Index('idx_collections_owner_id', 'owner_id'),
        Index('idx_collections_org_id', 'org_id'),
        Index('idx_collections_is_graph_generated', 'is_graph_generated'),
        Index('idx_collections_parent_id', 'parent_id'),
        Index('idx_collections_is_deleted', 'is_deleted'),
        Index('idx_collections_default_visibility_profile_id', 'default_visibility_profile_id'),
    )

    def __repr__(self):
        return f"<Collection(id={self.id}, name='{self.name}')>"

    @property
    def files(self):
        """Alias for documents relationship - backward compatibility with market-ui."""
        return self.documents.all()


class SourceType(enum.Enum):
    """Enum for entity/relationship source types"""
    file = "file"
    collection_generated = "collection_generated"
    document = "document"


class CollectionEntity(Base):
    """
    Merged entity views within a collection.

    Entities can be merged from multiple source files within a collection,
    providing a unified view of entities across documents.
    """
    __tablename__ = 'collection_entities'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    entity_id = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)

    # Merged Data
    name = Column(Text, nullable=False)
    description = Column(Text)
    properties = Column(JSON)

    # Source Tracking
    source_entity_ids = Column(JSON)  # Array of original entity IDs that were merged

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="collection_entities")
    entity_links = relationship("EntityLink", back_populates="collection_entity", lazy="dynamic", cascade="all, delete-orphan")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(entity_id)) > 0", name="collection_entities_entity_id_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="collection_entities_name_not_empty"),
        Index('idx_collection_entities_collection_id', 'collection_id'),
        Index('idx_collection_entities_entity_id', 'entity_id'),
        Index('idx_collection_entities_entity_type', 'entity_type'),
    )

    def __repr__(self):
        return f"<CollectionEntity(id={self.id}, entity_id='{self.entity_id}', name='{self.name}')>"


class CollectionRelationship(Base):
    """
    Collection-scoped relationships between merged entities.

    Tracks relationships within a collection context,
    potentially merging relationships from multiple source files.
    """
    __tablename__ = 'collection_relationships'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    source_entity_id = Column(Text, nullable=False)
    target_entity_id = Column(Text, nullable=False)
    relationship_type = Column(Text, nullable=False)

    # Metadata
    description = Column(Text)
    properties = Column(JSON)

    # Source Tracking
    source_relationship_ids = Column(JSON)  # Array of original relationship IDs

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="collection_relationships")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(source_entity_id)) > 0", name="collection_relationships_source_not_empty"),
        CheckConstraint("length(trim(target_entity_id)) > 0", name="collection_relationships_target_not_empty"),
        Index('idx_collection_relationships_collection_id', 'collection_id'),
        Index('idx_collection_relationships_source', 'source_entity_id'),
        Index('idx_collection_relationships_target', 'target_entity_id'),
    )

    def __repr__(self):
        return f"<CollectionRelationship(collection_id={self.collection_id}, {self.source_entity_id} -> {self.target_entity_id})>"


class EntityLink(Base):
    """
    Cross-file entity linking within collections.

    Links entities from individual files to merged collection entities,
    enabling tracking of which source entities contribute to merged views.
    """
    __tablename__ = 'entity_links'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    graph_entity_id = Column(UUID(as_uuid=True), ForeignKey('graph_entities.id', ondelete='CASCADE'), nullable=False)
    collection_entity_id = Column(UUID(as_uuid=True), ForeignKey('collection_entities.id', ondelete='CASCADE'), nullable=False)

    # Collection Context (from market-ui)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)

    # Link Metadata
    confidence_score = Column(Integer)  # 0-100 confidence in the link
    link_type = Column(Text)  # e.g., "exact_match", "fuzzy_match", "manual"

    # Merge State (from market-ui)
    is_active = Column(Boolean, nullable=False, default=True)  # Active/inactive state
    merged_entity_id = Column(UUID(as_uuid=True), ForeignKey('collection_entities.id', ondelete='SET NULL'), nullable=True)  # Result of merge

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    graph_entity = relationship("GraphEntity", back_populates="entity_links")
    collection_entity = relationship("CollectionEntity", back_populates="entity_links")
    collection = relationship("Collection", foreign_keys=[collection_id])
    merged_entity = relationship("CollectionEntity", foreign_keys=[merged_entity_id])

    # Table Constraints
    __table_args__ = (
        Index('idx_entity_links_graph_entity_id', 'graph_entity_id'),
        Index('idx_entity_links_collection_entity_id', 'collection_entity_id'),
        Index('idx_entity_links_collection_id', 'collection_id'),
        Index('idx_entity_links_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<EntityLink(graph_entity_id={self.graph_entity_id}, collection_entity_id={self.collection_entity_id})>"


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


class EntityOperation(Base):
    """
    Operation audit trail for entity management.

    Tracks all operations performed on entities within collections,
    including merges, splits, and manual edits.
    """
    __tablename__ = 'entity_operations'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(SQLEnum(OperationType), nullable=False)
    entity_id = Column(Text, nullable=False)

    # Operation Details
    description = Column(Text)
    details = Column(JSON)  # Structured operation details

    # Actor
    performed_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Timestamp
    performed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    collection = relationship("Collection", back_populates="entity_operations")
    performed_by = relationship("User")

    # Table Constraints
    __table_args__ = (
        Index('idx_entity_operations_collection_id', 'collection_id'),
        Index('idx_entity_operations_entity_id', 'entity_id'),
        Index('idx_entity_operations_performed_at', 'performed_at'),
    )

    def __repr__(self):
        return f"<EntityOperation(id={self.id}, operation_type={self.operation_type}, entity_id='{self.entity_id}')>"


class DocumentCollectionContext(Base):
    """
    Document-collection context storage.

    Stores collection-specific context and metadata for documents,
    allowing different views or summaries per collection.
    """
    __tablename__ = 'document_collection_contexts'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)

    # Context Data
    context_summary = Column(Text)
    context_metadata = Column(JSON)

    # Visibility Profile (from market-ui)
    visibility_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey('visibility_profiles.id', ondelete='SET NULL'),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="collection_contexts")
    collection = relationship("Collection", back_populates="document_contexts")
    visibility_profile = relationship("VisibilityProfile", foreign_keys=[visibility_profile_id])

    # Table Constraints
    __table_args__ = (
        Index('idx_document_collection_contexts_document_id', 'document_id'),
        Index('idx_document_collection_contexts_collection_id', 'collection_id'),
        Index('idx_document_collection_contexts_visibility_profile_id', 'visibility_profile_id'),
    )

    def __repr__(self):
        return f"<DocumentCollectionContext(document_id={self.document_id}, collection_id={self.collection_id})>"


class VisibilityProfile(Base):
    """
    Graph visibility configuration profiles.

    Defines which entities and relationships are visible in graph visualizations.
    Can be shared across collections or document-specific.
    """
    __tablename__ = 'visibility_profiles'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Fields
    name = Column(Text, nullable=False)
    description = Column(Text)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Scope (from market-ui) - Links to specific file or collection
    file_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE', use_alter=True, name='fk_visibility_profile_document'), nullable=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id', ondelete='CASCADE', use_alter=True, name='fk_visibility_profile_collection'), nullable=True)
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
    document = relationship("Document", foreign_keys=[file_id])
    collection = relationship("Collection", foreign_keys=[collection_id])

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="visibility_profiles_name_not_empty"),
        CheckConstraint(
            "profile_type IN ('FILE', 'COLLECTION', 'GLOBAL')",
            name="visibility_profiles_valid_profile_type"
        ),
        Index('idx_visibility_profiles_owner_id', 'owner_id'),
        Index('idx_visibility_profiles_file_id', 'file_id'),
        Index('idx_visibility_profiles_collection_id', 'collection_id'),
    )

    def __repr__(self):
        return f"<VisibilityProfile(id={self.id}, name='{self.name}')>"
