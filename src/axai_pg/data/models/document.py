from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
import uuid
from ..config.database import Base
from .base import DualIdMixin


class Document(DualIdMixin, Base):
    """
    Unified document/file storage with ownership and metadata.

    Merges concepts from:
    - axai-pg: Documents with content, summaries, topics
    - market-ui: Files with storage metadata, collections, graph visualization

    Supports both organizational (multi-tenant) and non-organizational usage.
    Includes file storage metadata, versioning, summaries, topics, and graph relationships.

    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """

    __tablename__ = "documents"

    # Core Identification Fields
    title = Column(Text, nullable=False)
    filename = Column(
        Text, nullable=False, index=True
    )  # From market-ui: File storage name

    # Content (nullable for binary files)
    content = Column(Text, nullable=True)  # Made nullable for binary file support

    # Ownership & Organization (both nullable for flexibility)
    owner_uuid = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid", ondelete="CASCADE"), nullable=False
    )
    org_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.uuid", ondelete="CASCADE"),
        nullable=True,
    )  # Nullable for non-org

    # File Storage Metadata (from market-ui)
    file_path = Column(Text, nullable=False)  # Physical/cloud storage path
    size = Column(Integer, nullable=False)  # File size in bytes (market-ui 'size')
    content_type = Column(Text, nullable=False)  # MIME type

    # Document Classification
    document_type = Column(String(50), nullable=False)
    file_format = Column(String(50))  # File extension or format

    # Status & Processing
    status = Column(
        String(20), nullable=False, default="draft"
    )  # draft/published/archived/deleted
    processing_status = Column(
        String(50), default="pending"
    )  # pending/processing/complete/error
    is_deleted = Column(
        Boolean, nullable=False, default=False
    )  # From market-ui: Soft delete flag
    deleted_at = Column(DateTime(timezone=True))  # From market-ui: Deletion timestamp

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    version_id = Column(
        String
    )  # From market-ui: Version identifier (collection_id or "DEFAULT")
    description = Column(Text)  # From market-ui: Document description

    # Content Analysis (from axai-pg)
    word_count = Column(Integer)
    content_hash = Column(String(64))

    # Source & References
    source = Column(String(100))  # Origin system
    external_ref_id = Column(String(100))  # External reference ID

    # Search & Metadata (from market-ui)
    topics = Column(Text)  # Legacy: Comma-separated topics
    tags = Column(JSON)  # Array of tags
    key_terms = Column(JSON)  # Array of key terms
    linked_docs = Column(JSON)  # Array of linked document IDs
    summary = Column(Text)  # Quick summary text (separate from Summary table)

    # Legacy Graph Data (from market-ui - deprecated, use graph_entities table)
    graph_nodes = Column(JSON)  # Legacy graph nodes
    graph_relationships = Column(JSON)  # Legacy graph relationships

    # Graph Management (from market-ui)
    default_visibility_profile_uuid = Column(
        UUID(as_uuid=True), ForeignKey("visibility_profiles.uuid")
    )
    entities_last_updated = Column(DateTime(timezone=True))
    relationships_last_updated = Column(DateTime(timezone=True))

    # Processing Status Flags (for quick filtering)
    has_summary = Column(Boolean, nullable=False, default=False)
    has_graph = Column(Boolean, nullable=False, default=False)
    has_versions = Column(Boolean, nullable=False, default=False)

    # User Processing Preferences (from upload options)
    summarize_on_upload = Column(
        Boolean, nullable=False, default=True
    )  # Whether to generate summary
    generate_graph_on_upload = Column(
        Boolean, nullable=False, default=True
    )  # Whether to generate graph

    # Extraction Metadata
    extraction_started_at = Column(DateTime(timezone=True))
    extraction_completed_at = Column(DateTime(timezone=True))
    extraction_error = Column(Text)

    # Summarization Status (pending/processing/complete/failed/not_requested)
    summarization_status = Column(String(20), default="pending")
    summarization_started_at = Column(DateTime(timezone=True))
    summarization_completed_at = Column(DateTime(timezone=True))
    summarization_error = Column(Text)

    # Graph Generation Status (pending/processing/complete/failed/not_requested)
    graph_generation_status = Column(String(20), default="pending")
    graph_generation_started_at = Column(DateTime(timezone=True))
    graph_generation_completed_at = Column(DateTime(timezone=True))
    graph_generation_error = Column(Text)

    # Document Chunking Fields
    # For large documents that exceed processing thresholds, the document is split into chunks.
    # Parent documents have is_chunked=True and chunk_count set.
    # Child chunks have parent_document_uuid, chunk_index, and total_chunks set.
    parent_document_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_chunked = Column(Boolean, default=False, nullable=False, server_default="false")
    chunk_count = Column(Integer, nullable=True)  # Number of chunks (parent only)
    chunk_index = Column(Integer, nullable=True)  # 0-based index (chunks only)
    total_chunks = Column(Integer, nullable=True)  # Total chunks in set (chunks only)
    character_count = Column(
        Integer, nullable=True
    )  # Character count of extracted text
    chunking_status = Column(
        String(20), nullable=True
    )  # pending/processing/complete/failed
    chunking_error = Column(
        String(500), nullable=True
    )  # Error message if chunking failed

    # Metadata
    document_metadata = Column(JSONB, name="metadata")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    owner = relationship("User", back_populates="owned_documents")
    organization = relationship("Organization", back_populates="documents")
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    summaries = relationship(
        "Summary",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    topics_rel = relationship(
        "DocumentTopic",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    graph_entity = relationship(
        "GraphEntity",
        back_populates="document",
        foreign_keys="GraphEntity.document_uuid",
        uselist=False,
        cascade="all, delete-orphan",
    )
    graph_relationships_rel = relationship(
        "GraphRelationship",
        back_populates="document",
        foreign_keys="GraphRelationship.document_uuid",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # From market-ui
    collections = relationship(
        "Collection",
        secondary="file_collection_association",
        back_populates="documents",
        lazy="dynamic",
    )
    graph_entities = relationship(
        "GraphEntity",
        back_populates="source_file",
        lazy="dynamic",
        foreign_keys="GraphEntity.source_file_uuid",
    )
    collection_contexts = relationship(
        "DocumentCollectionContext",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    default_visibility_profile = relationship(
        "VisibilityProfile", foreign_keys=[default_visibility_profile_uuid]
    )

    # LLM Usage Tracking
    llm_usage_records = relationship(
        "LLMUsage",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Document Chunking Relationships (self-referential)
    # - chunks: Get child chunks from parent document (lazy load - could be many)
    # - parent_document: Get parent document from chunk (eager load via selectin)
    chunks = relationship(
        "Document",
        backref=backref("parent_document", lazy="selectin", uselist=False),
        remote_side="Document.uuid",
        foreign_keys=[parent_document_uuid],
        lazy="select",
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="documents_title_not_empty"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'deleted')",
            name="documents_valid_status",
        ),
        CheckConstraint("version > 0", name="documents_valid_version"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'complete', 'error')",
            name="documents_valid_processing_status",
        ),
        Index("idx_documents_org_uuid", "org_uuid"),
        Index("idx_documents_owner_uuid", "owner_uuid"),
        Index("idx_documents_type", "document_type"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_org_status", "org_uuid", "status"),
        Index("idx_documents_is_deleted", "is_deleted"),
        Index("idx_documents_version_id", "version_id"),
    )

    def __repr__(self):
        return f"<Document(uuid={self.uuid}, id='{self.id}', title='{self.title}', version={self.version})>"


class DocumentVersion(DualIdMixin, Base):
    """Historical versions of documents for version control."""

    __tablename__ = "document_versions"

    # Core Fields
    document_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)
    created_by_uuid = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    change_description = Column(Text)
    doc_metadata = Column(JSON)

    # File Storage Metadata (from market-ui FileVersion)
    file_path = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="versions")
    created_by = relationship("User", back_populates="document_versions")

    # Unique constraint for document_id and version combination
    __table_args__ = (
        CheckConstraint("version > 0", name="document_versions_valid_version"),
    )

    def __repr__(self):
        return f"<DocumentVersion(uuid={self.uuid}, id='{self.id}', document_uuid={self.document_uuid}, version={self.version})>"
