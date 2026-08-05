"""Lineage: column-level and table-level lineage tracking and impact analysis."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id

@dataclass
class LineageNode:
    node_id: str=field(default_factory=lambda: generate_id("node_"))
    name: str=""; node_type: str="table"; columns: list[str]=field(default_factory=list)

@dataclass
class LineageEdge:
    source_id: str; target_id: str
    column_mapping: dict[str,str]=field(default_factory=dict); transformation: str=""

class LineageTracker:
    def __init__(self): self._nodes={}; self._edges=[]
    def add_node(self, n): self._nodes[n.node_id]=n; return n.node_id
    def add_edge(self, e): self._edges.append(e)
    def get_node(self, nid): return self._nodes.get(nid)
    def get_upstream(self, nid): return [e.source_id for e in self._edges if e.target_id==nid]
    def get_downstream(self, nid): return [e.target_id for e in self._edges if e.source_id==nid]
    def impact_analysis(self, nid):
        visited=set(); queue=[nid]
        while queue:
            c=queue.pop(0)
            for d in self.get_downstream(c):
                if d not in visited: visited.add(d); queue.append(d)
        return list(visited)
    def lineage_graph(self, nid):
        return {"node":self.get_node(nid),"upstream":[self.get_node(u) for u in self.get_upstream(nid)],
                "downstream":[self.get_node(d) for d in self.get_downstream(nid)]}

