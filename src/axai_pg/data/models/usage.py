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

    # TODO: Implement fields in US-002

    def __repr__(self):
        return f"<LLMUsage(uuid={self.uuid}, id='{self.id}')>"


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

    # TODO: Implement fields in US-003

    def __repr__(self):
        return f"<LLMModelPricing(uuid={self.uuid}, id='{self.id}')>"
