"""Tests for KnowledgeGraphStore subclass reasoning, transitive closure, and BFS paths."""

from pathlib import Path

from src.graph.knowledge_graph import KnowledgeGraphStore
from src.schema.ontology_registry import OntologyRegistry

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "configs" / "ontology_schema.yaml"


def test_knowledge_graph_subclass_query_transitive_closure_and_path(tmp_path: Path) -> None:
    registry = OntologyRegistry.from_yaml(SCHEMA_PATH)
    kg = KnowledgeGraphStore(tmp_path / "kg.sqlite", registry)

    m1 = kg.upsert_node("Merchant", "m1", {"entity_id": "m1", "display_name": "Parent Co", "mcc_code": "5411"})
    m2 = kg.upsert_node("Merchant", "m2", {"entity_id": "m2", "display_name": "Mid Co", "mcc_code": "5411"})
    m3 = kg.upsert_node("Merchant", "m3", {"entity_id": "m3", "display_name": "Leaf Co", "mcc_code": "4215"})
    c1 = kg.upsert_node(
        "Customer",
        "c1",
        {"entity_id": "c1", "display_name": "Alice", "email": "alice@example.com"},
    )

    kg.add_edge(m3.uri, "SUBSIDIARY_OF", m2.uri)
    kg.add_edge(m2.uri, "SUBSIDIARY_OF", m1.uri)
    inferred_count = kg.materialize_transitive_closures()

    # m3 -> m1 transitive closure + inverse PARENT_OF edges
    assert inferred_count == 1
    transitive = kg.get_edges(subject_uri=m3.uri, predicate="SUBSIDIARY_OF", object_uri=m1.uri)
    assert len(transitive) == 1
    assert transitive[0].inferred is True

    # Inverse edge allows parent -> child traversal
    parent_edges = kg.get_edges(subject_uri=m1.uri, predicate="PARENT_OF")
    assert {e.object_uri for e in parent_edges} == {m2.uri, m3.uri}

    # Subclass inference on abstract LegalEntity returns both Merchants and Customers
    legal_entities = kg.query_instances("LegalEntity", include_subclasses=True)
    assert len(legal_entities) == 4
    assert c1.uri in {n.uri for n in legal_entities}

    # Shortest path from leaf merchant to parent merchant
    path = kg.find_shortest_path(m3.uri, m1.uri)
    assert path is not None and len(path) == 1
