# Interview Questions: Enterprise Data Ontology & Knowledge Graphs (20 Q&As)

### 1. What is the difference between a Data Catalog, a Semantic Layer, and an Enterprise Data Ontology?
- A **Data Catalog** indexes technical metadata (tables, schemas, owners, lineage).
- A **Semantic Layer** (e.g., dbt Semantic Layer) standardizes BI metrics and dimensions over warehouse tables.
- An **Enterprise Ontology** models real-world business **Object Types** (classes with inheritance), **Link Types** (relationships with domain/range/cardinality), constraints, and operational state independent of physical storage—powering analytics, apps, and GraphRAG.

### 2. RDF Triple Store vs. Labeled Property Graph (LPG) — how do you choose?
- **RDF (Turtle / SPARQL):** Represents everything as `(subject, predicate, object)` triples with W3C URIs and native RDFS/OWL reasoning—ideal for open standards and cross-org federation, though edge attributes require reification/RDF-star.
- **Labeled Property Graph (Neo4j / Cypher):** Nodes and edges natively hold key-value properties with index-free adjacency—ideal for low-latency multi-hop traversals (fraud rings, impact analysis).

### 3. Why is Entity Resolution critical before loading a Knowledge Graph?
Without entity resolution, `"Aarav Sharma"` (`crm_101`) and `"Aarav K. Sharma"` (`crm_103`) become disconnected nodes, fragmenting order history, LTV, and fraud connections across separate subgraphs. Blocking keys (e.g., normalized email) plus deterministic survivorship rules merge duplicates into one canonical URI (`urn:de:ontology:customer:...`) while preserving `source_ids` lineage.

### 4. What is an abstract class in an Ontology, and why disallow direct instantiation?
An abstract class (like `LegalEntity`) defines shared identity and properties inherited by concrete subclasses (`Customer`, `Merchant`). Disallowing direct instantiation (`validate_instance` fails closed) ensures every stored entity has a concrete operational type, while `query_instances("LegalEntity", include_subclasses=True)` still unifies queries across all subtypes.

### 5. Explain domain and range constraints on Ontology relationships.
A relationship's `domain` restricts valid subject classes and its `range` restricts valid object classes (e.g., `PLACED_ORDER` requires `Customer -> Order`). Enforcing domain/range checks with subclass polymorphism (`Merchant` satisfies `LegalEntity` for `SUBSIDIARY_OF`) prevents inverted or nonsensical edges from polluting the graph.

### 6. How does RDFS-style subclass inference simplify downstream analytics and queries?
Instead of hardcoding `WHERE type IN ('Customer', 'Merchant', ...)` across dozens of queries, subclass inference walks the ontology class hierarchy (`is_subclass_of`) so querying a parent concept automatically includes all current and future subclasses.

### 7. What is transitive closure materialization, and what is the read vs. write tradeoff?
For transitive predicates like `SUBSIDIARY_OF` (`m_sub2 -> m_sub1 -> m_parent`), computing transitive closure at write time (`materialize_transitive_closures()`) inserts inferred edges (`m_sub2 -> m_parent`, `inferred=True`). This trades a small write-time BFS cost for $O(1)$ single-hop reads without expensive recursive CTEs at query time.

### 8. Why track an `inferred` flag on Knowledge Graph edges?
Distinguishing raw asserted facts (`inferred=False`) from reasoned edges (inverse links and transitive closures, `inferred=True`) is essential for provenance, debugging, selective recomputation when an asserted link is removed, and clean RDF/Cypher exports.

### 9. How do Ontologies improve RAG (GraphRAG) over pure vector chunk search?
Vector search retrieves isolated text snippets by semantic similarity and often fails on multi-hop relational questions (*"Which parent company owns the merchant selling SKU-002 in a pending IMPS order?"*). Extracting an N-hop ontology subgraph (`format_graphrag_context()`) supplies the LLM with verified, exact relational paths.

### 10. How do you evolve an Ontology schema safely in production without breaking consumers?
Treat the ontology as a versioned contract. Run a backward-compatibility check in CI (`check_backward_compatibility()`) that blocks removing classes/properties, narrowing/changing property types, altering relationship domain/range, or adding `required` properties without a `default`.

### 11. What are survivorship rules in Entity Resolution?
When multiple source records merge into one canonical entity, survivorship rules deterministically decide which attribute wins—for example, taking the most complete `display_name`, the highest loyalty `tier` (`PLATINUM > GOLD > SILVER > BRONZE`), or the most recent `updated_at` timestamp from a trusted system of record.

### 12. Why use deterministic blocking keys before fuzzy string similarity in Entity Resolution?
Comparing every pair of $N$ records is $O(N^2)$ and collapses at millions of rows. Grouping records by blocking keys (normalized email, phone, or domain+zip) shrinks candidate comparisons to tiny buckets before applying token-Jaccard or Jaro-Winkler similarity.

### 13. How do canonical URIs (`urn:de:ontology:...`) prevent ID collisions across source systems?
Auto-increment IDs (`101` in CRM vs `101` in Merchant Master) collide if used directly as graph node keys. Prefixing or hashing into namespaced canonical URNs (`urn:de:ontology:customer:cust_...`) guarantees global uniqueness across heterogeneous systems.

### 14. Why materialize inverse relationships (`PLACED_ORDER` / `PLACED_BY`, `SUBSIDIARY_OF` / `PARENT_OF`)?
Materializing explicit inverses lets graph traversals and BFS shortest-path algorithms walk uniformly along outgoing indexed edges (`subject_uri`) without needing bidirectional union scans on every hop.

### 15. How do you enforce fail-closed governance when ingesting messy JSON/CSV feeds into a Knowledge Graph?
Validate every node and edge against `OntologyRegistry` before persistence (`upsert_node`, `add_edge`). Reject or quarantine records with missing required fields, wrong primitive types, or invalid enum values (`tier="DIAMOND"`) rather than silently coercing bad semantics into the graph.

### 16. How do JSON-LD, RDF Turtle (`.ttl`), and Neo4j Cypher exports complement one another?
- **Turtle (`.ttl`):** W3C standard for SPARQL triple stores (Neptune, GraphDB) and OWL tooling.
- **JSON-LD:** Web/API-friendly linked data format readable by standard JSON consumers and knowledge panels.
- **Cypher (`MERGE`):** Idempotent loading script for Neo4j property graph databases.

### 17. How do you detect and handle cycles in Ontology class hierarchies vs. instance graphs?
Class inheritance (`parent`) must form a strict DAG—`OntologyRegistry._validate_schema_integrity()` rejects cycles at schema load time. Instance graphs (`SUBSIDIARY_OF`, `find_shortest_path`) can contain cycles in dirty source data, so BFS traversals must track a `visited` set to terminate safely.

### 18. How do you bridge an existing Lakehouse (Medallion Silver/Gold) with an Enterprise Ontology?
Keep bulk event history and analytical aggregations in Delta/Iceberg Gold tables, while projecting core business entities and relationships (Customers, Merchants, Orders, Disputes, Ownership) into the Ontology/Knowledge Graph with foreign-key URIs back to lakehouse records.

### 19. How do you size N-hop neighborhood extraction for GraphRAG without blowing up the LLM context window?
Bound traversal depth (`max_hops=1` or `2`), filter by relevant relationship predicates rather than expanding all high-degree hub nodes (like `Country=IN`), and serialize only compact key properties per node.

### 20. How do you test an Ontology and Knowledge Graph pipeline end-to-end in CI?
Load the YAML ontology schema into an isolated `tmp_path` SQLite store, run sample feeds with intentional duplicates and multi-hop hierarchies, assert entity merge counts, fail-closed `OntologyValidationError` cases, subclass/transitive reasoning counts, and validate Turtle/JSON-LD/Cypher/GraphRAG outputs.
