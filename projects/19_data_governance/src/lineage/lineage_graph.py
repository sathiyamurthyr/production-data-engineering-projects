"""
Lineage Graph Module
====================
Constructs and traverses directed acyclic graphs (DAGs) representing dataset
dependencies, enabling upstream root cause analysis and downstream impact analysis.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from src.lineage.lineage_tracker import LineageEdge, LineageTracker

logger = logging.getLogger(__name__)

@dataclass
class LineageNode:
    """Represents a node in the lineage graph."""
    node_id: str  # asset_id or asset_id.column_name
    node_type: str = "TABLE"  # "TABLE" or "COLUMN"
    domain: str = "unknown"
    sensitivity_level: str = "INTERNAL"
    attributes: Dict[str, Any] = field(default_factory=dict)


class LineageGraph:
    """
    DAG-based Lineage Graph engine supporting upstream/downstream graph traversal.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}
        self._adjacency_out: Dict[str, Set[str]] = {}  # source -> set of targets (downstream)
        self._adjacency_in: Dict[str, Set[str]] = {}   # target -> set of sources (upstream)
        self._edges: List[LineageEdge] = []

    def add_node(self, node_id: str, node_type: str = "TABLE", domain: str = "unknown", sensitivity: str = "INTERNAL") -> LineageNode:
        """Add or update a node in the lineage graph."""
        if node_id not in self._nodes:
            self._nodes[node_id] = LineageNode(node_id=node_id, node_type=node_type, domain=domain, sensitivity_level=sensitivity)
            self._adjacency_out[node_id] = set()
            self._adjacency_in[node_id] = set()
        return self._nodes[node_id]

    def add_edge(self, edge: LineageEdge) -> None:
        """Add a lineage edge to the graph."""
        src = edge.source_asset if not edge.source_column else f"{edge.source_asset}.{edge.source_column}"
        tgt = edge.target_asset if not edge.target_column else f"{edge.target_asset}.{edge.target_column}"

        self.add_node(src)
        self.add_node(tgt)

        self._adjacency_out[src].add(tgt)
        self._adjacency_in[tgt].add(src)
        self._edges.append(edge)
        logger.debug(f"Added graph edge: {src} -> {tgt}")

    def build_from_tracker(self, tracker: LineageTracker) -> None:
        """Populate graph using recorded edges from a LineageTracker."""
        for edge in tracker.get_all_edges():
            self.add_edge(edge)

    def get_upstream_dependencies(self, node_id: str) -> List[str]:
        """
        Recursively find all upstream source nodes that feed into the target node.
        
        Args:
            node_id: Target node identifier.
            
        Returns:
            List of all upstream node identifiers.
        """
        visited: Set[str] = set()

        def _dfs(curr: str):
            for parent in self._adjacency_in.get(curr, set()):
                if parent not in visited:
                    visited.add(parent)
                    _dfs(parent)

        _dfs(node_id)
        return sorted(list(visited))

    def get_downstream_impact(self, node_id: str) -> List[str]:
        """
        Recursively find all downstream nodes that would be impacted by a change in node_id.
        
        Args:
            node_id: Source node identifier.
            
        Returns:
            List of all downstream impacted node identifiers.
        """
        visited: Set[str] = set()

        def _dfs(curr: str):
            for child in self._adjacency_out.get(curr, set()):
                if child not in visited:
                    visited.add(child)
                    _dfs(child)

        _dfs(node_id)
        return sorted(list(visited))

    def find_root_causes(self, node_id: str) -> List[str]:
        """
        Find terminal root cause nodes (nodes with 0 upstream parents) that feed into node_id.
        """
        all_upstream = self.get_upstream_dependencies(node_id)
        # Handle case where the node itself has no parents and has no upstream at all
        if not all_upstream:
            # If the node exists in the graph, it is its own root cause
            if node_id in self._nodes:
                return [node_id]
            return []
            
        root_causes = [
            node for node in all_upstream
            if len(self._adjacency_in.get(node, set())) == 0
        ]
        return root_causes

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect any circular dependency cycles in the lineage graph.
        
        Returns:
            List of cycles, where each cycle is a list of node IDs forming a loop.
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def _dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._adjacency_out.get(node, set()):
                if neighbor not in visited:
                    _dfs(neighbor)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node in list(self._nodes.keys()):
            if node not in visited:
                _dfs(node)

        return cycles

    def get_nodes(self) -> Dict[str, LineageNode]:
        """Return graph nodes dict."""
        return self._nodes
