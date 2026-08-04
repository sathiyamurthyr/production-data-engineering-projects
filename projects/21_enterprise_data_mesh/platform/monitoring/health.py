"""Data Mesh Health Monitoring - Domain and product health status."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .models import HealthStatus


class DomainHealth(BaseModel):
    """Health metrics for an entire domain."""

    domain: str
    status: HealthStatus = HealthStatus.HEALTHY
    products_count: int = 0
    healthy_products: int = 0
    degraded_products: int = 0
    failed_products: int = 0
    avg_quality_score: float = 0.0
    avg_availability: float = 0.0
    last_check: datetime = Field(default_factory=datetime.now)
    issues: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def health_percentage(self) -> float:
        """Calculate health percentage of domain products."""
        if self.products_count == 0:
            return 100.0
        return (self.healthy_products / self.products_count) * 100


class ProductHealth(BaseModel):
    """Health metrics for a data product."""

    product_name: str
    domain: str
    status: HealthStatus = HealthStatus.HEALTHY
    quality_score: float = 0.0
    availability: float = 0.0
    freshness_status: HealthStatus = HealthStatus.HEALTHY
    last_updated: datetime = Field(default_factory=datetime.now)
    next_update_due: datetime | None = None
    quality_issues: list[dict[str, Any]] = Field(default_factory=list)
    uptime_hours: float = 0.0
    downtime_hours: float = 0.0

    def is_healthy(self) -> bool:
        """Check if product is healthy."""
        return self.status == HealthStatus.HEALTHY

    def to_report(self) -> dict[str, Any]:
        """Generate health report dictionary."""
        return {
            "product_name": self.product_name,
            "domain": self.domain,
            "status": self.status.value,
            "quality_score": self.quality_score,
            "availability": self.availability,
            "freshness_status": self.freshness_status.value,
            "last_updated": self.last_updated.isoformat(),
            "health_percentage": self.uptime_hours / (self.uptime_hours + self.downtime_hours) * 100
            if (self.uptime_hours + self.downtime_hours) > 0
            else 100.0,
        }