"""Interoperability exporters: RDF Turtle, JSON-LD, Neo4j Cypher, and GraphRAG context."""

import json
from typing import Any, Dict, List

from src.graph.knowledge_graph import KnowledgeGraphStore
from src.schema.ontology_registry import OntologyRegistry


def _escape_turtle(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def export_turtle(registry: OntologyRegistry, graph: KnowledgeGraphStore) -> str:
    """Serialize ontology classes/properties and knowledge graph triples to RDF Turtle."""
    lines: List[str] = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        f"@prefix ont: <{registry.namespace}> .",
        "",
    ]

    for cname, cspec in registry.classes.items():
        lines.append(f"ont:{cname} a owl:Class ;")
        if cspec.parent:
            lines.append(f"    rdfs:subClassOf ont:{cspec.parent} ;")
        lines.append(f'    rdfs:comment "{_escape_turtle(cspec.description)}" .')

    for rname, rspec in registry.relationships.items():
        lines.append(
            f"ont:{rname} a owl:ObjectProperty ; "
            f"rdfs:domain ont:{rspec.domain} ; rdfs:range ont:{rspec.range} ."
        )

    lines.append("")
    for node in graph.list_all_nodes():
        subj = f"<{node.uri}>"
        lines.append(f"{subj} rdf:type ont:{node.class_name} ;")
        prop_items = list(node.properties.items())
        for idx, (k, v) in enumerate(prop_items):
            sep = " ." if idx == len(prop_items) - 1 else " ;"
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                lines.append(f"    ont:{k} {v}{sep}")
            else:
                lines.append(f'    ont:{k} "{_escape_turtle(str(v))}"{sep}')

    for edge in graph.get_edges(include_inferred=False):
        lines.append(f"<{edge.subject_uri}> ont:{edge.predicate} <{edge.object_uri}> .")

    return "\n".join(lines) + "\n"


def export_jsonld(registry: OntologyRegistry, graph: KnowledgeGraphStore) -> Dict[str, Any]:
    """Export knowledge graph nodes and outgoing edges as JSON-LD."""
    edges_by_subj: Dict[str, List[Dict[str, str]]] = {}
    for edge in graph.get_edges(include_inferred=False):
        edges_by_subj.setdefault(edge.subject_uri, []).append(
            {"predicate": edge.predicate, "target": edge.object_uri}
        )

    graph_items: List[Dict[str, Any]] = []
    for node in graph.list_all_nodes():
        item: Dict[str, Any] = {
            "@id": node.uri,
            "@type": f"ont:{node.class_name}",
            **node.properties,
        }
        for rel in edges_by_subj.get(node.uri, []):
            item.setdefault(f"ont:{rel['predicate']}", []).append({"@id": rel["target"]})
        graph_items.append(item)

    return {
        "@context": {
            "ont": registry.namespace,
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        },
        "@graph": graph_items,
    }


def export_cypher(graph: KnowledgeGraphStore) -> str:
    """Generate idempotent Neo4j Cypher MERGE statements for nodes and edges."""
    statements: List[str] = []
    for node in graph.list_all_nodes():
        props_literal = json.dumps({**node.properties, "uri": node.uri})
        statements.append(
            f"MERGE (n:{node.class_name} {{uri: {json.dumps(node.uri)}}}) SET n += {props_literal};"
        )

    for edge in graph.get_edges(include_inferred=False):
        statements.append(
            f"MATCH (a {{uri: {json.dumps(edge.subject_uri)}}}), "
            f"(b {{uri: {json.dumps(edge.object_uri)}}}) "
            f"MERGE (a)-[:{edge.predicate}]->(b);"
        )
    return "\n".join(statements) + "\n"


def format_graphrag_context(
    graph: KnowledgeGraphStore, root_uri: str, max_hops: int = 2
) -> str:
    """Format an N-hop entity neighborhood into structured context for LLM/GraphRAG prompts."""
    nodes, edges = graph.extract_subgraph(root_uri, max_hops=max_hops)
    if not nodes:
        return f"No ontology entity found for {root_uri}."

    node_map = {n.uri: n for n in nodes}
    lines = [f"### Ontology Context Subgraph (root={root_uri}, max_hops={max_hops})", "", "Entities:"]
    for node in nodes:
        summary = ", ".join(f"{k}={v}" for k, v in node.properties.items())
        lines.append(f"- [{node.class_name}] {node.uri} ({summary})")

    lines.extend(["", "Relationships:"])
    for edge in edges:
        subj = node_map.get(edge.subject_uri)
        obj = node_map.get(edge.object_uri)
        subj_label = subj.class_name if subj else "Entity"
        obj_label = obj.class_name if obj else "Entity"
        tag = " [inferred]" if edge.inferred else ""
        lines.append(
            f"- ({subj_label} {edge.subject_uri}) -[{edge.predicate}]-> "
            f"({obj_label} {edge.object_uri}){tag}"
        )
    return "\n".join(lines)
