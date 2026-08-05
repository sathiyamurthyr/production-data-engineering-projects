"""ETL framework: extractors, loaders, transforms, SCD."""
from __future__ import annotations
import csv, json
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any
from shared.utils.helpers import utc_now_iso

class Extractor(ABC):
    @abstractmethod
    def extract(self) -> list[dict[str, Any]]: ...

class Loader(ABC):
    @abstractmethod
    def load(self, data: list[dict[str, Any]]) -> int: ...

class CSVExtractor(Extractor):
    def __init__(self, path, delimiter=","): self.path=Path(path); self.delimiter=delimiter
    def extract(self):
        with self.path.open(newline="") as f: return list(csv.DictReader(f, delimiter=self.delimiter))

class JSONExtractor(Extractor):
    def __init__(self, path, json_path=None): self.path=Path(path); self.json_path=json_path
    def extract(self):
        data = json.loads(self.path.read_text())
        if self.json_path:
            for k in self.json_path.split("."): data = data[k]
        return [data] if isinstance(data, dict) else data

class ListExtractor(Extractor):
    def __init__(self, data): self._data = data
    def extract(self): return self._data

class CSVLoader(Loader):
    def __init__(self, path): self.path = Path(path)
    def load(self, data):
        if not data: return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=data[0].keys()); w.writeheader(); w.writerows(data)
        return len(data)

class JSONLoader(Loader):
    def __init__(self, path): self.path = Path(path)
    def load(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, default=str)); return len(data)

class InMemoryLoader(Loader):
    def __init__(self): self.data = []
    def load(self, data): self.data.extend(data); return len(data)

def drop_nulls(field): return lambda d: [r for r in d if r.get(field) is not None]
def add_field(name, value):
    def t(d):
        for r in d: r[name] = value
        return d
    return t
def filter_records(pred): return lambda d: [r for r in d if pred(r)]
def deduplicate(key):
    def t(d):
        seen=set(); r=[]
        for x in d:
            v=x.get(key)
            if v not in seen: seen.add(v); r.append(x)
        return r
    return t

class SCDType2:
    def __init__(self, key_field, tracked_fields): self.key_field=key_field; self.tracked_fields=tracked_fields; self._records=[]
    def apply(self, new_data):
        now=utc_now_iso(); results=[]
        for nr in new_data:
            key=nr.get(self.key_field)
            cur=next((r for r in reversed(self._records) if r["data"].get(self.key_field)==key and r["is_current"]), None)
            if cur is None:
                scd={"data":nr,"valid_from":now,"valid_to":None,"is_current":True,"version":1}
                self._records.append(scd); results.append(scd)
            elif any(cur["data"].get(f)!=nr.get(f) for f in self.tracked_fields):
                cur["valid_to"]=now; cur["is_current"]=False
                scd={"data":nr,"valid_from":now,"valid_to":None,"is_current":True,"version":cur["version"]+1}
                self._records.append(scd); results.append(scd)
            else: results.append(cur)
        return results
    def get_current(self): return [r for r in self._records if r["is_current"]]
    def get_history(self, key): return [r for r in self._records if r["data"].get(self.key_field)==key]

class ETLPipeline:
    def __init__(self, name): self.name=name; self._ext=None; self._tf=[]; self._ld=None
    def extract(self, e): self._ext=e; return self
    def transform(self, fn): self._tf.append(fn); return self
    def load(self, l): self._ld=l; return self
    def run(self):
        if not self._ext: raise ValueError("No extractor")
        if not self._ld: raise ValueError("No loader")
        data=self._ext.extract()
        for fn in self._tf: data=fn(data)
        c=self._ld.load(data)
        return {"pipeline":self.name,"records_extracted":len(data),"records_loaded":c}

