"""
AXAI PostgreSQL Models Package
"""

from .data.config.database import DatabaseManager, PostgresConnectionConfig
from .data.models import (
    Organization,
    User,
    Document,
    DocumentVersion,
    Summary,
    Topic,
    GraphEntity,
    GraphRelationship,
    DocumentTopic,
    Collection,
    VisibilityProfile,
)

__version__ = "0.6.0"
