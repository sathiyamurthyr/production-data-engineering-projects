"""Batch processing framework with partitioning and retry."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class BatchJob:
    name: str; handler: Callable; partition_key: str | None = None; retries: int = 0

@dataclass
class BatchResult:
    job_id: str = field(default_factory=lambda: generate_id("batch_"))
    job_name: str = ""; status: str = "pending"; records: int = 0
    start_time: str = ""; end_time: str = ""; errors: list[str] = field(default_factory=list)

class BatchProcessor:
    def __init__(self, name): self.name=name; self._jobs=[]
    def add_job(self, j): self._jobs.append(j); return self
    def run(self, data):
        results=[]
        for job in self._jobs:
            r=BatchResult(job_name=job.name, start_time=utc_now_iso())
            try:
                if job.partition_key:
                    parts={}
                    for x in data: parts.setdefault(x.get(job.partition_key),[]).append(x)
                    for pd in parts.values(): job.handler(pd); r.records+=len(pd)
                else: job.handler(data); r.records+=len(data)
                r.status="success"
            except Exception as e: r.status="failed"; r.errors.append(str(e))
            r.end_time=utc_now_iso(); results.append(r)
        return results

