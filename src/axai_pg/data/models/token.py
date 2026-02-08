from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..config.database import Base


class Token(Base):
    """
    JWT token management for authentication.

    From market-ui integration - tracks issued tokens with revocation support.
    Uses JTI (JWT ID) as primary key for efficient token lookups.
    """

    __tablename__ = "tokens"

    # Primary Key (JTI - JWT ID)
    id = Column(Text, primary_key=True)

    # Core Fields
    token_type = Column(Text, nullable=False)
    user_uuid = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid", ondelete="CASCADE"), nullable=False
    )

    # Token Lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_revoked = Column(Boolean, nullable=False, default=False)

    # Relationships
    user = relationship("User", back_populates="tokens")

    # Table Constraints
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="tokens_id_not_empty"),
        CheckConstraint(
            "length(trim(token_type)) > 0", name="tokens_token_type_not_empty"
        ),
        Index("idx_tokens_user_uuid", "user_uuid"),
        Index("idx_tokens_expires_at", "expires_at"),
        Index("idx_tokens_is_revoked", "is_revoked"),
    )

    def __repr__(self):
        return f"<Token(id='{self.id}', user_uuid={self.user_uuid}, token_type='{self.token_type}')>"
