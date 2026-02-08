from sqlalchemy import Column, Text, DateTime, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..config.database import Base
from .base import DualIdMixin


class Organization(DualIdMixin, Base):
    """
    Organizations represent B2B tenants in the multi-tenant system.

    Each organization is a separate tenant with its own users and documents.
    This model implements multi-tenancy at the organization level.

    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """

    __tablename__ = "organizations"

    # Core Fields
    name = Column(Text, nullable=False)
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
    users = relationship(
        "User",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "Document",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    collections = relationship(
        "Collection",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # LLM Usage Tracking
    llm_usage_records = relationship(
        "LLMUsage", back_populates="organization", lazy="dynamic"
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="organizations_name_not_empty"),
        Index("idx_organizations_name", "name"),
    )

    def __repr__(self):
        return f"<Organization(uuid={self.uuid}, id='{self.id}', name='{self.name}')>"
