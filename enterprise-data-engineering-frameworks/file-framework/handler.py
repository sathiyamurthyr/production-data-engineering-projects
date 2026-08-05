"""File ingestion: CSV, JSON, Parquet, XML, Excel."""
from __future__ import annotations
import csv, json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

class FileHandler(ABC):
    @abstractmethod
    def read(self, path) -> list[dict[str, Any]]: ...
    @abstractmethod
    def write(self, path, data) -> int: ...

class CSVHandler(FileHandler):
    def read(self, path):
        with Path(path).open(newline="") as f: return list(csv.DictReader(f))
    def write(self, path, data):
        if not data: return 0
        p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="") as f:
            w=csv.DictWriter(f, fieldnames=data[0].keys()); w.writeheader(); w.writerows(data)
        return len(data)

class JSONHandler(FileHandler):
    def read(self, path):
        d=json.loads(Path(path).read_text()); return [d] if isinstance(d, dict) else d
    def write(self, path, data):
        p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str)); return len(data)

class FileIngestionManager:
    def __init__(self): self._h={".csv":CSVHandler(), ".json":JSONHandler()}
    def register(self, ext, h): self._h[ext]=h
    def read(self, path):
        ext=Path(path).suffix.lower()
        if ext not in self._h: raise ValueError(f"No handler for {ext}")
        return self._h[ext].read(path)
    def write(self, path, data):
        ext=Path(path).suffix.lower()
        if ext not in self._h: raise ValueError(f"No handler for {ext}")
        return self._h[ext].write(path, data)

