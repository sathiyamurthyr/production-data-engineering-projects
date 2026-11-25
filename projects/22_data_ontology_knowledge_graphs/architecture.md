# Architecture: Enterprise Data Ontology & Knowledge Graphs

## 1. Why an Ontology Layer Above the Medallion Lakehouse?

Silver and Gold tables solve storage and batch aggregation, but business semantics remain scattered across SQL joins, dbt models, and BI dashboards. An **Enterprise Ontology** defines a single shared contract:
- **Object Types (Classes):** `LegalEntity` (abstract) -> `Customer`, `Merchant`, `Product`, `Order`, `PaymentTransaction`.
- **Link Types (Relationships):** `PLACED_ORDER`, `CONTAINS_PRODUCT`, `SOLD_BY`, `SETTLED_BY`, `SUBSIDIARY_OF` with explicit `domain`, `range`, `cardinality`, `inverse`, and `transitive` rules.
- **Canonical URIs:** Every resolved entity receives a stable URN (`urn:de:ontology:customer:cust_...`) independent of source-system auto-increment IDs.

## 2. Fail-Closed Governance & Inference

1. **Pre-write Validation:** Every `upsert_node()` and `add_edge()` call validates required properties, types, enum domains, and relationship domain/range inheritance before touching SQLite.
2. **RDFS-style Subclass Querying:** Querying `LegalEntity` with `include_subclasses=True` automatically returns both `Customer` and `Merchant` nodes.
3. **Materialized Reasoning:** Inverse links (`PLACED_BY`, `PARENT_OF`) and transitive links (`SUBSIDIARY_OF`) are materialized with `inferred = 1` so downstream queries stay fast and distinguishable from raw facts (`inferred = 0`).

## 3. Bridging Project 21 (RAG) + Project 22 (Ontology = GraphRAG)

`format_graphrag_context(graph, root_uri, max_hops=2)` extracts a grounded multi-hop subgraph (e.g., `Customer -> Order -> Product -> Merchant` and `Order -> PaymentTransaction`) that can be injected directly into an LLM context window alongside Project 21's hybrid vector search results.
