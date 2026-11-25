"""
Lineage Reporter Module
=======================
Exports lineage graph topologies into visual formats (Mermaid.js diagram syntax,
JSON specifications, and structured Impact Analysis Reports).
"""

import json
import logging
from typing import Dict, Any
from src.lineage.lineage_graph import LineageGraph

logger = logging.getLogger(__name__)

class LineageReporter:
    """
    Generates reports and visual diagrams from LineageGraph instances.
    """

    def __init__(self, graph: LineageGraph) -> None:
        self.graph = graph

    def generate_mermaid_diagram(self) -> str:
        """
        Export the lineage graph as a Mermaid markdown flow diagram.
        
        Returns:
            String containing Mermaid diagram syntax.
        """
        lines = ["graph LR"]
        edges = self.graph._edges

        if not edges:
            lines.append("    empty_graph[No Lineage Data]")
            return "\n".join(lines)

        for edge in edges:
            src = edge.source_asset if not edge.source_column else f"{edge.source_asset}.{edge.source_column}"
            tgt = edge.target_asset if not edge.target_column else f"{edge.target_asset}.{edge.target_column}"
            op = edge.transformation_type

            src_clean = src.replace(".", "_")
            tgt_clean = tgt.replace(".", "_")

            lines.append(f'    {src_clean}["{src}"] -->|"{op}"| {tgt_clean}["{tgt}"]')

        diagram = "\n".join(lines)
        logger.info("Generated Mermaid lineage diagram.")
        return diagram

    def generate_impact_report(self, asset_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive downstream impact report for an asset or column change.
        
        Args:
            asset_id: Name of asset being modified or deprecated.
            
        Returns:
            Dictionary containing impact analysis breakdown.
        """
        downstream = self.graph.get_downstream_impact(asset_id)
        upstream = self.graph.get_upstream_dependencies(asset_id)
        root_causes = self.graph.find_root_causes(asset_id)

        report = {
            "target_asset": asset_id,
            "downstream_impacted_count": len(downstream),
            "downstream_assets": downstream,
            "upstream_dependency_count": len(upstream),
            "upstream_assets": upstream,
            "root_cause_sources": root_causes,
            "risk_level": "HIGH" if len(downstream) > 3 else ("MEDIUM" if len(downstream) > 0 else "LOW"),
        }
        logger.info(f"Impact report generated for '{asset_id}': risk_level={report['risk_level']}.")
        return report

    def export_json(self) -> str:
        """Export full graph structure to JSON string."""
        nodes_dict = [node.node_id for node in self.graph._nodes.values()]
        edges_dict = [edge.to_dict() for edge in self.graph._edges]
        return json.dumps({"nodes": nodes_dict, "edges": edges_dict}, indent=2)
