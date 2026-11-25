# Design Decisions: Data Ontology & Knowledge Graphs

## 1. Hybrid Property-Graph + RDF Semantics
- **Decision:** Store nodes with typed JSON property bags and directed `(subject_uri, predicate, object_uri)` edges in SQLite, while preserving RDF/OWL class hierarchy and exporting to Turtle (`.ttl`), JSON-LD, and Neo4j Cypher.
- **Rationale:** Pure RDF triples make multi-attribute entity records verbose; pure property graphs often lack formal domain/range governance and subclass inference. Combining both gives clean Python ergonomics plus W3C & Neo4j interoperability.

## 2. Deterministic Blocking + Survivorship for Entity Resolution
- **Decision:** Group CRM records by normalized email (`lower(trim(email))`), compute token-Jaccard confidence on names, and apply deterministic survivorship (longest display name, highest loyalty tier), keeping `source_ids` lineage.
- **Rationale:** Prevents duplicate customer nodes (`crm_101` + `crm_103`) from fragmenting order history and LTV metrics in the Knowledge Graph.

## 3. Schema Backward-Compatibility Gate in CI
- **Decision:** Provide `check_backward_compatibility(v1, v2)` to catch removed classes/properties, narrowed types, or new required properties without defaults.
- **Rationale:** Ontologies act as enterprise contracts consumed by BI tools, microservices, and LLM agents; breaking ontology changes must fail CI before merge.
