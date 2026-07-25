"""
Pipeline Metrics Collection

Monitors and collects metrics for ETL pipeline performance.
"""

import time
from datetime import datetime
from typing import Any
from dataclasses import dataclass, field


@dataclass
class PipelineMetrics:
    """Metrics collected during pipeline execution."""
    pipeline_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float = 0
    records_processed: int = 0
    records_loaded: int = 0
    records_rejected: int = 0
    error_count: int = 0
    duration_seconds: float = 0
    
    def stop(self) -> None:
        """Stop timer and calculate duration."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "records_processed": self.records_processed,
            "records_loaded": self.records_loaded,
            "records_rejected": self.records_rejected,
            "error_count": self.error_count,
            "duration_seconds": round(self.duration_seconds, 3),
            "throughput_rps": round(
                self.records_processed / self.duration_seconds, 2
            ) if self.duration_seconds > 0 else 0,
        }


class MetricsCollector:
    """
    Collects and aggregates pipeline metrics.
    """
    
    def __init__(self):
        self.metrics: dict[str, PipelineMetrics] = {}
    
    def start_pipeline(self, name: str) -> PipelineMetrics:
        """Start collecting metrics for a pipeline."""
        metric = PipelineMetrics(pipeline_name=name)
        self.metrics[name] = metric
        return metric
    
    def record_success(self, name: str, records: int) -> None:
        """Record successful processing of records."""
        if name in self.metrics:
            self.metrics[name].records_processed += records
    
    def record_error(self, name: str) -> None:
        """Record pipeline error."""
        if name in self.metrics:
            self.metrics[name].error_count += 1
    
    def get_metrics(self, name: str) -> dict[str, Any]:
        """Get metrics for a specific pipeline."""
        metric = self.metrics.get(name)
        return metric.to_dict() if metric else {}
    
    def get_all_metrics(self) -> list[dict[str, Any]]:
        """Get all pipeline metrics."""
        return [m.to_dict() for m in self.metrics.values()]