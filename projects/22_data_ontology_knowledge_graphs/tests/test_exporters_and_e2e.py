"""End-to-end tests for OntologyIngestionPipeline and RDF/JSON-LD/Cypher/GraphRAG exports."""

from pathlib import Path

from src.exporters.graph_exporter import (
    export_cypher,
    export_jsonld,
    export_turtle,
    format_graphrag_context,
)
from src.pipeline.ontology_pipeline import OntologyIngestionPipeline


def test_ontology_pipeline_e2e_and_all_exporters(tmp_path: Path) -> None:
    project_dir = Path(__file__).resolve().parent.parent
    pipeline = OntologyIngestionPipeline.from_yaml(
        project_dir / "configs" / "ontology_schema.yaml",
        graph_db_path=tmp_path / "kg.sqlite",
    )

    report = pipeline.run(project_dir / "sample-data")
    assert report.customers_raw == 4
    assert report.customers_resolved == 3  # crm_101 & crm_103 deduplicated
    assert report.merchants_loaded == 3
    assert report.products_loaded == 2
    assert report.orders_loaded == 3
    assert report.payments_loaded == 3
    assert report.inferred_edges_added == 1  # m_sub2 -> m_parent transitive closure

    # Turtle RDF export
    ttl = export_turtle(pipeline.registry, pipeline.graph)
    assert "@prefix owl: <http://www.w3.org/2002/07/owl#> ." in ttl
    assert "ont:Customer a owl:Class ;" in ttl
    assert "ont:PLACED_ORDER" in ttl

    # JSON-LD export
    jsonld = export_jsonld(pipeline.registry, pipeline.graph)
    assert "@context" in jsonld and len(jsonld["@graph"]) == report.total_nodes

    # Neo4j Cypher export
    cypher = export_cypher(pipeline.graph)
    assert "MERGE (n:Customer" in cypher
    assert "MERGE (a)-[:SETTLED_BY]->(b);" in cypher

    # GraphRAG 2-hop context subgraph for a resolved customer
    aarav = next(
        n
        for n in pipeline.graph.query_instances("Customer")
        if n.properties["email"] == "aarav.sharma@example.com"
    )
    context = format_graphrag_context(pipeline.graph, aarav.uri, max_hops=2)
    assert "Ontology Context Subgraph" in context
    assert "ORD-9001" in context
    assert "TXN-5001" in context
