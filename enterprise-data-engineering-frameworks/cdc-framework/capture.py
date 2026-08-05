"""CDC framework: log-based, timestamp-based change data capture."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.utils.helpers import utc_now_iso

class ChangeType(Enum):
    INSERT="insert"; UPDATE="update"; DELETE="delete"

@dataclass
class ChangeEvent:
    change_type: ChangeType; table: str; data: dict[str, Any]
    timestamp: str=field(default_factory=utc_now_iso); position: int=0

class TimestampCDC:
    def __init__(self, ts_field="updated_at"): self.field=ts_field; self._last=None
    def capture(self, records):
        if self._last is None: changes=[ChangeEvent(ChangeType.INSERT,"",r) for r in records]
        else: changes=[ChangeEvent(ChangeType.UPDATE,"",r) for r in records if r.get(self.field,"")>self._last]
        if records: self._last=max(r.get(self.field,"") for r in records)
        return changes

class LogCDC:
    def __init__(self): self._pos=0
    def capture(self, entries):
        changes=[]
        for e in entries:
            self._pos+=1
            changes.append(ChangeEvent(ChangeType(e.get("op","insert")),e.get("table",""),e.get("data",{}),position=self._pos))
        return changes
    @property
    def position(self): return self._pos

class CDCProcessor:
    def __init__(self): self._processed=[]; self._cp=0
    def process(self, events):
        new=[e for e in events if e.position>self._cp]
        self._processed.extend(new)
        if new: self._cp=max(e.position for e in new)
        return new
    @property
    def checkpoint(self): return self._cp

