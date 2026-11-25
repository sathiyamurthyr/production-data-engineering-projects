# Performance & Scaling Guide

## 1. Read-Time vs Write-Time Reasoning
- **Materialized Inferred Edges (`inferred = 1`):** Inverse and transitive closure edges are computed during pipeline ingestion (`materialize_transitive_closures()`), making read queries and GraphRAG N-hop traversals $O(\text{edges})$ index lookups without recursive SQL CTEs at query time.
- **Tradeoff:** Slight write-time overhead on deep hierarchies (`SUBSIDIARY_OF`), negligible for typical corporate trees (<10k entities).

## 2. Indexed Graph Access in SQLite
- Composite primary key `(subject_uri, predicate, object_uri)` prevents duplicate edges idempotently.
- Secondary indexes on `kg_nodes(class_name)`, `kg_edges(subject_uri)`, and `kg_edges(object_uri)` keep 1–3 hop BFS traversals fast.

## 3. Scaling Beyond Single-Node SQLite
- Export directly via `export_cypher()` into **Neo4j** (index-free adjacency for 10M+ node multi-hop traversals) or via `export_turtle()` into **Amazon Neptune / GraphDB / Stardog** for SPARQL federation.
