# Architecture Design: Data Governance, RBAC & Lineage

This document explains the technical architecture, database schemas, and data flow patterns of the Data Governance Framework.

---

## 1. Architectural Blueprint

The system follows a modular, decoupled architecture where each capability (Cataloging, Classification, Lineage, Access Control, and Compliance) operates independently but shares a common database-backed physical metadata layer.

```
       [ Data Pipelines / Crawlers ]
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │         Metadata Catalog            │ <─── [ SQLite Database ]
  │  (DataCatalog, MetadataManager)     │       ├── data_assets
  └──────────────────┬──────────────────┘       ├── catalog_entries
                     │                          ├── asset_tags
                     ▼                          ├── business_glossary
  ┌─────────────────────────────────────┐       ├── sensitivity_audit
  │      Classification Engine          │       └── (lineage in-memory/JSON)
  │  (PIIDetector, DataClassifier)      │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │       Lineage Graph (DAG)           │ ───> [ Mermaid / JSON Exports ]
  │  (LineageTracker, LineageGraph)     │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │     RBAC & Masking Engine           │ <─── [ Audit Logger ]
  │  (RBACManager, PolicyEngine)        │
  └──────────────────┬──────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │      Compliance & Lifecycles        │ ───> [ SAR & Erasure Reports ]
  │  (GDPRChecker, RetentionManager)    │
  └─────────────────────────────────────┘
```

---

## 2. Database Schema Definition (SQLite)

The framework maintains persistent schemas inside SQLite for metadata inventory, audit logging, and terms mappings:

### 1. `data_assets` (Column-level Registry)
Represents physical table columns cataloged during ingestion.
- `asset_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `database_name`: TEXT NOT NULL
- `schema_name`: TEXT NOT NULL
- `table_name`: TEXT NOT NULL
- `column_name`: TEXT NOT NULL
- `data_type`: TEXT NOT NULL
- `description`: TEXT
- `owner`: TEXT
- `business_domain`: TEXT
- `sensitivity_level`: TEXT (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)
- `last_updated`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- *Unique Constraint*: (`database_name`, `schema_name`, `table_name`, `column_name`)

### 2. `catalog_entries` (Table-level Logical Registry)
Represents logical tables or datasets registered in the catalog.
- `asset_id`: TEXT PRIMARY KEY
- `asset_name`: TEXT NOT NULL
- `domain`: TEXT NOT NULL
- `owner`: TEXT NOT NULL
- `asset_type`: TEXT NOT NULL (table, view, file)
- `sensitivity_level`: TEXT NOT NULL
- `storage_location`: TEXT
- `description`: TEXT
- `schema_fields`: TEXT (JSON string mapping of columns to data types)
- `tags`: TEXT (JSON string array of tags)
- `created_at`: TEXT

### 3. `asset_tags` (Key-Value Tag Registry)
Enables semantic indexing of columns (e.g. key="PII", value="EMAIL").
- `tag_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `asset_id`: INTEGER (FK -> `data_assets.asset_id` ON DELETE CASCADE)
- `tag_key`: TEXT NOT NULL
- `tag_value`: TEXT NOT NULL
- `added_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- *Unique Constraint*: (`asset_id`, `tag_key`)

### 4. `business_glossary` (Business Glossary Catalog)
Stores common domain vocabularies, owners, and categorization.
- `term_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `term_name`: TEXT NOT NULL UNIQUE
- `definition`: TEXT NOT NULL
- `category`: TEXT NOT NULL
- `owner`: TEXT NOT NULL
- `sensitivity_level`: TEXT DEFAULT 'PUBLIC'
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 5. `sensitivity_audit` (Audit Logging for Tag Overrides)
Enforces accountability for manual classification overrides.
- `audit_id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `asset_id`: INTEGER (FK -> `data_assets.asset_id` ON DELETE CASCADE)
- `old_sensitivity`: TEXT NOT NULL
- `new_sensitivity`: TEXT NOT NULL
- `changed_by`: TEXT NOT NULL
- `reason`: TEXT
- `changed_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 3. Component Details & Design Goals

### Metadata Catalog Layer
- **Unified Catalog**: Supports database tables, schemas, columns, and logical catalog entries.
- **Searchable Index**: Built-in SQL pattern queries scan across database names, tables, and description fields.

### PII Classification Engine
- **Confidence Scoring**: Regular expressions compute a confidence score weighted by match ratio in sample rows.
- **Dynamic Catalog Registration**: Registers column schemas automatically if columns are not found in the index prior to tag updates.

### Lineage Tracker & Graph Traversal
- **Decoupled Edge Logging**: Decouples the tracking of edges (pipeline metrics, execution IDs) from the graph engine.
- **Directed Graph Representation**: A clean directed graph structure inside `LineageGraph` allows quick parent-child node traversal.
- **Cycle Detection**: Validates lineage DAGs using Depth-First Search (DFS) recursion checks to block pipeline dependency circular loops.

### RBAC Access Policy Engine
- **Role Assignments**: Maps users to logical system roles: `DATA_ADMIN`, `DATA_ENGINEER`, `DATA_ANALYST`, `DATA_STEWARD`, `DATA_VIEWER`.
- **Dynamic Masking Policies**: Implements Attribute-Based Access Control (ABAC) to partially mask, hash, or redact fields at query runtime.

### Compliance & Data Retention Lifecycle
- **GDPR Checkers**: Implements automated subject erasure and SAR reporting queries across multiple mock datasets.
- **Retention Lifecycle Managers**: Computes the age of assets and schedules automated purging, archiving, or locking schedules based on domain rules.
