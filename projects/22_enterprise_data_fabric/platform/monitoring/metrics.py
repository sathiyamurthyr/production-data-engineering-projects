"""Metrics Collector - Collect and expose platform metrics."""

import time
from collections import defaultdict
from datetime import datetime
from typing import Any


class MetricsCollector:
    """Collect platform metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.counters: dict[str, int] = defaultdict(int)
        self.gauges: dict[str, float] = {}

    def increment_counter(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        self.counters[name] += value
        self.metrics[name].append({
            "timestamp": datetime.now(),
            "type": "counter",
            "value": value,
            "tags": tags or {},
        })

    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        self.gauges[name] = value
        self.metrics[name].append({
            "timestamp": datetime.now(),
            "type": "gauge",
            "value": value,
            "tags": tags or {},
        })

    def record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a histogram value."""
        self.metrics[name].append({
            "timestamp": datetime.now(),
            "type": "histogram",
            "value": value,
            "tags": tags or {},
        })

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)

    def get_gauge(self, name: str) -> float | None:
        """Get gauge value."""
        return self.gauges.get(name)

    def get_metric_history(self, name: str, limit: int = 1000) -> list[dict[str, Any]]:
        """Get metric history."""
        return self.metrics.get(name, [])[-limit:]

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "metric_types": {
                name: list(set(m["type"] for m in entries))
                for name, entries in self.metrics.items()
            },
        }

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()


class HealthChecker:
    """Check platform health."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.checks: dict[str, dict[str, Any]] = {}

    def register_check(self, name: str, check_func: Any, interval_seconds: int = 60) -> None:
        """Register a health check."""
        self.checks[name] = {
            "func": check_func,
            "interval": interval_seconds,
            "last_check": None,
            "last_status": None,
            "last_error": None,
        }

    async def run_check(self, name: str) -> dict[str, Any]:
        """Run a specific health check."""
        check = self.checks.get(name)
        if not check:
            return {"status": "error", "error": f"Check {name} not found"}
        
        try:
            result = await check["func"]()
            check["last_check"] = datetime.now()
            check["last_status"] = result.get("status", "unknown")
            check["last_error"] = None
            return result
        except Exception as e:
            check["last_check"] = datetime.now()
            check["last_status"] = "error"
            check["last_error"] = str(e)
            return {"status": "error", "error": str(e)}

    async def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks."""
        results = {}
        for name in self.checks:
            results[name] = await self.run_check(name)
        return results

    def get_health_status(self) -> dict[str, Any]:
        """Get overall health status."""
        if not self.checks:
            return {"status": "unknown", "checks": {}}
        
        all_statuses = [check["last_status"] for check in self.checks.values() if check["last_status"]]
        
        if not all_statuses:
            return {"status": "unknown", "checks": {}}
        
        if all(status == "healthy" for status in all_statuses):
            overall_status = "healthy"
        elif any(status == "error" for status in all_statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "checks": {
                name: {
                    "status": check["last_status"],
                    "last_check": check["last_check"],
                    "error": check["last_error"],
                }
                for name, check in self.checks.items()
            },
        }


class SLATracker:
    """Track SLA compliance."""

    def __init__(self) -> None:
        """Initialize SLA tracker."""
        self.slas: dict[str, dict[str, Any]] = {}
        self.violations: list[dict[str, Any]] = []

    def define_sla(self, name: str, target: float, unit: str = "percent") -> None:
        """Define an SLA."""
        self.slas[name] = {
            "target": target,
            "unit": unit,
            "current_value": 0.0,
            "violations": 0,
        }

    def record_metric(self, sla_name: str, value: float) -> None:
        """Record a metric value for SLA tracking."""
        sla = self.slas.get(sla_name)
        if not sla:
            return
        
        sla["current_value"] = value
        
        # Check for violation
        if sla["unit"] == "percent" and value < sla["target"]:
            sla["violations"] += 1
            self.violations.append({
                "sla_name": sla_name,
                "timestamp": datetime.now(),
                "expected": sla["target"],
                "actual": value,
            })

    def get_sla_report(self) -> dict[str, Any]:
        """Get SLA compliance report."""
        return {
            "slas": {
                name: {
                    "target": sla["target"],
                    "current": sla["current_value"],
                    "violations": sla["violations"],
                    "status": "met" if sla["current_value"] >= sla["target"] else "violated",
                }
                for name, sla in self.slas.items()
            },
            "total_violations": len(self.violations),
            "recent_violations": self.violations[-10:],
        }