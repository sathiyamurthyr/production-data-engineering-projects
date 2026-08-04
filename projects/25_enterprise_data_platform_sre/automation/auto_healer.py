"""Auto-Healing Engine - Automated self-healing for platform components."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Issue(BaseModel):
    """Issue detected in component."""
    issue_id: str
    component: str
    issue_type: str
    severity: str
    description: str
    detected_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    metadata: dict[str, Any] = {}
    resolved: bool = False


class HealingStrategy(BaseModel):
    """Healing strategy definition."""
    strategy_id: str
    component: str
    issue_type: str
    description: str
    action: str  # restart, scale_up, failover, etc.
    parameters: dict[str, Any] = {}
    max_attempts: int = 3
    cooldown_minutes: int = 5


class HealingResult(BaseModel):
    """Healing execution result."""
    success: bool
    strategy_id: str
    component: str
    action: str
    message: str
    timestamp: datetime
    next_attempt: datetime | None = None


class AutoHealer:
    """Automated self-healing for platform components."""
    
    def __init__(self):
        """Initialize auto-healer."""
        self.strategies: dict[str, HealingStrategy] = {}
        self.issue_history: list[Issue] = []
        self.healing_history: list[HealingResult] = []
        self.component_health: dict[str, HealthStatus] = {}
        self.last_healing: dict[str, datetime] = {}
    
    def register_strategy(self, strategy: HealingStrategy) -> None:
        """Register healing strategy.
        
        Args:
            strategy: Healing strategy
        """
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"Registered healing strategy: {strategy.strategy_id}")
    
    def detect_issue(self, component: str, issue_type: str, description: str, severity: str = "medium") -> Issue:
        """Detect issue in component.
        
        Args:
            component: Component name
            issue_type: Type of issue
            description: Issue description
            severity: Issue severity
            
        Returns:
            Detected issue
        """
        import uuid
        
        issue = Issue(
            issue_id=f"ISS-{uuid.uuid4().hex[:8].upper()}",
            component=component,
            issue_type=issue_type,
            severity=severity,
            description=description,
            detected_at=datetime.now(),
        )
        
        self.issue_history.append(issue)
        self.component_health[component] = HealthStatus.UNHEALTHY
        
        logger.warning(f"Issue detected: {issue.issue_id} - {component}: {description}")
        
        # Trigger healing
        self._attempt_healing(issue)
        
        return issue
    
    def _attempt_healing(self, issue: Issue) -> HealingResult:
        """Attempt to heal issue.
        
        Args:
            issue: Issue to heal
            
        Returns:
            Healing result
        """
        # Find matching strategy
        strategy = self._find_strategy(issue.component, issue.issue_type)
        
        if not strategy:
            return HealingResult(
                success=False,
                strategy_id="none",
                component=issue.component,
                action="none",
                message="No healing strategy found",
                timestamp=datetime.now(),
            )
        
        # Check cooldown
        if not self._can_heal(issue.component, strategy):
            return HealingResult(
                success=False,
                strategy_id=strategy.strategy_id,
                component=issue.component,
                action=strategy.action,
                message="In cooldown period",
                timestamp=datetime.now(),
            )
        
        # Execute healing
        try:
            result = self._execute_healing(strategy, issue)
            
            self.healing_history.append(result)
            self.last_healing[issue.component] = datetime.now()
            
            if result.success:
                issue.resolved = True
                self.component_health[issue.component] = HealthStatus.HEALTHY
                logger.info(f"Healing successful: {issue.issue_id}")
            else:
                logger.warning(f"Healing failed: {issue.issue_id} - {result.message}")
            
            return result
        
        except Exception as e:
            logger.error(f"Healing error: {e}")
            return HealingResult(
                success=False,
                strategy_id=strategy.strategy_id,
                component=issue.component,
                action=strategy.action,
                message=f"Healing error: {str(e)}",
                timestamp=datetime.now(),
            )
    
    def _find_strategy(self, component: str, issue_type: str) -> HealingStrategy | None:
        """Find matching healing strategy.
        
        Args:
            component: Component name
            issue_type: Issue type
            
        Returns:
            Matching strategy or None
        """
        for strategy in self.strategies.values():
            if strategy.component == component and strategy.issue_type == issue_type:
                return strategy
        return None
    
    def _can_heal(self, component: str, strategy: HealingStrategy) -> bool:
        """Check if healing can be attempted.
        
        Args:
            component: Component name
            strategy: Healing strategy
            
        Returns:
            True if can heal
        """
        last_heal = self.last_healing.get(component)
        if not last_heal:
            return True
        
        cooldown = timedelta(minutes=strategy.cooldown_minutes)
        return datetime.now() - last_heal > cooldown
    
    def _execute_healing(self, strategy: HealingStrategy, issue: Issue) -> HealingResult:
        """Execute healing strategy.
        
        Args:
            strategy: Healing strategy
            issue: Issue to heal
            
        Returns:
            Healing result
        """
        # Simplified - actual implementation would execute real actions
        # like restarting services, scaling up, failing over, etc.
        
        if strategy.action == "restart":
            message = f"Restarted {issue.component}"
            success = True
        elif strategy.action == "scale_up":
            message = f"Scaled up {issue.component}"
            success = True
        elif strategy.action == "failover":
            message = f"Failed over {issue.component}"
            success = True
        elif strategy.action == "clear_cache":
            message = f"Cleared cache for {issue.component}"
            success = True
        else:
            message = f"Unknown action: {strategy.action}"
            success = False
        
        return HealingResult(
            success=success,
            strategy_id=strategy.strategy_id,
            component=issue.component,
            action=strategy.action,
            message=message,
            timestamp=datetime.now(),
        )
    
    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all components.
        
        Returns:
            Health status
        """
        return {
            component: status.value
            for component, status in self.component_health.items()
        }
    
    def get_healing_stats(self) -> dict[str, Any]:
        """Get healing statistics.
        
        Returns:
            Healing stats
        """
        # Count all healing attempts, including those blocked by cooldown
        total_attempts = len(self.healing_history)
        # Also count issues that were detected but couldn't be healed due to cooldown
        cooldown_blocked = len([i for i in self.issue_history if not i.resolved and i.component in self.last_healing])
        total = total_attempts + cooldown_blocked
        successful = len([h for h in self.healing_history if h.success])
        failed = total - successful
        
        return {
            "total_attempts": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
        }


class SelfHealingPipeline:
    """Self-healing for data pipelines."""
    
    def __init__(self, auto_healer: AutoHealer):
        """Initialize self-healing pipeline.
        
        Args:
            auto_healer: Auto-healer instance
        """
        self.auto_healer = auto_healer
        self.pipeline_status: dict[str, dict[str, Any]] = {}
    
    def register_pipeline_health(
        self,
        pipeline_id: str,
        health_check: Callable,
        healing_strategies: list[HealingStrategy],
    ) -> None:
        """Register pipeline health check and strategies.
        
        Args:
            pipeline_id: Pipeline identifier
            health_check: Health check function
            healing_strategies: Healing strategies
        """
        self.pipeline_status[pipeline_id] = {
            "health_check": health_check,
            "strategies": healing_strategies,
            "last_check": None,
            "status": HealthStatus.UNKNOWN,
        }
        
        # Register strategies
        for strategy in healing_strategies:
            self.auto_healer.register_strategy(strategy)
    
    def check_pipeline_health(self, pipeline_id: str) -> dict[str, Any]:
        """Check pipeline health.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Health status
        """
        pipeline = self.pipeline_status.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not registered"}
        
        # Run health check
        try:
            is_healthy = pipeline["health_check"]()
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            status = HealthStatus.UNKNOWN
        
        pipeline["last_check"] = datetime.now()
        pipeline["status"] = status
        
        return {
            "pipeline_id": pipeline_id,
            "status": status.value,
            "last_check": pipeline["last_check"].isoformat(),
        }
    
    def heal_pipeline(self, pipeline_id: str) -> dict[str, Any]:
        """Heal pipeline if needed.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Healing result
        """
        pipeline = self.pipeline_status.get(pipeline_id)
        if not pipeline:
            return {"error": "Pipeline not registered"}
        
        # Check if healing needed
        if pipeline["status"] == HealthStatus.HEALTHY:
            return {"status": "healthy", "action": "none"}
        
        # Detect issues
        issue = self.auto_healer.detect_issue(
            component=pipeline_id,
            issue_type="pipeline_failure",
            description="Pipeline health check failed",
            severity="high",
        )
        
        # Attempt healing
        result = self.auto_healer._attempt_healing(issue)
        
        return {
            "pipeline_id": pipeline_id,
            "issue_id": issue.issue_id,
            "healing_result": result.dict(),
        }


class HealthChecker:
    """Health check for platform components."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: dict[str, Callable] = {}
        self.results: dict[str, dict[str, Any]] = {}
    
    def register_check(self, component: str, check_func: Callable) -> None:
        """Register health check.
        
        Args:
            component: Component name
            check_func: Health check function
        """
        self.checks[component] = check_func
    
    def run_checks(self) -> dict[str, dict[str, Any]]:
        """Run all health checks.
        
        Returns:
            Health check results
        """
        results = {}
        
        for component, check_func in self.checks.items():
            try:
                start_time = datetime.now()
                
                # Run check
                healthy = check_func()
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results[component] = {
                    "healthy": healthy,
                    "execution_time_ms": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                results[component] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
        
        self.results = results
        return results
    
    def get_overall_health(self) -> dict[str, Any]:
        """Get overall health status.
        
        Returns:
            Overall health
        """
        if not self.results:
            return {"status": "unknown"}
        
        all_healthy = all(r.get("healthy", False) for r in self.results.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "components": self.results,
            "timestamp": datetime.now().isoformat(),
        }