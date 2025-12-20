from sqlalchemy import Column, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..config.database import Base
from .base import DualIdMixin

class Feedback(DualIdMixin, Base):
    """
    User feedback submission storage.

    From market-ui integration - captures user feedback with context.
    Supports both authenticated (user_id) and anonymous (user_email) feedback.
    
    Uses dual ID pattern:
    - uuid: UUID primary key for internal use and FK relationships
    - id: 8-character string for UI display
    """
    __tablename__ = 'feedback'

    # Core Fields
    type = Column(Text, nullable=False)
    description = Column(Text, nullable=False)

    # Context and Metadata
    page_context = Column(JSON, nullable=True)

    # User Identification (one of these should be populated)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey('users.uuid', ondelete='SET NULL'), nullable=True)
    user_email = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="feedback_submissions")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(type)) > 0", name="feedback_type_not_empty"),
        CheckConstraint("length(trim(description)) > 0", name="feedback_description_not_empty"),
        Index('idx_feedback_user_uuid', 'user_uuid'),
        Index('idx_feedback_type', 'type'),
        Index('idx_feedback_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Feedback(uuid={self.uuid}, id='{self.id}', type='{self.type}', user_uuid={self.user_uuid})>"
