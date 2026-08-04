"""SLA Tracker - Track SLA compliance and violations."""

from datetime import datetime
from typing import Any


class SLATracker:
    """Track SLA compliance for platform operations."""

    def __init__(self) -> None:
        """Initialize SLA tracker."""
        self.slas: dict[str, dict[str, Any]] = {}
        self.violations: list[dict[str, Any]] = []

    def define_sla(
        self,
        name: str,
        target: float,
        unit: str = "percent",
        description: str | None = None,
    ) -> None:
        """Define an SLA.
        
        Args:
            name: SLA name
            target: Target value
            unit: Unit of measurement (percent, hours, etc.)
            description: SLA description
        """
        self.slas[name] = {
            "target": target,
            "unit": unit,
            "description": description or name,
            "current_value": 0.0,
            "violations": 0,
            "last_updated": datetime.now(),
        }

    def record_metric(self, sla_name: str, value: float) -> None:
        """Record a metric value for SLA tracking.
        
        Args:
            sla_name: Name of the SLA
            value: Metric value
        """
        sla = self.slas.get(sla_name)
        if not sla:
            return
        
        sla["current_value"] = value
        sla["last_updated"] = datetime.now()
        
        # Check for violation based on unit
        if sla["unit"] == "percent" and value < sla["target"]:
            sla["violations"] += 1
            self.violations.append({
                "sla_name": sla_name,
                "timestamp": datetime.now(),
                "expected": sla["target"],
                "actual": value,
                "description": sla["description"],
            })
        elif sla["unit"] == "hours" and value > sla["target"]:
            sla["violations"] += 1
            self.violations.append({
                "sla_name": sla_name,
                "timestamp": datetime.now(),
                "expected": sla["target"],
                "actual": value,
                "description": sla["description"],
            })

    def get_sla(self, name: str) -> dict[str, Any] | None:
        """Get SLA details."""
        return self.slas.get(name)

    def get_sla_report(self) -> dict[str, Any]:
        """Get SLA compliance report."""
        return {
            "slas": {
                name: {
                    "name": name,
                    "description": sla["description"],
                    "target": sla["target"],
                    "unit": sla["unit"],
                    "current": sla["current_value"],
                    "violations": sla["violations"],
                    "status": "met" if self._is_sla_met(sla) else "violated",
                    "last_updated": sla["last_updated"],
                }
                for name, sla in self.slas.items()
            },
            "total_violations": len(self.violations),
            "recent_violations": self.violations[-10:],
        }

    def _is_sla_met(self, sla: dict[str, Any]) -> bool:
        """Check if SLA is met."""
        if sla["unit"] == "percent":
            return sla["current_value"] >= sla["target"]
        elif sla["unit"] == "hours":
            return sla["current_value"] <= sla["target"]
        return True

    def get_violations(self, sla_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get SLA violations.
        
        Args:
            sla_name: Filter by SLA name (optional)
            limit: Maximum number of violations to return
        """
        if sla_name:
            violations = [v for v in self.violations if v["sla_name"] == sla_name]
        else:
            violations = self.violations
        return violations[-limit:]

    def clear_violations(self, sla_name: str | None = None) -> None:
        """Clear violations.
        
        Args:
            sla_name: Clear violations for specific SLA (optional)
        """
        if sla_name:
            self.violations = [v for v in self.violations if v["sla_name"] != sla_name]
            if sla_name in self.slas:
                self.slas[sla_name]["violations"] = 0
        else:
            self.violations.clear()
            for sla in self.slas.values():
                sla["violations"] = 0