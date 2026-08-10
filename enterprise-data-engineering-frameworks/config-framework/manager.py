"""Hierarchical configuration: env, file, vault, CLI, dynamic config."""
from __future__ import annotations
import json, os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml

@dataclass
class ConfigSource:
    name: str; priority: int; data: dict[str,Any]=field(default_factory=dict)

class ConfigManager:
    def __init__(self): self._sources=[]; self._cache={}; self._dirty=True
    def add_source(self, name, data, priority=0):
        self._sources.append(ConfigSource(name,priority,data)); self._sources.sort(key=lambda s:s.priority,reverse=True); self._dirty=True
    def add_file(self, path, priority=10):
        p=Path(path)
        if not p.exists(): return
        if p.suffix in (".yaml",".yml"): d=yaml.safe_load(p.read_text()) or {}
        elif p.suffix==".json": d=json.loads(p.read_text())
        else: d=yaml.safe_load(p.read_text()) or {}
        self.add_source(f"file:{p.name}",d,priority)
    def add_env(self, prefix="EDF_", priority=100):
        d={k[len(prefix):].lower():v for k,v in os.environ.items() if k.startswith(prefix)}
        self.add_source("env",d,priority)
    def get(self, key, default=None):
        if self._dirty: self._rebuild()
        return self._cache.get(key, default)
    def set(self, key, value): self.add_source("override",{key:value},priority=200)
    def snapshot(self):
        if self._dirty: self._rebuild()
        return dict(self._cache)
    def _rebuild(self):
        self._cache={}
        for s in reversed(self._sources): self._cache.update(s.data)
        self._dirty=False

