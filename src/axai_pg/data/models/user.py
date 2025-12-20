from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..config.database import Base
from .base import DualIdMixin

class User(DualIdMixin, Base):
    """
    Users can belong to organizations and can own documents.

    Supports both organizational (multi-tenant) and non-organizational users.
    Users can own documents, create document versions, and have authentication credentials.

    Fields from market-ui integration:
    - hashed_password: For local authentication
    - is_active: Account activation status
    - is_admin: Administrator privileges
    - is_email_verified: Email verification status
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'users'

    # Core Fields
    username = Column(Text, nullable=False, unique=True)
    email = Column(Text, nullable=False, unique=True)

    # Organization (nullable to support non-organizational users from market-ui)
    org_uuid = Column(UUID(as_uuid=True), ForeignKey('organizations.uuid', ondelete='CASCADE'), nullable=True)

    # Authentication Fields (from market-ui)
    hashed_password = Column(Text, nullable=True)  # Nullable for external auth providers
    is_active = Column(Boolean, nullable=False, server_default='true')
    is_admin = Column(Boolean, nullable=False, server_default='false')
    is_email_verified = Column(Boolean, nullable=False, server_default='false')

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    owned_documents = relationship("Document", back_populates="owner", lazy="dynamic")
    document_versions = relationship("DocumentVersion", back_populates="created_by", lazy="dynamic")

    # Additional relationships (from market-ui)
    collections = relationship("Collection", back_populates="owner", lazy="dynamic")
    tokens = relationship("Token", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    feedback_submissions = relationship("Feedback", back_populates="user", lazy="dynamic")

    # Role relationship (from market-ui) - read-only through UserRole table
    roles = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.uuid == UserRole.user_id",
        secondaryjoin="UserRole.role_id == Role.uuid",
        viewonly=True,  # Read-only since we use UserRole directly for writes
        lazy="select"
    )

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(username)) > 0", name="users_username_not_empty"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="users_email_valid"
        ),
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_org_id', 'org_id'),
    )

    def __repr__(self):
        return f"<User(uuid={self.uuid}, id='{self.id}', username='{self.username}', org_uuid={self.org_uuid})>"
