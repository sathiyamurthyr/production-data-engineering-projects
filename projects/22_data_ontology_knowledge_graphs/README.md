# Project 22: Enterprise Data Ontology & Knowledge Graphs

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![Pytest](https://img.shields.io/badge/tests-pytest-brightgreen.svg)](tests/)
[![Architecture: Ontology + GraphRAG](https://img.shields.io/badge/architecture-Ontology%20%2B%20GraphRAG-teal.svg)](architecture.md)

Enterprise-grade reference implementation for **Data Ontologies, Semantic Layers, Entity Resolution, and Knowledge Graphs** as part of **Data Engineering Diaries** by **Sathiya Murthy**.

This project demonstrates how modern data platforms (Palantir Foundry-style Object/Link ontologies, RDF/OWL semantic models, and GraphRAG) unify siloed relational tables and JSON streams into a **schema-governed, reasoner-backed Knowledge Graph**.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Sources ["Siloed Source Feeds"]
        S1["CRM Customers (crm_customers.csv)"]
        S2["Merchant Hierarchy (merchant_accounts.csv)"]
        S3["Product Catalog (products.jsonl)"]
        S4["Orders & Payments (orders.jsonl)"]
    end

    subgraph Schema ["Ontology Governance Plane"]
        REG["OntologyRegistry\n(configs/ontology_schema.yaml)"]
        COMPAT["Backward Compatibility Checker"]
    end

    subgraph Resolution ["Entity Resolution & Mapping"]
        RES["CustomerEntityResolver\n(Email Blocking + Survivorship)"]
    end

    subgraph Graph ["Knowledge Graph & Reasoning"]
        KG["KnowledgeGraphStore (SQLite)\n• Fail-closed schema validation\n• Inverse edge materialization\n• Transitive closure & subclass inference"]
    end

    subgraph Exports ["Interoperability & GraphRAG"]
        TTL["RDF Turtle (.ttl)"]
        JLD["JSON-LD"]
        CYP["Neo4j Cypher MERGE"]
        RAG["GraphRAG N-Hop Subgraph Context"]
    end

    S1 --> RES --> KG
    S2 & S3 & S4 --> KG
    REG --> KG
    REG --> COMPAT
    KG --> TTL & JLD & CYP & RAG
```

---

## Directory Structure

```text
22_data_ontology_knowledge_graphs/
├── README.md                              # Project overview & quick start
├── architecture.md                        # Ontology layers & GraphRAG integration
├── design-decisions.md                    # Property Graph vs RDF, fail-closed validation
├── performance.md                         # Indexing, transitive closure & traversal scaling
├── troubleshooting.md                     # Common schema, resolution & graph cycle issues
├── interview-questions.md                 # Ontology & Knowledge Graph DE interview Q&As
├── requirements.txt                       # Dependencies (PyYAML, pytest)
├── configs/
│   └── ontology_schema.yaml               # Enterprise E-Commerce & FinTech Ontology
├── sample-data/
│   ├── crm_customers.csv                  # Duplicate customer rows for entity resolution
│   ├── merchant_accounts.csv              # Multi-level merchant corporate hierarchy
│   ├── products.jsonl
│   └── orders.jsonl
├── src/
│   ├── models.py                          # ClassSpec, RelationshipSpec, GraphNode, GraphEdge
│   ├── schema/
│   │   └── ontology_registry.py           # Inheritance, validation, compatibility checks
│   ├── mapping/
│   │   └── entity_resolver.py             # Blocking-key resolution & survivorship
│   ├── graph/
│   │   └── knowledge_graph.py             # SQLite graph store, reasoning & BFS traversal
│   ├── exporters/
│   │   └── graph_exporter.py              # Turtle, JSON-LD, Cypher, GraphRAG context
│   └── pipeline/
│       └── ontology_pipeline.py           # End-to-end Knowledge Graph builder
├── tests/
│   ├── conftest.py
│   ├── test_ontology_registry.py
│   ├── test_entity_resolution.py
│   ├── test_knowledge_graph_reasoning.py
│   └── test_exporters_and_e2e.py
└── notebooks/
    └── 01_ontology_knowledge_graph.ipynb  # Interactive walkthrough
```

---

## Quick Start

```bash
python -m pytest projects/22_data_ontology_knowledge_graphs/tests -v
```
