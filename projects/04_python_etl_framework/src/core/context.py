"""
Execution Context for ETL Pipeline

Manages execution state, metrics, and audit trail for pipeline runs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from enum import Enum


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ExecutionContext:
    """Immutable execution context for pipeline runs."""
    
    pipeline_name: str
    run_id: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    status: PipelineStatus = PipelineStatus.PENDING
    records_processed: int = 0
    records_rejected: int = 0
    error_count: int = 0
    retry_count: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "pipeline_name": self.pipeline_name,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "status": self.status.value,
            "records_processed": self.records_processed,
            "records_rejected": self.records_rejected,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }