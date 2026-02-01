from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, Integer, DateTime, String, event
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid as uuid_lib

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

class DualIdMixin:
    """
    Mixin that provides dual identification fields:
    - uuid: UUID primary key used for all foreign key relationships (internal)
    - id: 8-character string derived from uuid for UI display (external)

    This pattern allows efficient UUID-based relationships internally while
    providing short, user-friendly IDs for UI/API consumption.
    """

    @declared_attr
    def uuid(cls):
        """UUID primary key for internal use and foreign key relationships."""
        return Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4, nullable=False)

    @declared_attr
    def id(cls):
        """8-character string ID for UI display, derived from last 8 chars of UUID."""
        return Column(String(8), unique=True, nullable=False, index=True)

    def __init__(self, **kwargs):
        """Initialize with auto-generated short ID from UUID if not provided."""
        # If uuid is provided but id is not, generate id from uuid
        if 'uuid' in kwargs and 'id' not in kwargs:
            uuid_val = kwargs['uuid']
            kwargs['id'] = str(uuid_val).replace('-', '')[-8:]
        # If neither uuid nor id provided, generate both
        elif 'uuid' not in kwargs and 'id' not in kwargs:
            new_uuid = uuid_lib.uuid4()
            kwargs['uuid'] = new_uuid
            kwargs['id'] = str(new_uuid).replace('-', '')[-8:]
        super().__init__(**kwargs)

class BaseModel(Base):
    """Base model class that includes common columns."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 