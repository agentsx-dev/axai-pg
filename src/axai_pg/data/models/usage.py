"""
LLM Usage Tracking Models.

This module contains SQLAlchemy models for tracking LLM token usage and model pricing.
These tables support rate limiting, quota enforcement, and usage analytics.

Tables:
    - llm_usage: Stores per-operation token usage linked to documents, users, and organizations.
    - llm_model_pricing: Stores model pricing configuration for cost estimation.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..config.database import Base
from .base import DualIdMixin


class LLMUsage(DualIdMixin, Base):
    """
    LLM token usage tracking per operation.

    Records token consumption for each LLM operation, linked to documents, users,
    and organizations. Supports queries for rate limiting (tokens used by user in
    last hour) and quota enforcement (total tokens this month by org).

    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'llm_usage'

    # Foreign Keys
    document_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('documents.uuid', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('users.uuid', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    org_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.uuid', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # Operation Classification
    operation_type = Column(String(50), nullable=False)
    tool_name = Column(String(100), nullable=True)
    model_name = Column(String(100), nullable=False, index=True)
    model_provider = Column(String(50), nullable=True)

    # Token Usage
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    # Optional Fields
    processing_time_seconds = Column(Numeric(10, 3), nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    job_id = Column(String(100), nullable=True)
    usage_metadata = Column(JSONB, name='metadata', nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="llm_usage_records")
    user = relationship("User", back_populates="llm_usage_records")
    organization = relationship("Organization", back_populates="llm_usage_records")

    # Table Constraints
    __table_args__ = (
        # Non-negative token constraints
        CheckConstraint("input_tokens >= 0", name="llm_usage_input_tokens_non_negative"),
        CheckConstraint("output_tokens >= 0", name="llm_usage_output_tokens_non_negative"),
        CheckConstraint("total_tokens >= 0", name="llm_usage_total_tokens_non_negative"),
        # Valid operation_type constraint
        CheckConstraint(
            "operation_type IN ('summary', 'graph_extraction', 'text_cleaning', 'email_analysis', 'other')",
            name="llm_usage_valid_operation_type"
        ),
        # Indexes
        Index('idx_llm_usage_document_uuid', 'document_uuid'),
        Index('idx_llm_usage_user_uuid', 'user_uuid'),
        Index('idx_llm_usage_org_uuid', 'org_uuid'),
        Index('idx_llm_usage_created_at', 'created_at'),
        Index('idx_llm_usage_operation_type', 'operation_type'),
        Index('idx_llm_usage_model_name', 'model_name'),
        # Composite indexes for rate limiting queries
        Index('idx_llm_usage_user_created', 'user_uuid', 'created_at'),
        Index('idx_llm_usage_org_created', 'org_uuid', 'created_at'),
    )

    def __repr__(self):
        return f"<LLMUsage(uuid={self.uuid}, id='{self.id}', operation_type='{self.operation_type}', total_tokens={self.total_tokens})>"


class LLMModelPricing(DualIdMixin, Base):
    """
    LLM model pricing configuration.

    Stores pricing information for LLM models to enable cost estimation.
    Supports time-based pricing with effective_from/effective_until fields
    for tracking pricing changes over time.

    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'llm_model_pricing'

    # Model Identification
    model_name = Column(String(100), nullable=False, unique=True)
    model_provider = Column(String(50), nullable=True)

    # Pricing (cost per 1,000 tokens)
    input_cost_per_1k = Column(Numeric(10, 6), nullable=False)
    output_cost_per_1k = Column(Numeric(10, 6), nullable=False)

    # Validity Period
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Table Constraints
    __table_args__ = (
        Index('idx_llm_model_pricing_model_name', 'model_name'),
        Index('idx_llm_model_pricing_effective_period', 'effective_from', 'effective_until'),
    )

    def __repr__(self):
        return f"<LLMModelPricing(uuid={self.uuid}, id='{self.id}', model_name='{self.model_name}')>"
