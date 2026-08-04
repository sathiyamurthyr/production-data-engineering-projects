"""Data Mesh Metrics Collection - Performance and quality metrics."""

import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricPoint(BaseModel):
    """Single metric data point."""

    name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: dict[str, str] = Field(default_factory=dict)
    dimensions: dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics for data mesh products.

    Provides enterprise-grade metrics collection for monitoring
    data product performance, quality, and SLA compliance.
    """

    def __init__(self) -> None:
        self.metrics: dict[str, list[MetricPoint]] = {}
        self._start_times: dict[str, float] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value."""
        point = MetricPoint(name=name, value=value, tags=tags or {})

        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(point)

    def start_timer(self, timer_name: str) -> None:
        """Start a timer for measuring duration."""
        self._start_times[timer_name] = time.time()

    def stop_timer(self, timer_name: str) -> float:
        """Stop a timer and record the duration."""
        if timer_name not in self._start_times:
            raise ValueError(f"Timer '{timer_name}' was not started")

        duration = time.time() - self._start_times[timer_name]
        del self._start_times[timer_name]
        self.record_metric(f"{timer_name}_duration", duration)
        return duration

    def get_latest(self, name: str) -> MetricPoint | None:
        """Get the most recent metric value."""
        points = self.metrics.get(name, [])
        return points[-1] if points else None

    def get_history(
        self,
        name: str,
        hours: int = 24,
    ) -> list[MetricPoint]:
        """Get metric history for the specified time period."""
        points = self.metrics.get(name, [])
        cutoff = datetime.now().timestamp() - (hours * 3600)
        return [p for p in points if p.timestamp.timestamp() >= cutoff]

    def get_average(self, name: str, hours: int = 24) -> float:
        """Calculate average metric value over time period."""
        points = self.get_history(name, hours)
        if not points:
            return 0.0
        return sum(p.value for p in points) / len(points)

    def get_product_metrics(self, product_name: str) -> dict[str, Any]:
        """Get all metrics for a specific data product."""
        product_points = {
            name: points
            for name, points in self.metrics.items()
            if product_name in name
        }

        return {
            "product_name": product_name,
            "metrics": {
                name: {
                    "latest": points[-1].value if points else None,
                    "average": self.get_average(name),
                    "points": [p.value for p in points],
                }
                for name, points in product_points.items()
            },
        }