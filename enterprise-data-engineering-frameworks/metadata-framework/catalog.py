"""Metadata: business, technical, operational metadata, catalog, data contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class TableMetadata:
    table_id: str=field(default_factory=lambda: generate_id("tbl_"))
    name: str=""; schema: str=""; database: str=""
    columns: list[dict[str,Any]]=field(default_factory=list)
    owner: str=""; tags: list[str]=field(default_factory=list)
    description: str=""; created_at: str=field(default_factory=utc_now_iso)

@dataclass
class DataContract:
    contract_id: str=field(default_factory=lambda: generate_id("dc_"))
    name: str=""; version: str="1.0.0"
    schema: dict[str,Any]=field(default_factory=dict)
    owner: str=""; created_at: str=field(default_factory=utc_now_iso)

class MetadataCatalog:
    def __init__(self): self._tables={}; self._contracts={}
    def register_table(self, m): self._tables[m.name]=m
    def get_table(self, n): return self._tables.get(n)
    def list_tables(self, tag=None):
        if tag: return [t for t in self._tables.values() if tag in t.tags]
        return list(self._tables.values())
    def search_tables(self, q):
        ql=q.lower()
        return [t for t in self._tables.values() if ql in t.name.lower() or ql in t.description.lower()]
    def register_contract(self, c): self._contracts[c.name]=c
    def get_contract(self, n): return self._contracts.get(n)
    def list_contracts(self): return list(self._contracts.values())

