# Database Entity Relationship Diagram

This document provides a complete visual representation of the database schema, including all tables, fields, data types, and relationships.

## Database Overview

The database contains **20 tables** organized into 5 functional areas:

| Module | Tables |
|--------|--------|
| Core | organizations, users, documents |
| Content | summaries, document_versions |
| Graph | graph_nodes, graph_relationships |
| Topics/Clusters | topics, document_topics, document_clusters, document_cluster_members |
| Security/GDPR | audit_log, access_log, personal_data_registry, personal_data_locations, data_subject_requests, consent_records, role_permissions, access_policies, audit_policies |

---

## Core Entity Relationship Diagram

```mermaid
erDiagram
    organizations {
        UUID id PK
        TEXT name
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    
    users {
        UUID id PK
        TEXT username UK
        TEXT email UK
        UUID org_id FK
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    
    documents {
        UUID id PK
        TEXT title
        TEXT content
        UUID owner_id FK
        UUID org_id FK
        VARCHAR50 document_type
        VARCHAR20 status
        INTEGER version
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        VARCHAR50 file_format
        INTEGER size_bytes
        INTEGER word_count
        VARCHAR50 processing_status
        VARCHAR100 source
        VARCHAR64 content_hash
        VARCHAR100 external_ref_id
        JSONB metadata
    }
    
    summaries {
        UUID id PK
        UUID document_id FK
        TEXT content
        VARCHAR50 summary_type
        VARCHAR50 target_audience
        VARCHAR100 tool_agent
        VARCHAR50 tool_version
        JSONB config_parameters
        DECIMAL confidence_score
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        INTEGER word_count
        INTEGER character_count
        VARCHAR10 language_code
        INTEGER processing_time_ms
        VARCHAR20 status
    }
    
    document_versions {
        UUID id PK
        UUID document_id FK
        INTEGER version
        TEXT content
        TEXT title
        VARCHAR20 status
        UUID modified_by FK
        TIMESTAMPTZ created_at
        TEXT change_description
        JSONB metadata
    }
    
    graph_nodes {
        UUID id PK
        UUID document_id FK
        VARCHAR50 node_type
        VARCHAR255 name
        TEXT description
        JSONB properties
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        VARCHAR100 created_by_tool
        BOOLEAN is_active
    }
    
    graph_relationships {
        UUID id PK
        UUID source_node_id FK
        UUID target_node_id FK
        UUID document_id FK
        VARCHAR50 relationship_type
        BOOLEAN is_directed
        DECIMAL weight
        DECIMAL confidence_score
        JSONB properties
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        VARCHAR100 created_by_tool
        BOOLEAN is_active
    }
    
    topics {
        UUID id PK
        VARCHAR100 name UK
        TEXT description
        TEXT_ARRAY keywords
        UUID parent_topic_id FK
        VARCHAR50 extraction_method
        DECIMAL global_importance
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        VARCHAR100 created_by_tool
        BOOLEAN is_active
    }
    
    document_topics {
        UUID id PK
        UUID document_id FK
        UUID topic_id FK
        DECIMAL relevance_score
        JSONB context
        TIMESTAMPTZ extracted_at
        TIMESTAMPTZ updated_at
        VARCHAR100 extracted_by_tool
    }
    
    document_clusters {
        UUID id PK
        VARCHAR100 name
        TEXT description
        VARCHAR50 algorithm
        JSONB parameters
        JSONB validity_metrics
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
        VARCHAR100 created_by_tool
        INTEGER version
    }
    
    document_cluster_members {
        UUID id PK
        UUID document_id FK
        UUID cluster_id FK
        DECIMAL membership_score
        DECIMAL distance_from_centroid
        TIMESTAMPTZ assignment_timestamp
        TIMESTAMPTZ updated_at
        BOOLEAN is_primary_cluster
    }

    organizations ||--o{ users : "has"
    organizations ||--o{ documents : "owns"
    users ||--o{ documents : "creates"
    users ||--o{ document_versions : "modifies"
    documents ||--o{ summaries : "has"
    documents ||--o{ document_versions : "has"
    documents ||--o| graph_nodes : "represented_by"
    documents ||--o| graph_relationships : "context_for"
    documents ||--o{ document_topics : "categorized_by"
    documents ||--o{ document_cluster_members : "grouped_in"
    graph_nodes ||--o{ graph_relationships : "source"
    graph_nodes ||--o{ graph_relationships : "target"
    topics ||--o{ document_topics : "applied_to"
    topics ||--o| topics : "parent_of"
    document_clusters ||--o{ document_cluster_members : "contains"
```

---

## Security and GDPR Tables

```mermaid
erDiagram
    audit_log {
        SERIAL id PK
        VARCHAR50 operation_type
        TEXT table_name
        INTEGER record_id
        INTEGER user_id FK
        TIMESTAMPTZ performed_at
        JSONB details
    }
    
    access_log {
        SERIAL id PK
        TEXT username
        TEXT action_type
        TIMESTAMPTZ action_time
        TEXT table_affected
        INTEGER record_id
        TEXT details
    }
    
    personal_data_registry {
        SERIAL id PK
        INTEGER user_id FK
        TEXT table_name
        TEXT column_name
        INTEGER record_id
        TEXT data_category
        TIMESTAMPTZ created_at
    }
    
    personal_data_locations {
        SERIAL id PK
        INTEGER user_id FK
        TEXT table_name
        TEXT column_name
        TEXT data_category
        TIMESTAMPTZ created_at
    }
    
    data_subject_requests {
        SERIAL id PK
        INTEGER user_id FK
        VARCHAR50 request_type
        VARCHAR50 status
        TIMESTAMPTZ requested_at
        TIMESTAMPTZ completed_at
        INTEGER handled_by FK
        JSONB request_details
        JSONB response_details
    }
    
    consent_records {
        SERIAL id PK
        INTEGER user_id FK
        TEXT consent_type
        TIMESTAMPTZ given_at
        TIMESTAMPTZ expires_at
        TEXT consent_details
        TIMESTAMPTZ withdrawal_date
    }
    
    role_permissions {
        SERIAL id PK
        TEXT role_name
        TEXT table_name
        TEXT permission_type
        TIMESTAMPTZ granted_at
        INTEGER granted_by FK
    }
    
    access_policies {
        SERIAL id PK
        TEXT role_name
        TEXT resource_name
        TEXT permission_type
        TIMESTAMPTZ created_at
        TEXT created_by
        BOOLEAN is_active
    }
    
    audit_policies {
        SERIAL id PK
        TEXT table_name
        VARCHAR50 operation_type
        BOOLEAN is_enabled
        VARCHAR50 detail_level
        INTEGER retention_days
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    users ||--o{ audit_log : "performed"
    users ||--o{ personal_data_registry : "owns_data"
    users ||--o{ personal_data_locations : "has_data"
    users ||--o{ data_subject_requests : "requests"
    users ||--o{ data_subject_requests : "handles"
    users ||--o{ consent_records : "gives"
    users ||--o{ role_permissions : "grants"
```

---

## Key Relationships Summary

| Relationship | Cardinality | Description |
|-------------|-------------|-------------|
| organizations → users | 1:N | Each organization has many users |
| organizations → documents | 1:N | Each organization owns many documents |
| users → documents | 1:N | Each user creates many documents |
| documents → summaries | 1:N | Each document can have multiple summaries |
| documents → document_versions | 1:N | Each document has version history |
| documents → graph_nodes | 1:N | Documents can be represented as graph nodes |
| documents → document_topics | M:N | Documents linked to topics via junction table |
| documents → document_cluster_members | M:N | Documents linked to clusters via junction table |
| graph_nodes → graph_relationships | N:M | Nodes connected by relationships (source/target) |
| topics → topics | 1:N | Self-referential hierarchy (parent_topic_id) |
| users → audit/security tables | 1:N | User actions tracked in security tables |

---

## Table Details by Module

### Core Module

#### organizations
Multi-tenant B2B organizations.
- **Constraints**: `name` cannot be empty

#### users  
Users belonging to organizations.
- **Constraints**: `username` not empty, valid email format
- **Unique**: `username`, `email`

#### documents
Core document storage with ownership and metadata.
- **Constraints**: `title` not empty, valid `status` (draft/published/archived/deleted), `version` > 0, valid `processing_status`

### Content Module

#### summaries
Document summaries generated by various tools/agents.
- **Constraints**: `content` not empty, `confidence_score` between 0-1, valid `status`

#### document_versions
Historical versions of documents for version control.
- **Constraints**: `title` not empty, valid `status`, `version` > 0
- **Unique**: `(document_id, version)`

### Graph Module

#### graph_nodes
Nodes for graph representation of document connections.
- **Node types**: document, concept, entity, topic, user, custom
- **Constraints**: `name` not empty

#### graph_relationships
Relationships between nodes in the document graph structure.
- **Relationship types**: references, contains, related_to, similar_to, contradicts, supports, custom
- **Constraints**: `confidence_score` between 0-1, `weight` > 0

### Topics/Clusters Module

#### topics
Topics extracted from document content for categorization.
- **Constraints**: `name` not empty, `global_importance` between 0-1, no self-reference
- **Unique**: `name`

#### document_topics
Junction table connecting documents to topics with relevance scores.
- **Constraints**: `relevance_score` between 0-1
- **Unique**: `(document_id, topic_id)`

#### document_clusters
Clusters of related documents generated by clustering algorithms.
- **Constraints**: `name` not empty, `algorithm` not empty, `version` > 0

#### document_cluster_members
Junction table connecting documents to clusters with membership scores.
- **Constraints**: `membership_score` between 0-1, `distance_from_centroid` >= 0
- **Unique**: `(document_id, cluster_id)`

### Security/GDPR Module

#### audit_log
Tracks database operations (INSERT, UPDATE, DELETE, SELECT).

#### access_log
Basic audit table for tracking access.

#### personal_data_registry / personal_data_locations
GDPR personal data tracking tables.
- **Data categories**: contact, identity, personal

#### data_subject_requests
GDPR data subject requests (erasure, export, access).

#### consent_records
GDPR consent tracking with expiration.

#### role_permissions / access_policies
Role-based access control configuration.

#### audit_policies
Audit policy configuration with retention settings.

---

## Schema Source Files

- Core schema: [`sql/schema/schema.sql`](../../sql/schema/schema.sql)
- Security schema: [`sql/security/security_schema.sql`](../../sql/security/security_schema.sql)
- Security setup: [`sql/security/security.sql`](../../sql/security/security.sql)
- GDPR: [`sql/gdpr/gdpr.sql`](../../sql/gdpr/gdpr.sql)

