# Database Entity Relationship Diagram

This document provides a complete visual representation of the database schema, including all tables, fields, data types, and relationships.

## Database Overview

The database contains **27 tables** organized into 7 functional areas:

| Module | Tables |
|--------|--------|
| Core | `organizations`, `users` |
| Documents | `documents`, `document_versions` |
| Content Analysis | `summaries`, `topics`, `document_topics` |
| Graph | `graph_entities`, `graph_relationships` |
| Collections | `collections`, `file_collection_association`, `collection_entities`, `collection_relationships`, `collection_entity_sources`, `collection_relationship_sources`, `entity_links`, `entity_operations`, `document_collection_contexts`, `visibility_profiles` |
| Security | `roles`, `user_roles`, `role_permissions`, `audit_logs`, `rate_limits`, `security_policies` |
| Other | `tokens`, `feedback` |

---

## Complete Entity Relationship Diagram

This diagram shows all 27 tables and their relationships:

```mermaid
erDiagram
    organizations {
        uuid uuid
    }
    users {
        uuid uuid
    }
    documents {
        uuid uuid
    }
    document_versions {
        uuid uuid
    }
    summaries {
        uuid uuid
    }
    topics {
        uuid uuid
    }
    document_topics {
        uuid uuid
    }
    graph_entities {
        uuid uuid
    }
    graph_relationships {
        uuid uuid
    }
    collections {
        uuid uuid
    }
    file_collection_association {
        uuid file_id
    }
    collection_entities {
        uuid uuid
    }
    collection_relationships {
        uuid uuid
    }
    collection_entity_sources {
        uuid collection_entity_uuid
    }
    collection_relationship_sources {
        uuid collection_relationship_uuid
    }
    entity_links {
        uuid uuid
    }
    entity_operations {
        uuid uuid
    }
    document_collection_contexts {
        uuid uuid
    }
    visibility_profiles {
        uuid uuid
    }
    roles {
        uuid uuid
    }
    user_roles {
        uuid uuid
    }
    role_permissions {
        uuid uuid
    }
    audit_logs {
        uuid uuid
    }
    rate_limits {
        uuid uuid
    }
    security_policies {
        uuid uuid
    }
    tokens {
        text id
    }
    feedback {
        uuid uuid
    }

    organizations ||--o{ users : "has"
    organizations ||--o{ documents : "owns"
    organizations ||--o{ collections : "owns"
    users ||--o{ documents : "owns"
    users ||--o{ document_versions : "creates"
    users ||--o{ collections : "owns"
    users ||--o{ tokens : "has"
    users ||--o{ feedback : "submits"
    users ||--o{ user_roles : "has"
    users ||--o{ audit_logs : "performs"
    users ||--o{ rate_limits : "tracked"
    users ||--o{ visibility_profiles : "owns"
    documents ||--o{ document_versions : "has_history"
    documents ||--o{ summaries : "has"
    documents ||--o{ document_topics : "categorized_by"
    documents ||--o{ graph_entities : "source_for"
    documents ||--o{ graph_relationships : "source_for"
    documents ||--o{ document_collection_contexts : "has_contexts"
    documents ||--o{ file_collection_association : "belongs_to"
    topics ||--o{ document_topics : "applied_to"
    topics ||--o| topics : "parent_of"
    graph_entities ||--o{ graph_relationships : "source"
    graph_entities ||--o{ graph_relationships : "target"
    graph_entities ||--o{ entity_links : "linked_by"
    graph_entities ||--o{ collection_entity_sources : "merged_into"
    graph_relationships ||--o{ collection_relationship_sources : "contributes_to"
    collections ||--o{ file_collection_association : "contains"
    collections ||--o{ collection_entities : "has"
    collections ||--o{ collection_relationships : "has"
    collections ||--o{ entity_operations : "tracked_by"
    collections ||--o{ document_collection_contexts : "provides_context"
    collections ||--o{ graph_entities : "generates"
    collections ||--o{ graph_relationships : "generates"
    collections ||--o{ entity_links : "scopes"
    collections ||--o| collections : "parent_of"
    collection_entities ||--o{ entity_links : "linked_by"
    collection_entities ||--o{ collection_entity_sources : "sourced_from"
    collection_relationships ||--o{ collection_relationship_sources : "sourced_from"
    entity_links ||--o{ collection_entities : "creates_merge"
    visibility_profiles ||--o{ documents : "applied_to"
    visibility_profiles ||--o{ collections : "applied_to"
    visibility_profiles ||--o{ document_collection_contexts : "used_in"
    roles ||--o{ user_roles : "assigned_via"
```

---

## Detailed Table Schemas

### Core Module

```mermaid
erDiagram
    organizations {
        uuid uuid PK
        string id UK
        text name
        timestamp created_at
        timestamp updated_at
    }
    users {
        uuid uuid PK
        string id UK
        text username UK
        text email UK
        uuid org_uuid FK
        text hashed_password
        boolean is_active
        boolean is_admin
        boolean is_email_verified
        timestamp created_at
        timestamp updated_at
    }
    organizations ||--o{ users : "has"
```

---

### Documents Module

```mermaid
erDiagram
    documents {
        uuid uuid PK
        string id UK
        text title
        text filename
        text content
        uuid owner_uuid FK
        uuid org_uuid FK
        text file_path
        integer size
        text content_type
        string document_type
        string file_format
        string status
        string processing_status
        boolean is_deleted
        timestamp deleted_at
        integer version
        text version_id
        text description
        integer word_count
        string content_hash
        string source
        string external_ref_id
        text topics
        json tags
        json key_terms
        json linked_docs
        text summary
        json graph_nodes
        json graph_relationships
        uuid default_visibility_profile_uuid FK
        timestamp entities_last_updated
        timestamp relationships_last_updated
        boolean has_summary
        boolean has_graph
        boolean has_versions
        timestamp extraction_started_at
        timestamp extraction_completed_at
        text extraction_error
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }
    document_versions {
        uuid uuid PK
        string id UK
        uuid document_uuid FK
        integer version
        text content
        text title
        string status
        uuid created_by_uuid FK
        text change_description
        json doc_metadata
        text file_path
        text content_type
        timestamp created_at
    }
    documents ||--o{ document_versions : "has_history"
```

---

### Content Analysis Module

```mermaid
erDiagram
    summaries {
        uuid uuid PK
        string id UK
        uuid document_uuid FK
        text content
        string summary_type
        string target_audience
        string tool_agent
        string tool_version
        json config_parameters
        decimal confidence_score
        integer word_count
        integer character_count
        string language_code
        integer processing_time_ms
        string status
        timestamp created_at
        timestamp updated_at
    }
    topics {
        uuid uuid PK
        string id UK
        string name UK
        text description
        array keywords
        uuid parent_topic_uuid FK
        string extraction_method
        decimal global_importance
        string created_by_tool
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    document_topics {
        uuid uuid PK
        string id UK
        uuid document_uuid FK
        uuid topic_uuid FK
        decimal relevance_score
        json context
        string extracted_by_tool
        timestamp extracted_at
        timestamp updated_at
    }
    topics ||--o{ document_topics : "applied_to"
    topics ||--o| topics : "parent_of"
```

---

### Graph Module

```mermaid
erDiagram
    graph_entities {
        uuid uuid PK
        string id UK
        text entity_id
        string entity_type
        string name
        text description
        json properties
        enum source_type
        uuid source_file_uuid FK
        uuid source_collection_uuid FK
        uuid document_uuid FK
        string created_by_tool
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    graph_relationships {
        uuid uuid PK
        string id UK
        uuid source_entity_uuid FK
        uuid target_entity_uuid FK
        text relationship_id
        string relationship_type
        enum source_type
        uuid source_file_uuid FK
        uuid source_collection_uuid FK
        uuid document_uuid FK
        boolean is_directed
        decimal weight
        decimal confidence_score
        json properties
        string created_by_tool
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    graph_entities ||--o{ graph_relationships : "source"
    graph_entities ||--o{ graph_relationships : "target"
```

---

### Collections Module - Core Tables

```mermaid
erDiagram
    collections {
        uuid uuid PK
        string id UK
        text name
        text description
        uuid owner_uuid FK
        uuid org_uuid FK
        uuid parent_uuid FK
        boolean is_deleted
        timestamp deleted_at
        boolean is_graph_generated
        timestamp graph_generated_at
        uuid default_visibility_profile_uuid FK
        integer entity_count
        integer relationship_count
        integer document_count
        string graph_state
        text entities_hash
        timestamp last_sync_timestamp
        timestamp created_at
        timestamp updated_at
    }
    file_collection_association {
        uuid file_id PK_FK
        uuid collection_id PK_FK
        timestamp added_at
    }
    collection_entities {
        uuid uuid PK
        string id UK
        uuid collection_uuid FK
        text entity_id
        text entity_type
        text name
        text display_name
        text description
        json properties
        json source_entity_ids
        boolean is_merged
        uuid created_from_link_uuid FK
        string lifecycle_state
        uuid operation_lock
        timestamp created_at
        timestamp updated_at
    }
    collection_relationships {
        uuid uuid PK
        string id UK
        uuid collection_uuid FK
        text source_entity_id
        text target_entity_id
        text relationship_type
        text description
        json properties
        timestamp created_at
        timestamp updated_at
    }
    collections ||--o{ file_collection_association : "contains"
    collections ||--o{ collection_entities : "has"
    collections ||--o{ collection_relationships : "has"
    collections ||--o| collections : "parent_of"
```

---

### Collections Module - Junction and Supporting Tables

```mermaid
erDiagram
    collection_entity_sources {
        uuid collection_entity_uuid PK_FK
        uuid source_graph_entity_uuid PK_FK
        timestamp created_at
    }
    collection_relationship_sources {
        uuid collection_relationship_uuid PK_FK
        uuid source_graph_relationship_uuid PK_FK
        timestamp created_at
    }
    entity_links {
        uuid uuid PK
        string id UK
        uuid graph_entity_uuid FK
        uuid collection_entity_uuid FK
        uuid collection_uuid FK
        text entity_type
        integer confidence_score
        text link_type
        json linked_entities
        boolean is_active
        uuid merged_entity_uuid FK
        text common_name
        text description
        string created_by_tool
        timestamp created_at
        timestamp updated_at
    }
    entity_operations {
        uuid uuid PK
        string id UK
        uuid collection_uuid FK
        enum operation_type
        text entity_id
        text description
        json details
        uuid performed_by_uuid FK
        json entity_ids
        json operation_data
        uuid user_uuid FK
        string status
        timestamp performed_at
    }
    document_collection_contexts {
        uuid uuid PK
        string id UK
        uuid document_uuid FK
        uuid collection_uuid FK
        text context_summary
        json context_metadata
        uuid visibility_profile_uuid FK
        timestamp created_at
        timestamp updated_at
    }
    visibility_profiles {
        uuid uuid PK
        string id UK
        text name
        text description
        uuid owner_uuid FK
        uuid file_uuid FK
        uuid collection_uuid FK
        text version_id
        string profile_type
        json visible_entity_types
        json visible_relationship_types
        json hidden_entities
        json hidden_relationships
        json all_entities
        json enabled_entities
        json all_relationships
        json enabled_relationships
        boolean auto_include_new
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
```

---

### Security Module

```mermaid
erDiagram
    roles {
        uuid uuid PK
        string id UK
        text name UK
        text description
        text permissions
        timestamp created_at
        timestamp updated_at
    }
    user_roles {
        uuid uuid PK
        string id UK
        uuid user_uuid FK
        uuid role_uuid FK
        text role_name
        timestamp assigned_at
        uuid assigned_by_uuid FK
    }
    role_permissions {
        uuid uuid PK
        string id UK
        text role_name
        text resource_name
        text permission_type
        timestamp granted_at
        uuid granted_by_uuid FK
    }
    audit_logs {
        uuid uuid PK
        string id UK
        uuid user_uuid FK
        text username
        text action
        timestamp action_time
        text resource_type
        uuid resource_uuid
        json details
    }
    rate_limits {
        uuid uuid PK
        string id UK
        uuid user_uuid FK
        text action_type
        timestamp window_start
        integer count
    }
    security_policies {
        uuid uuid PK
        string id UK
        text name UK
        text description
        text policy_type
        json policy_data
        uuid created_by_uuid FK
        timestamp created_at
        timestamp updated_at
    }
    roles ||--o{ user_roles : "assigned_via"
```

---

### Other Tables

```mermaid
erDiagram
    tokens {
        text id PK
        text token_type
        uuid user_uuid FK
        timestamp expires_at
        timestamp created_at
        boolean is_revoked
    }
    feedback {
        uuid uuid PK
        string id UK
        text type
        text description
        json page_context
        uuid user_uuid FK
        text user_email
        timestamp created_at
        timestamp updated_at
    }
```

---

## Key Relationships Summary

| Relationship | Cardinality | Description |
|-------------|-------------|-------------|
| organizations → users | 1:N | Multi-tenant user ownership |
| organizations → documents | 1:N | Multi-tenant document ownership |
| users → documents | 1:N | Document authorship |
| users → roles | M:N | Role-based access control via `user_roles` |
| documents → summaries | 1:N | AI-generated summaries |
| documents → document_versions | 1:N | Version history |
| documents ↔ topics | M:N | Topic categorization via `document_topics` |
| documents ↔ collections | M:N | Collection membership via `file_collection_association` |
| documents → graph_entities | 1:N | Entity extraction |
| graph_entities → graph_relationships | N:M | Graph edges (source/target) |
| collections → collection_entities | 1:N | Merged entity views |
| collection_entities ↔ graph_entities | M:N | Source tracking via `collection_entity_sources` |
| collections → collections | 1:N | Hierarchical collections (parent_uuid) |
| topics → topics | 1:N | Topic hierarchy (parent_topic_uuid) |

---

## Table Details by Module

### Core Module

#### organizations
Multi-tenant B2B organizations.
- **Constraints**: `name` cannot be empty
- **Unique**: `uuid`, `id`

#### users
Users with optional organization membership.
- **Constraints**: `username` not empty, valid email format
- **Unique**: `uuid`, `id`, `username`, `email`
- **Notes**: Supports both organizational and non-organizational users

### Documents Module

#### documents
Unified document/file storage with comprehensive metadata.
- **Constraints**: `title` not empty, valid `status`, `version` > 0, valid `processing_status`
- **Features**: Soft delete, version tracking, graph metadata, file storage info

#### document_versions
Historical versions for document version control.
- **Constraints**: `version` > 0

### Content Analysis Module

#### summaries
AI-generated document summaries.
- **Constraints**: `confidence_score` between 0-1, valid `status`

#### topics
Hierarchical topic taxonomy.
- **Constraints**: `global_importance` between 0-1, no self-reference
- **Unique**: `name`

#### document_topics
Junction table for document-topic relationships.
- **Constraints**: `relevance_score` between 0-1

### Graph Module

#### graph_entities
Entities extracted from documents for knowledge graph.
- **Source types**: file, collection_generated, document
- **Features**: Multi-source tracking, active/inactive state

#### graph_relationships
Edges connecting graph entities.
- **Constraints**: `confidence_score` between 0-1, `weight` > 0
- **Features**: Directed/undirected, multi-source tracking

### Collections Module

#### collections
Document groupings with graph generation capabilities.
- **Features**: Hierarchical (parent_uuid), soft delete, graph state management
- **Constraints**: `name` not empty

#### collection_entities
Merged entity views within a collection scope.
- **Features**: Lifecycle state management, merge tracking, concurrency control

#### collection_relationships
Merged relationship views within a collection.

#### entity_links
Cross-file entity linking for merge tracking.

#### entity_operations
Audit trail for entity management operations.
- **Operation types**: created, merged, split, deleted, updated, unmerged, link, unlink, initialize_graph, sync_graph

#### document_collection_contexts
Document-specific context within a collection.

#### visibility_profiles
Graph visualization configuration.
- **Profile types**: FILE, COLLECTION, GLOBAL

### Security Module

#### roles
Role definitions for RBAC.
- **Unique**: `name`

#### user_roles
User-role assignments.
- **Unique**: (`user_uuid`, `role_uuid`)

#### role_permissions
Fine-grained permission assignments.
- **Permission types**: READ, CREATE, UPDATE, DELETE

#### audit_logs
Unified audit logging for security compliance.

#### rate_limits
API rate limiting tracking.

#### security_policies
Configurable security policies.
- **Policy types**: ACCESS_CONTROL, DATA_PROTECTION, AUDIT, RATE_LIMIT

### Other

#### tokens
JWT token tracking with revocation support.
- **Primary Key**: JTI (JWT ID) as text

#### feedback
User feedback submissions.
- **Features**: Supports authenticated and anonymous feedback

---

## Dual ID Pattern

All models (except `Token` and junction tables) use the **Dual ID Pattern**:

| Field | Type | Purpose |
|-------|------|---------|
| `uuid` | UUID | Primary key for internal use and foreign key relationships |
| `id` | VARCHAR(8) | Short ID derived from UUID for UI display (last 8 chars of UUID hex) |

This pattern enables:
- Efficient UUID-based joins internally
- User-friendly short IDs for APIs and UIs
- Consistent referencing across the application

---

## Schema Management

The database schema is managed through SQLAlchemy models in `src/axai_pg/data/models/`.

**Model Files:**
- `base.py` - Base classes and DualIdMixin
- `organization.py` - Organization model
- `user.py` - User model
- `document.py` - Document and DocumentVersion models
- `summary.py` - Summary model
- `topic.py` - Topic and DocumentTopic models
- `graph.py` - GraphEntity and GraphRelationship models
- `collection.py` - All collection-related models
- `security.py` - Security and RBAC models
- `token.py` - JWT Token model
- `feedback.py` - Feedback model

Schema is created programmatically using `PostgreSQLSchemaBuilder` from `src/axai_pg/utils/schema_builder.py`.

See [`CLAUDE.md`](../../CLAUDE.md) for development workflow documentation.
