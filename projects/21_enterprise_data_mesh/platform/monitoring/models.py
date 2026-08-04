"""Data Mesh Monitoring Models - Enums and shared types."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    FAILED = "failed"


class SlaMetrics(BaseModel):
    """SLA metrics for data products."""

    product_name: str
    domain: str
    freshness: HealthStatus = HealthStatus.HEALTHY
    availability: float = 99.9
    quality_score: float = 1.0
    latency_ms: float = 0.0
    last_check: datetime = Field(default_factory=datetime.now)
    breach_count: int = 0

    def is_compliant(self) -> bool:
        """Check if SLA is compliant."""
        return self.freshness in (HealthStatus.HEALTHY, HealthStatus.WARNING)


class MetricType(str, Enum):
    """Types of metrics collected."""

    FRESHNESS = "freshness"
    QUALITY = "quality"
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"