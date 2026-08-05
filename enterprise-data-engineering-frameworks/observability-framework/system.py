"""Observability: metrics, logs, tracing, SLIs, SLOs, dashboards."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.utils.helpers import utc_now_iso

class SLIType(Enum):
    LATENCY="latency"; AVAILABILITY="availability"; THROUGHPUT="throughput"; ERROR_RATE="error_rate"

@dataclass
class SLI:
    name: str; sli_type: SLIType; value: float=0.0; target: float=0.99
    timestamp: str=field(default_factory=utc_now_iso)

@dataclass
class SLO:
    name: str; sli: SLI; target: float=0.99; window_hours: int=24; current_compliance: float=0.0

@dataclass
class TraceSpan:
    span_id: str=field(default_factory=lambda: f"span_{utc_now_iso()}")
    trace_id: str=""; operation: str=""
    start_time: str=field(default_factory=utc_now_iso); end_time: str=""
    duration_ms: float=0.0; tags: dict[str,Any]=field(default_factory=dict)

class ObservabilitySystem:
    def __init__(self): self._slis={}; self._slos={}; self._spans=[]; self._logs=[]
    def record_sli(self, s): self._slis[s.name]=s
    def get_sli(self, n): return self._slis.get(n)
    def define_slo(self, s): self._slos[s.name]=s
    def check_slo(self, n):
        s=self._slos.get(n); return s and s.current_compliance>=s.target
    def start_span(self, tid, op, tags=None):
        sp=TraceSpan(trace_id=tid,operation=op,tags=tags or {}); self._spans.append(sp); return sp
    def end_span(self, sp): sp.end_time=utc_now_iso()
    def log(self, level, msg, **kw): self._logs.append({"level":level,"message":msg,"timestamp":utc_now_iso(),**kw})
    def get_dashboard_data(self):
        return {"slis":{n:{"value":s.value,"target":s.target} for n,s in self._slis.items()},
                "slos":{n:{"compliance":s.current_compliance,"target":s.target} for n,s in self._slos.items()},
                "spans":len(self._spans),"logs":len(self._logs)}

