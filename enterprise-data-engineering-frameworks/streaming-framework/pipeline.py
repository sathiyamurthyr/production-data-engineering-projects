"""Streaming framework: Kafka, checkpointing, DLQ, state."""
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

class StreamingSource(ABC):
    @abstractmethod
    def read(self) -> Iterator[list[dict[str, Any]]]: ...

class ListSource(StreamingSource):
    def __init__(self, data, batch_size=100): self.data=data; self.bs=batch_size
    def read(self):
        for i in range(0,len(self.data),self.bs): yield self.data[i:i+self.bs]

class StreamingSink(ABC):
    @abstractmethod
    def write(self, batch) -> int: ...

class ListSink(StreamingSink):
    def __init__(self): self.records=[]
    def write(self, b): self.records.extend(b); return len(b)

class DeadLetterQueue:
    def __init__(self): self._r=[]
    def write(self, b): self._r.extend(b); return len(b)
    @property
    def records(self): return list(self._r)
    def clear(self): self._r.clear()

@dataclass
class Checkpoint:
    pipeline_name: str; offset: int=0; batch_id: int=0; timestamp: str=field(default_factory=utc_now_iso)

class CheckpointManager:
    def __init__(self, d=".checkpoints"): self.dir=Path(d); self.dir.mkdir(parents=True, exist_ok=True)
    def save(self, cp): (self.dir/f"{cp.pipeline_name}.json").write_text(json.dumps({"pipeline_name":cp.pipeline_name,"offset":cp.offset,"batch_id":cp.batch_id,"timestamp":cp.timestamp}))
    def load(self, n):
        p=self.dir/f"{n}.json"
        if not p.exists(): return None
        return Checkpoint(**json.loads(p.read_text()))

class StateStore:
    def __init__(self): self._s={}
    def get(self,k): return self._s.get(k)
    def put(self,k,v): self._s[k]=v
    def delete(self,k): self._s.pop(k,None)
    def snapshot(self): return dict(self._s)
    def restore(self,s): self._s=dict(s)

@dataclass
class StreamingResult:
    pipeline_name: str; total_records: int=0; total_batches: int=0
    failed_records: int=0; errors: list[str]=field(default_factory=list)

class StreamingPipeline:
    def __init__(self, name, checkpoint_dir=".checkpoints", max_batches=None):
        self.name=name; self._src=None; self._sink=None; self._tf=[]
        self._dlq=DeadLetterQueue(); self._state=StateStore()
        self._cp=CheckpointManager(checkpoint_dir); self._max=max_batches
    def source(self, s): self._src=s; return self
    def sink(self, s): self._sink=s; return self
    def transform(self, fn): self._tf.append(fn); return self
    @property
    def dlq(self): return self._dlq
    @property
    def state(self): return self._state
    def run(self):
        if not self._src: raise ValueError("No source")
        if not self._sink: raise ValueError("No sink")
        r=StreamingResult(pipeline_name=self.name)
        cp=self._cp.load(self.name); bid=cp.batch_id if cp else 0; off=cp.offset if cp else 0
        for batch in self._src.read():
            if self._max and bid>=self._max: break
            bid+=1; r.total_batches+=1
            try:
                d=batch
                for fn in self._tf: d=fn(d)
                r.total_records+=len(d); self._sink.write(d); off+=len(d)
            except Exception as e:
                r.failed_records+=len(batch); r.errors.append(str(e)); self._dlq.write(batch)
            self._cp.save(Checkpoint(pipeline_name=self.name,offset=off,batch_id=bid))
        return r

