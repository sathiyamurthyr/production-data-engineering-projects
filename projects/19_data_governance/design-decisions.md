# Design Decisions: Data Governance, RBAC & Lineage

This document explains the technical trade-offs and architectural design decisions made during the implementation of the Data Governance Framework.

---

## 1. Lineage DAG Graph Representation: Custom Directed Graph vs. NetworkX

### Context
Data lineage requires modeling data dependencies as a Directed Acyclic Graph (DAG) to trace upstream sources (root causes) and downstream consumers (impact analysis).

### Decision
We implemented a custom, lightweight directed graph utilizing adjacency lists (`self._adjacency_out` and `self._adjacency_in`) rather than importing Python's heavy `networkx` library directly into the main lineage engine.

| Attribute | Custom Directed Graph (Chosen) | NetworkX Library |
|---|---|---|
| **Memory Footprint** | Extremely low (built-in Python `dict` and `set`). | Moderate. |
| **Dependencies** | Zero external dependencies. | Installs large numeric libraries. |
| **Traversal Speed** | O(V + E) using localized, highly optimized recursion. | O(V + E) but with generic wrapper overhead. |
| **Integration** | Easy to serialize directly to JSON. | Requires intermediate converters. |

### Rationale
A custom implementation ensures zero external runtime dependency bloat for simple lineage traversal, while matching the mathematical execution profile of standard graph traversal engines.

---

## 2. In-Memory vs. Database-Backed Metadata Search

### Context
A metadata catalog must handle high-throughput read/search operations for data discovery.

### Decision
We chose a **hybrid model**:
1. SQLite persistent storage for column schemas, business glossaries, and tag audits.
2. In-memory data structures for fast operational lineage and RBAC mappings during transient process runs.

### Rationale
SQLite provides single-file relational persistence that works perfectly out-of-the-box in distributed containers without the operational overhead of running PostgreSQL or Elasticsearch clusters. For high-throughput analytics, queries can easily run on indexing structures or memory caches.

---

## 3. Dynamic In-Flight Masking vs. Static Anonymization

### Context
Protecting PII can be done statically (overwriting database columns) or dynamically (masking data during SQL execution).

### Decision
We implemented **dynamic, in-flight masking** within `PolicyEngine`. Static anonymization is reserved solely for data retention enforcement (via GDPR RTBF workflows).

### Rationale
- **Static Anonymization** permanently destroys information density, rendering historical datasets unusable for machine learning or aggregations.
- **Dynamic Masking** allows data to be stored securely in its raw state (confidential cloud buckets) while applying role-specific hashing or redaction policies at the API query boundaries based on user identities.

---

## 4. Security Model: RBAC vs. Attribute-Based Access Control (ABAC)

### Context
Access to data assets must be managed at column, table, and row levels.

### Decision
We built a **hybrid security model**:
- **Role-Based Access Control (RBAC)** maps users to security clearance tiers (`DATA_ADMIN`, `DATA_ANALYST`, etc.).
- **Attribute-Based Access Control (ABAC)** maps data assets to attributes (sensitivity levels, database domains).
- The `PolicyEngine` combines both inputs dynamically: checking if the user's role permissions (RBAC) allow viewing the specific asset sensitivity tag (ABAC).

### Rationale
Pure RBAC leads to role explosion (e.g. `MKTG_EMAIL_VIEWER`, `FIN_EMAIL_VIEWER`). Integrating asset attributes (e.g. `sensitivity_level="RESTRICTED"`) allows a static set of roles to secure a dynamic set of data assets.
