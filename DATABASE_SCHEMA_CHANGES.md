# Database Schema Redesign - Changes Summary

**Date:** December 20, 2025  
**Status:** Completed

## Overview

This document summarizes all changes made to the database schema to implement dual ID fields (UUID for internal use, 8-character string for UI), add document status tracking flags, replace JSON arrays with proper junction tables, and remove deprecated SQL files.

---

## 1. Dual ID Pattern Implementation

### New Mixin: `DualIdMixin`

**File:** `src/axai_pg/data/models/base.py`

Created a new mixin that provides two identification fields:
- `uuid`: UUID primary key for all foreign key relationships (internal use)
- `id`: 8-character string extracted from the last 8 characters of the UUID (UI display)

The short ID is automatically generated before insert using a SQLAlchemy event listener.

### Models Updated with Dual ID Pattern

All models now inherit from `DualIdMixin` and use the dual ID pattern:

1. **Document** and **DocumentVersion**
2. **Collection**, **CollectionEntity**, **CollectionRelationship**, **EntityLink**, **EntityOperation**, **DocumentCollectionContext**, **VisibilityProfile**
3. **GraphEntity** and **GraphRelationship**
4. **User** and **Organization**
5. **Topic** and **DocumentTopic**
6. **Summary**
7. **Feedback**
8. **Role**, **UserRole**, **RolePermission**, **AuditLog**, **RateLimit**, **SecurityPolicy**

**Exception:** `Token` model retains `id` as Text (JTI) for JWT token management.

---

## 2. Foreign Key Updates

All foreign key references updated from `table.id` to `table.uuid`:

```python
# Old
owner_id = Column(UUID, ForeignKey('users.id'))

# New
owner_id = Column(UUID, ForeignKey('users.uuid'))
```

### Files Modified:
- `document.py`: References to users, organizations, visibility_profiles
- `collection.py`: References to users, organizations, documents, collections (self-referential)
- `graph.py`: References to documents, collections, graph_entities
- `topic.py`: References to topics (self-referential), documents
- `summary.py`: References to documents
- `feedback.py`: References to users
- `security.py`: References to users, roles
- `token.py`: References to users

---

## 3. Document Model Enhancements

**File:** `src/axai_pg/data/models/document.py`

### New Status Flags (for quick filtering without JOINs):
```python
has_summary = Column(Boolean, nullable=False, default=False)
has_graph = Column(Boolean, nullable=False, default=False)
has_versions = Column(Boolean, nullable=False, default=False)
```

### New Extraction Metadata:
```python
extraction_started_at = Column(DateTime(timezone=True))
extraction_completed_at = Column(DateTime(timezone=True))
extraction_error = Column(Text)
```

**Application Impact:** Application code should update these flags when:
- Creating/deleting summaries → update `has_summary`
- Creating/deleting graph entities → update `has_graph`
- Creating document versions → update `has_versions`

---

## 4. Collection Model Enhancements

**File:** `src/axai_pg/data/models/collection.py`

### New Cache Count Fields (for performance):
```python
entity_count = Column(Integer, nullable=False, default=0)
relationship_count = Column(Integer, nullable=False, default=0)
document_count = Column(Integer, nullable=False, default=0)
```

**Application Impact:** Update these counts when:
- Adding/removing entities/relationships in collections
- Adding/removing documents from collections

---

## 5. Junction Tables Replace JSON Arrays

### 5.1 CollectionEntitySource

Replaces `source_entity_ids` JSON array in `CollectionEntity`:

```python
class CollectionEntitySource(Base):
    __tablename__ = 'collection_entity_sources'
    
    collection_entity_uuid = Column(UUID, ForeignKey('collection_entities.uuid'), primary_key=True)
    source_graph_entity_uuid = Column(UUID, ForeignKey('graph_entities.uuid'), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Indexes:**
- `idx_collection_entity_sources_collection_entity` on `collection_entity_uuid`
- `idx_collection_entity_sources_source_entity` on `source_graph_entity_uuid`

### 5.2 CollectionRelationshipSource

Replaces `source_relationship_ids` JSON array in `CollectionRelationship`:

```python
class CollectionRelationshipSource(Base):
    __tablename__ = 'collection_relationship_sources'
    
    collection_relationship_uuid = Column(UUID, ForeignKey('collection_relationships.uuid'), primary_key=True)
    source_graph_relationship_uuid = Column(UUID, ForeignKey('graph_relationships.uuid'), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Indexes:**
- `idx_collection_relationship_sources_collection_rel` on `collection_relationship_uuid`
- `idx_collection_relationship_sources_source_rel` on `source_graph_relationship_uuid`

### Relationship Updates

Added SQLAlchemy relationships for the new junction tables:

**In CollectionEntity:**
```python
source_entities = relationship("GraphEntity", 
                              secondary="collection_entity_sources", 
                              back_populates="collection_entities_using", 
                              lazy="dynamic")
```

**In CollectionRelationship:**
```python
source_relationships = relationship("GraphRelationship", 
                                   secondary="collection_relationship_sources", 
                                   back_populates="collection_relationships_using", 
                                   lazy="dynamic")
```

**In GraphEntity:**
```python
collection_entities_using = relationship("CollectionEntity", 
                                        secondary="collection_entity_sources", 
                                        back_populates="source_entities", 
                                        lazy="dynamic")
```

**In GraphRelationship:**
```python
collection_relationships_using = relationship("CollectionRelationship", 
                                             secondary="collection_relationship_sources", 
                                             back_populates="source_relationships", 
                                             lazy="dynamic")
```

---

## 6. Deprecated Files Removed

### Deleted SQL Files and Directories:
- `sql/schema/schema.sql` (replaced by SQLAlchemy models)
- `sql/schema/*.md` (analysis documentation)
- `sql/gdpr/` (entire directory)
- `sql/security/` (entire directory)
- `sql/sample_data/` (entire directory)
- `sql/migrations/` (entire directory)
- `migrations/` (sqitch migration files)

**Rationale:** All schema definitions are now in SQLAlchemy models. Tables are generated directly from Python code, eliminating the need for separate SQL files.

---

## 7. Model Exports Updated

**File:** `src/axai_pg/data/models/__init__.py`

Added new models to exports:
- `DualIdMixin`
- `CollectionEntitySource`
- `CollectionRelationshipSource`

---

## 8. Application Code Migration Guide

### 8.1 ID Field Access

**OLD CODE:**
```python
document = session.query(Document).first()
print(document.id)  # UUID object
```

**NEW CODE:**
```python
document = session.query(Document).first()
print(document.uuid)  # UUID object (for FK relationships, internal use)
print(document.id)    # String (8 chars, for UI display)
```

### 8.2 Foreign Key Relationships

**OLD CODE:**
```python
# Query by ID
doc = session.query(Document).filter(Document.id == some_uuid).first()

# Create with FK
summary = Summary(document_id=doc.id, ...)
```

**NEW CODE:**
```python
# Query by UUID (internal)
doc = session.query(Document).filter(Document.uuid == some_uuid).first()

# Query by short ID (UI)
doc = session.query(Document).filter(Document.id == "a1b2c3d4").first()

# Create with FK (use uuid field)
summary = Summary(document_id=doc.uuid, ...)
```

### 8.3 API/UI Serialization

**Recommendation:**
```python
def serialize_document(doc):
    return {
        "id": doc.id,           # 8-char string for UI
        "uuid": str(doc.uuid),  # Full UUID for API calls if needed
        "title": doc.title,
        # ... other fields
    }
```

### 8.4 Querying Junction Tables

**OLD CODE (JSON array):**
```python
collection_entity = session.query(CollectionEntity).first()
source_ids = collection_entity.source_entity_ids  # JSON array
```

**NEW CODE (proper JOIN):**
```python
# Get source entities through junction table
collection_entity = session.query(CollectionEntity).first()
source_entities = collection_entity.source_entities.all()

# Or manual query
from axai_pg.data.models import CollectionEntitySource

sources = session.query(GraphEntity)\
    .join(CollectionEntitySource, 
          CollectionEntitySource.source_graph_entity_uuid == GraphEntity.uuid)\
    .filter(CollectionEntitySource.collection_entity_uuid == collection_entity.uuid)\
    .all()
```

### 8.5 Updating Document Flags

```python
# When creating a summary
summary = Summary(document_id=doc.uuid, ...)
session.add(summary)
doc.has_summary = True
session.commit()

# When creating graph entities
entity = GraphEntity(document_id=doc.uuid, ...)
session.add(entity)
doc.has_graph = True
session.commit()

# When creating versions
version = DocumentVersion(document_id=doc.uuid, ...)
session.add(version)
doc.has_versions = True
session.commit()
```

### 8.6 Updating Collection Counts

```python
# When adding entities
collection.entity_count += 1

# When adding relationships
collection.relationship_count += 1

# When adding documents
collection.document_count += 1

session.commit()
```

---

## 9. Database Migration Notes

**Since this is a fresh database (no migration needed):**

1. Drop existing database (if any)
2. Run SQLAlchemy's `Base.metadata.create_all(engine)` to create all tables
3. Tables will be created with the new dual ID structure
4. Junction tables will be created automatically

**Sample initialization code:**
```python
from sqlalchemy import create_engine
from axai_pg.data.models import Base
from axai_pg.data.config.database import get_engine

engine = get_engine()
Base.metadata.create_all(engine)
```

---

## 10. Breaking Changes Summary

| Change | Old Behavior | New Behavior | Action Required |
|--------|--------------|--------------|-----------------|
| Primary Key | `id` is UUID PK | `uuid` is UUID PK, `id` is 8-char string | Update all FK references from `.id` to `.uuid` |
| ID Display | Convert UUID to string | Use `.id` field directly | Update UI code to use `.id` |
| Source Entity IDs | JSON array in `source_entity_ids` | Junction table `collection_entity_sources` | Update queries to use JOIN |
| Source Relationship IDs | JSON array in `source_relationship_ids` | Junction table `collection_relationship_sources` | Update queries to use JOIN |
| Document Status | Query JOINs to check | Boolean flags: `has_summary`, `has_graph`, `has_versions` | Update flags when creating/deleting related records |

---

## 11. Testing Checklist

- [ ] Verify all models create tables successfully
- [ ] Test dual ID generation (uuid → id)
- [ ] Verify FK constraints work with uuid fields
- [ ] Test junction table queries for collection entities
- [ ] Test junction table queries for collection relationships
- [ ] Verify document status flags update correctly
- [ ] Test collection count cache updates
- [ ] Verify all relationships work correctly
- [ ] Test soft references (remote_side using uuid)
- [ ] Check that Token model still works (special case)

---

## 12. Files Modified

### Created:
- `src/axai_pg/data/models/base.py` - Added `DualIdMixin`

### Modified:
- `src/axai_pg/data/models/document.py`
- `src/axai_pg/data/models/collection.py`
- `src/axai_pg/data/models/graph.py`
- `src/axai_pg/data/models/user.py`
- `src/axai_pg/data/models/organization.py`
- `src/axai_pg/data/models/topic.py`
- `src/axai_pg/data/models/summary.py`
- `src/axai_pg/data/models/token.py`
- `src/axai_pg/data/models/feedback.py`
- `src/axai_pg/data/models/security.py`
- `src/axai_pg/data/models/__init__.py`

### Deleted:
- `sql/schema/schema.sql`
- `sql/schema/*.md`
- `sql/gdpr/` (directory)
- `sql/security/` (directory)
- `sql/sample_data/` (directory)
- `sql/migrations/` (directory)
- `migrations/` (directory)

---

## 13. Repository Layer Updates (COMPLETED)

### BaseRepository Changes (`src/axai_pg/data/repositories/base_repository.py`)

**New Methods Added:**
- `find_by_uuid(uuid: UUID)` - Find entity by UUID (internal primary key)
- `find_by_short_id(short_id: str)` - Find entity by 8-char short ID (for UI)
- `find_by_id(id_value: Union[UUID, str])` - Flexible lookup that auto-detects UUID vs short ID
- `to_dict(entity: T, include_uuid: bool = False)` - Serialization helper for API responses

**Updated Method Signatures:**
- `update(uuid: UUID, entity: Dict[str, Any])` - Now takes UUID instead of int
- `delete(uuid: UUID)` - Now takes UUID instead of int

**Import Changes:**
```python
from uuid import UUID
from typing import Union
```

### DocumentRepository Changes (`src/axai_pg/data/repositories/document_repository.py`)

**Updated Method Signatures:**
- `find_by_organization(org_uuid: UUID, ...)` - Takes org UUID
- `find_by_owner(owner_uuid: UUID, ...)` - Takes owner UUID
- `find_by_topic(topic_uuid: UUID, ...)` - Takes topic UUID
- `find_related_documents(document_uuid: UUID, ...)` - Takes document UUID
- `create_with_summary(...)` - Updates document with `has_summary = True`
- `update_with_version(uuid: UUID, ...)` - Takes document UUID, sets `has_versions = True`
- `search(query: str, org_uuid: UUID, ...)` - Takes org UUID
- `find_by_status(status: str, org_uuid: UUID, ...)` - Takes org UUID

**Foreign Key Column Updates:**
All FK column references updated to use `_uuid` suffix:
- `Document.org_id` → `Document.org_uuid`
- `Document.owner_id` → `Document.owner_uuid`
- `DocumentTopic.topic_id` → `DocumentTopic.topic_uuid`
- Graph relationship queries updated to use UUID columns

**Status Flag Updates:**
Methods now properly set document status flags:
- `create_with_summary()` sets `has_summary = True`
- `update_with_version()` sets `has_versions = True`
- Graph entity creation should set `has_graph = True` (when implemented)

### Test Updates (`src/axai_pg/data/repositories/tests/test_document_repository.py`)

All tests updated to:
- Use UUIDs instead of integers for IDs
- Test both `find_by_uuid()` and `find_by_short_id()` methods
- Verify short ID is 8 characters
- Use `_uuid` suffix for FK column names
- Test `to_dict()` serialization with and without UUID
- Use UUID parameters in all repository method calls

**New Test Added:**
- `test_to_dict_serialization()` - Tests serialization helper with and without UUID inclusion

## 14. Next Steps

1. ~~**Update Repository Layer:** Modify repository classes to use `.uuid` for FK operations and `.id` for UI responses~~ ✅ COMPLETED
2. **Update API Endpoints:** Ensure API serialization uses `.id` for user-facing IDs
3. **Update Tests:** Rewrite integration tests to account for dual ID pattern
4. **Update Documentation:** Revise API documentation to reflect new ID structure
5. **Database Initialization:** Create fresh database with new schema


---

**End of Changes Summary**

