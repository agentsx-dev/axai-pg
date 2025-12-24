from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..config.database import Base
from .base import DualIdMixin

class Role(DualIdMixin, Base):
    """
    Role definitions with normalized role management.

    From market-ui integration - defines available roles in the system
    with descriptions and optional legacy permissions field.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'roles'

    # Core Fields
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    permissions = Column(Text)  # Legacy comma-separated permissions

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", lazy="dynamic")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="roles_name_not_empty"),
        Index('idx_roles_name', 'name'),
    )

    def __repr__(self):
        return f"<Role(uuid={self.uuid}, id='{self.id}', name='{self.name}')>"

class UserRole(DualIdMixin, Base):
    """
    Model for user role assignments.

    Updated to reference Role table via role_id for normalized role management.
    Maintains backward compatibility with role_name field.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'user_roles'

    user_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='CASCADE'), nullable=False)
    role_uuid = Column(UUID(as_uuid=True), ForeignKey('roles.uuid', ondelete='CASCADE'), nullable=False)
    role_name = Column(Text, nullable=False)  # Legacy field for backward compatibility
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid'))

    # Relationships
    user = relationship("User", foreign_keys=[user_uuid])
    assigner = relationship("User", foreign_keys=[assigned_by_uuid])
    role = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        UniqueConstraint('user_uuid', 'role_uuid', name='uq_user_role'),
        Index('idx_user_roles_user_uuid', 'user_uuid'),
        Index('idx_user_roles_role_uuid', 'role_uuid'),
    )

class RolePermission(DualIdMixin, Base):
    """
    Model for role-based permissions.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'role_permissions'
    role_name = Column(Text, nullable=False)
    resource_name = Column(Text, nullable=False)
    permission_type = Column(Text, nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid'))
    
    # Relationships
    granter = relationship("User", foreign_keys=[granted_by_uuid])
    
    __table_args__ = (
        CheckConstraint(
            "permission_type IN ('READ', 'CREATE', 'UPDATE', 'DELETE')",
            name='valid_permission_type'
        ),
        UniqueConstraint('role_name', 'resource_name', 'permission_type', 
                        name='uq_role_permission'),
    )

class AuditLog(DualIdMixin, Base):
    """
    Unified audit logging (merged from AccessLog).

    Renamed fields for clarity and consistency with market-ui:
    - action_type → action
    - table_affected → resource_type
    - record_id → resource_id
    - details: Text → JSON for structured data
    Added user_id FK in addition to username for better referential integrity.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'audit_logs'

    user_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='SET NULL'), nullable=True)
    username = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    action_time = Column(DateTime(timezone=True), server_default=func.now())
    resource_type = Column(Text, nullable=False)
    resource_uuid = Column(UUID(as_uuid=True))  # Can reference records from different tables
    details = Column(JSON)  # Changed from Text to JSON for structured logging

    # Relationships
    user = relationship("User")

    # Table Constraints
    __table_args__ = (
        Index('idx_audit_logs_user_uuid', 'user_uuid'),
        Index('idx_audit_logs_action_time', 'action_time'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
    )

    def __repr__(self):
        return f"<AuditLog(uuid={self.uuid}, id='{self.id}', username='{self.username}', action='{self.action}')>"

class RateLimit(DualIdMixin, Base):
    """
    Model for rate limiting.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'rate_limits'

    user_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='CASCADE'), nullable=False)
    action_type = Column(Text, nullable=False)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    count = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_uuid', 'action_type', 'window_start', 
                        name='uq_rate_limit'),
    )

class SecurityPolicy(DualIdMixin, Base):
    """
    Model for security policies.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'security_policies'

    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    policy_type = Column(Text, nullable=False)
    policy_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid'))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by_uuid])
    
    __table_args__ = (
        CheckConstraint(
            "policy_type IN ('ACCESS_CONTROL', 'DATA_PROTECTION', 'AUDIT', 'RATE_LIMIT')",
            name='valid_policy_type'
        ),
    )
