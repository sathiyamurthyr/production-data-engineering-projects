"""Monitoring Models - Data classes for monitoring and observability."""

from datetime import datetime
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class HealthStatus(str, Enum):
    """Health check statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Metric:
    """Metric data point."""

    def __init__(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        timestamp: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Initialize metric."""
        self.name = name
        self.value = value
        self.type = metric_type
        self.timestamp = timestamp or datetime.now()
        self.tags = tags or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class HealthCheck:
    """Health check result."""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Initialize health check."""
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class SLA:
    """Service Level Agreement definition."""

    def __init__(
        self,
        name: str,
        target: float,
        unit: str = "percent",
        description: str = "",
        warning_threshold: float | None = None,
    ) -> None:
        """Initialize SLA."""
        self.name = name
        self.target = target
        self.unit = unit
        self.description = description
        self.warning_threshold = warning_threshold or target * 0.9
        self.violations: list[dict[str, Any]] = []

    def record_violation(self, actual: float, timestamp: datetime | None = None) -> None:
        """Record an SLA violation."""
        self.violations.append({
            "timestamp": timestamp or datetime.now(),
            "expected": self.target,
            "actual": actual,
        })

    def get_status(self, current_value: float) -> dict[str, Any]:
        """Get SLA status."""
        is_met = current_value >= self.target if self.unit == "percent" else current_value <= self.target
        is_warning = current_value >= self.warning_threshold if self.unit == "percent" else current_value <= self.warning_threshold
        
        return {
            "name": self.name,
            "target": self.target,
            "current": current_value,
            "unit": self.unit,
            "status": "met" if is_met else "violated",
            "warning": not is_met and is_warning,
            "violations": len(self.violations),
        }