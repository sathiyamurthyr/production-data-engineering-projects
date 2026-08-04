"""Data Mesh SLA Tracking - Service Level Agreement monitoring and breach detection."""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from .metrics import MetricsCollector
from .models import SlaMetrics, HealthStatus, MetricType


class SlaTarget(BaseModel):
    """SLA target definition for a data product."""

    product_name: str
    domain: str
    freshness_threshold_hours: float = Field(default=24.0)
    availability_target: float = Field(default=99.9)
    quality_target: float = Field(default=0.95)
    latency_threshold_ms: float = Field(default=5000.0)
    uptime_target: float = Field(default=99.9)


class SlaViolation(BaseModel):
    """SLA violation event."""

    product_name: str
    domain: str
    metric_type: str
    actual_value: float
    target_value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    severity: str = "warning"
    resolved: bool = False
    resolved_at: datetime | None = None

    def to_alert(self) -> dict[str, Any]:
        """Generate alert dictionary."""
        return {
            "alert_type": "sla_violation",
            "product_name": self.product_name,
            "domain": self.domain,
            "metric_type": self.metric_type,
            "actual_value": self.actual_value,
            "target_value": self.target_value,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


class SlaTracker:
    """
    Tracks SLA compliance for data products.

    Provides enterprise-grade SLA monitoring with breach detection,
    alerting, and compliance reporting for the Data Mesh platform.
    """

    def __init__(self, metrics_collector: MetricsCollector | None = None) -> None:
        """Initialize SLA tracker with optional metrics collector."""
        self.metrics = metrics_collector or MetricsCollector()
        self.sla_targets: dict[str, SlaTarget] = {}
        self.violations: list[SlaViolation] = []

    def register_product(self, target: SlaTarget) -> None:
        """Register a data product for SLA tracking."""
        self.sla_targets[target.product_name] = target

    def check_freshness(
        self,
        product_name: str,
        hours_since_update: float,
        domain: str,
    ) -> SlaMetrics | None:
        """Check freshness SLA compliance for a product."""
        if product_name not in self.sla_targets:
            return None

        target = self.sla_targets[product_name]
        is_breach = hours_since_update > target.freshness_threshold_hours

        status = HealthStatus.HEALTHY
        if is_breach:
            status = HealthStatus.FAILED
            self._record_violation(
                product_name,
                domain,
                "freshness",
                hours_since_update,
                target.freshness_threshold_hours,
            )

        return SlaMetrics(
            product_name=product_name,
            domain=domain,
            freshness=status,
            latency_ms=hours_since_update * 3600 * 1000,
        )

    def check_availability(
        self,
        product_name: str,
        availability_percent: float,
        domain: str,
    ) -> SlaMetrics | None:
        """Check availability SLA compliance for a product."""
        if product_name not in self.sla_targets:
            return None

        target = self.sla_targets[product_name]
        is_breach = availability_percent < target.availability_target

        status = HealthStatus.HEALTHY
        if availability_percent < 95.0:
            status = HealthStatus.FAILED
        elif availability_percent < 99.0:
            status = HealthStatus.DEGRADED
        elif availability_percent < target.availability_target:
            status = HealthStatus.WARNING

        if is_breach:
            self._record_violation(
                product_name,
                domain,
                "availability",
                availability_percent,
                target.availability_target,
            )

        return SlaMetrics(
            product_name=product_name,
            domain=domain,
            availability=availability_percent,
            freshness=status if is_breach else HealthStatus.HEALTHY,
        )

    def check_quality(
        self,
        product_name: str,
        quality_score: float,
        domain: str,
        issues: list[dict[str, Any]] | None = None,
    ) -> SlaMetrics | None:
        """Check quality SLA compliance for a product."""
        if product_name not in self.sla_targets:
            return None

        target = self.sla_targets[product_name]
        is_breach = quality_score < target.quality_target

        status = HealthStatus.HEALTHY
        if quality_score < 0.8:
            status = HealthStatus.FAILED
        elif quality_score < 0.9:
            status = HealthStatus.DEGRADED
        elif quality_score < target.quality_target:
            status = HealthStatus.WARNING

        if is_breach:
            self._record_violation(
                product_name,
                domain,
                "quality",
                quality_score,
                target.quality_target,
            )

        self.metrics.record_metric(
            f"product_{product_name}_quality_score",
            quality_score,
            tags={"domain": domain, "product": product_name},
        )

        return SlaMetrics(
            product_name=product_name,
            domain=domain,
            quality_score=quality_score,
            freshness=status if is_breach else HealthStatus.HEALTHY,
            latency_ms=target.latency_threshold_ms,
        )

    def check_latency(
        self,
        product_name: str,
        latency_ms: float,
        domain: str,
    ) -> SlaMetrics | None:
        """Check latency SLA compliance for a product."""
        if product_name not in self.sla_targets:
            return None

        target = self.sla_targets[product_name]
        is_breach = latency_ms > target.latency_threshold_ms

        status = HealthStatus.HEALTHY
        if latency_ms > target.latency_threshold_ms * 2:
            status = HealthStatus.FAILED
        elif latency_ms > target.latency_threshold_ms * 1.5:
            status = HealthStatus.DEGRADED
        elif latency_ms > target.latency_threshold_ms:
            status = HealthStatus.WARNING

        if is_breach:
            self._record_violation(
                product_name,
                domain,
                "latency",
                latency_ms,
                target.latency_threshold_ms,
            )

        self.metrics.record_metric(
            f"product_{product_name}_latency_ms",
            latency_ms,
            tags={"domain": domain, "product": product_name},
        )

        return SlaMetrics(
            product_name=product_name,
            domain=domain,
            latency_ms=latency_ms,
            freshness=status if is_breach else HealthStatus.HEALTHY,
        )

    def _record_violation(
        self,
        product_name: str,
        domain: str,
        metric_type: str,
        actual_value: float,
        target_value: float,
    ) -> None:
        """Record an SLA violation."""
        severity = "warning"
        if actual_value > target_value * 2:
            severity = "critical"
        elif actual_value > target_value * 1.5:
            severity = "high"

        violation = SlaViolation(
            product_name=product_name,
            domain=domain,
            metric_type=metric_type,
            actual_value=actual_value,
            target_value=target_value,
            severity=severity,
        )
        self.violations.append(violation)
        self.metrics.record_metric(
            f"product_{product_name}_sla_breaches",
            1,
            tags={"domain": domain, "type": metric_type},
        )

    def get_compliance_report(self, product_name: str) -> dict[str, Any]:
        """Generate SLA compliance report for a product."""
        if product_name not in self.sla_targets:
            return {"error": "Product not registered for SLA tracking"}

        target = self.sla_targets[product_name]
        product_violations = [
            v for v in self.violations
            if v.product_name == product_name and not v.resolved
        ]

        quality_points = self.metrics.get_history(f"product_{product_name}_quality_score")
        latency_points = self.metrics.get_history(f"product_{product_name}_latency_ms")

        return {
            "product_name": product_name,
            "domain": target.domain,
            "targets": {
                "freshness_hours": target.freshness_threshold_hours,
                "availability_percent": target.availability_target,
                "quality_score": target.quality_target,
                "latency_ms": target.latency_threshold_ms,
            },
            "current_metrics": {
                "avg_quality_score": self.metrics.get_average(f"product_{product_name}_quality_score"),
                "avg_latency_ms": self.metrics.get_average(f"product_{product_name}_latency_ms"),
            },
            "violations": {
                "total_breaches": len(product_violations),
                "unresolved_breaches": len([v for v in product_violations if not v.resolved]),
                "breach_rate": (len(product_violations) / max(len(quality_points), 1)) * 100,
            },
            "compliance_status": self._calculate_compliance_status(product_violations),
        }

    def get_domain_compliance(self, domain: str) -> dict[str, Any]:
        """Get SLA compliance for all products in a domain."""
        domain_products = [
            name for name, target in self.sla_targets.items()
            if target.domain == domain
        ]

        reports = [
            self.get_compliance_report(name) for name in domain_products
        ]

        total_violations = sum(
            r["violations"]["total_breaches"] for r in reports if "violations" in r
        )

        return {
            "domain": domain,
            "products_monitored": len(domain_products),
            "total_violations": total_violations,
            "compliance_summary": [
                {"product": r.get("product_name"), "status": r.get("compliance_status")}
                for r in reports
            ],
        }

    def _calculate_compliance_status(self, violations: list[SlaViolation]) -> str:
        """Calculate overall compliance status based on violations."""
        if not violations:
            return "compliant"

        critical = len([v for v in violations if v.severity == "critical"])
        high = len([v for v in violations if v.severity == "high"])

        if critical > 0:
            return "non_compliant"
        if high > 2:
            return "at_risk"
        if len(violations) > 3:
            return "degraded"
        return "warning"

    def resolve_violation(self, violation_index: int) -> bool:
        """Mark a violation as resolved."""
        if 0 <= violation_index < len(self.violations):
            self.violations[violation_index].resolved = True
            self.violations[violation_index].resolved_at = datetime.now()
            return True
        return False

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active SLA violation alerts."""
        return [
            v.to_alert() for v in self.violations
            if not v.resolved
        ]

    def get_sla_dashboard(self) -> dict[str, Any]:
        """Generate SLA dashboard summary."""
        domains = list(set(t.domain for t in self.sla_targets.values()))
        domain_reports = [self.get_domain_compliance(d) for d in domains]

        return {
            "total_products": len(self.sla_targets),
            "domains_monitored": len(domains),
            "overall_compliance": self._aggregate_compliance(domain_reports),
            "domains": domain_reports,
            "active_alerts_count": len(self.get_active_alerts()),
        }

    def _aggregate_compliance(self, domain_reports: list[dict[str, Any]]) -> str:
        """Aggregate compliance status across domains."""
        statuses = [r.get("compliance_summary", []) for r in domain_reports]
        flat_statuses = [s.get("status") for r in statuses for s in r]

        if any(s == "non_compliant" for s in flat_statuses):
            return "non_compliant"
        if any(s == "at_risk" for s in flat_statuses):
            return "at_risk"
        if any(s in ("warning", "degraded") for s in flat_statuses):
            return "degraded"
        return "compliant"