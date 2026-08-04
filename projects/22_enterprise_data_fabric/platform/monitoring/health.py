"""Health Checker - Platform health monitoring."""

from datetime import datetime
from typing import Any, Callable, Coroutine


class HealthChecker:
    """Check platform component health."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.checks: dict[str, dict[str, Any]] = {}

    def register_check(
        self,
        name: str,
        check_func: Callable[..., Coroutine[Any, Any, Any]],
        interval_seconds: int = 60,
    ) -> None:
        """Register a health check.
        
        Args:
            name: Check name
            check_func: Async function that returns health status
            interval_seconds: Check interval in seconds
        """
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
        """Run all registered health checks."""
        results = {}
        for name in self.checks:
            results[name] = await self.run_check(name)
        return results

    def get_health_status(self) -> dict[str, Any]:
        """Get overall health status."""
        if not self.checks:
            return {"status": "unknown", "checks": {}}
        
        all_statuses = [
            check["last_status"]
            for check in self.checks.values()
            if check["last_status"]
        ]
        
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

    def get_check_detail(self, name: str) -> dict[str, Any] | None:
        """Get detailed information about a specific check."""
        check = self.checks.get(name)
        if not check:
            return None
        return {
            "name": name,
            "interval": check["interval"],
            "last_check": check["last_check"],
            "last_status": check["last_status"],
            "last_error": check["last_error"],
        }