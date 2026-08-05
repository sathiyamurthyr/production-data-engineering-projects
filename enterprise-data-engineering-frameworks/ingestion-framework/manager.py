"""Unified ingestion abstraction."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class IngestionResult:
    ingestion_id: str=field(default_factory=lambda: generate_id("ing_"))
    source: str=""; records: int=0; status: str="success"
    errors: list[str]=field(default_factory=list); timestamp: str=field(default_factory=utc_now_iso)

class IngestionSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def ingest(self) -> list[dict[str, Any]]: ...

class IngestionManager:
    def __init__(self): self._sources={}; self._results=[]
    def register(self, s): self._sources[s.name]=s
    def ingest(self, name):
        if name not in self._sources: return IngestionResult(source=name, status="failed", errors=["Not found"])
        try:
            d=self._sources[name].ingest(); r=IngestionResult(source=name, records=len(d))
        except Exception as e: r=IngestionResult(source=name, status="failed", errors=[str(e)])
        self._results.append(r); return r
    def ingest_all(self): return [self.ingest(n) for n in self._sources]
    def get_results(self): return list(self._results)

