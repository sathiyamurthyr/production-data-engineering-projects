"""ELT framework: Extract-Load-Transform with warehouse-native models."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ELTModel:
    name: str; sql: str; materialized_as: str = "table"
    depends_on: list[str] = field(default_factory=list)

class ELTPipeline:
    def __init__(self, name): self.name=name; self._models=[]
    def add_model(self, m): self._models.append(m); return self
    def run(self):
        ordered=self._order(); results={}
        for m in ordered: results[m.name]={"status":"success","sql":m.sql}
        return {"pipeline":self.name,"models":len(ordered),"results":results}
    def _order(self):
        mp={m.name:m for m in self._models}; ordered=[]; visited=set()
        def visit(n):
            if n in visited: return
            m=mp.get(n)
            if not m: return
            visited.add(n)
            for d in m.depends_on: visit(d)
            ordered.append(m)
        for m in self._models: visit(m.name)
        return ordered

