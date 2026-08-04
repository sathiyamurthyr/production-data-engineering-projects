"""Chaos Engineering - Resilience Testing Framework."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Chaos experiment status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ChaosScenario(BaseModel):
    """Chaos scenario definition."""
    scenario_id: str
    name: str
    description: str
    category: str  # infrastructure, network, application, data
    severity: str
    steps: list[dict[str, Any]]
    rollback_steps: list[dict[str, Any]]
    prerequisites: list[str] = []
    success_criteria: dict[str, Any]


class ChaosExperiment(BaseModel):
    """Chaos experiment instance."""
    experiment_id: str
    scenario_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    results: dict[str, Any] = {}
    metrics_before: dict[str, Any] = {}
    metrics_after: dict[str, Any] = {}
    rollback_executed: bool = False


class ChaosEngine:
    """Chaos engineering engine for resilience testing."""
    
    def __init__(self):
        """Initialize chaos engine."""
        self.scenarios: dict[str, ChaosScenario] = {}
        self.experiments: dict[str, ChaosExperiment] = {}
        self.active_experiments: dict[str, ChaosExperiment] = {}
        self.safety_checks: list[callable] = []
        self._initialize_default_scenarios()
    
    def _initialize_default_scenarios(self) -> None:
        """Initialize default chaos scenarios."""
        # Kafka broker failure
        self.register_scenario(ChaosScenario(
            scenario_id="CHAOS-KAFKA-001",
            name="Kafka Broker Failure",
            description="Simulate Kafka broker failure and verify system resilience",
            category="infrastructure",
            severity="high",
            steps=[
                {"step": 1, "action": "stop_kafka_broker", "params": {"broker_id": "random"}},
                {"step": 2, "action": "wait", "params": {"duration_seconds": 30}},
                {"step": 3, "action": "verify_consumer_lag", "params": {"max_lag": 1000}},
                {"step": 4, "action": "restart_broker", "params": {}},
            ],
            rollback_steps=[
                {"step": 1, "action": "restart_broker", "params": {}},
                {"step": 2, "action": "verify_cluster_health", "params": {}},
            ],
            prerequisites=["kafka_cluster_healthy", "consumer_lag_normal"],
            success_criteria={
                "consumer_lag_recovery": True,
                "data_loss": False,
                "service_degradation_max_minutes": 5,
            },
        ))
        
        # Database connection failure
        self.register_scenario(ChaosScenario(
            scenario_id="CHAOS-DB-001",
            name="Database Connection Failure",
            description="Simulate database connection pool exhaustion",
            category="infrastructure",
            severity="medium",
            steps=[
                {"step": 1, "action": "exhaust_connection_pool", "params": {"duration_seconds": 60}},
                {"step": 2, "action": "verify_circuit_breaker", "params": {"expected_state": "open"}},
                {"step": 3, "action": "restore_connections", "params": {}},
            ],
            rollback_steps=[
                {"step": 1, "action": "restore_connections", "params": {}},
                {"step": 2, "action": "verify_pool_health", "params": {}},
            ],
            prerequisites=["database_healthy", "connection_pool_available"],
            success_criteria={
                "circuit_breaker_triggered": True,
                "auto_recovery": True,
                "data_consistency": True,
            },
        ))
        
        # High latency injection
        self.register_scenario(ChaosScenario(
            scenario_id="CHAOS-LATENCY-001",
            name="High Latency Injection",
            description="Inject latency to test system resilience",
            category="network",
            severity="medium",
            steps=[
                {"step": 1, "action": "inject_latency", "params": {"latency_ms": 500, "duration_seconds": 120}},
                {"step": 2, "action": "monitor_system", "params": {"duration_seconds": 120}},
                {"step": 3, "action": "remove_latency", "params": {}},
            ],
            rollback_steps=[
                {"step": 1, "action": "remove_latency", "params": {}},
            ],
            prerequisites=["system_healthy"],
            success_criteria={
                "system_remains_available": True,
                "error_rate_max": 0.05,
                "auto_recovery": True,
            },
        ))
        
        # Pipeline failure
        self.register_scenario(ChaosScenario(
            scenario_id="CHAOS-PIPELINE-001",
            name="Pipeline Failure",
            description="Simulate pipeline failure and test recovery",
            category="application",
            severity="high",
            steps=[
                {"step": 1, "action": "kill_pipeline", "params": {"pipeline_id": "random"}},
                {"step": 2, "action": "verify_checkpoint", "params": {}},
                {"step": 3, "action": "restart_pipeline", "params": {"from_checkpoint": True}},
            ],
            rollback_steps=[
                {"step": 1, "action": "restart_pipeline", "params": {"from_checkpoint": True}},
            ],
            prerequisites=["pipeline_running", "checkpoint_enabled"],
            success_criteria={
                "pipeline_restarts": True,
                "no_data_loss": True,
                "recovery_time_max_seconds": 300,
            },
        ))
    
    def register_scenario(self, scenario: ChaosScenario) -> None:
        """Register chaos scenario.
        
        Args:
            scenario: Chaos scenario
        """
        self.scenarios[scenario.scenario_id] = scenario
        logger.info(f"Registered chaos scenario: {scenario.scenario_id}")
    
    async def execute_scenario(
        self,
        scenario_id: str,
        parameters: dict[str, Any] = None,
    ) -> ChaosExperiment:
        """Execute chaos scenario.
        
        Args:
            scenario_id: Scenario identifier
            parameters: Execution parameters
            
        Returns:
            Experiment result
        """
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")
        
        import uuid
        
        experiment = ChaosExperiment(
            experiment_id=f"EXP-{uuid.uuid4().hex[:8].upper()}",
            scenario_id=scenario_id,
            status="running",
            started_at=datetime.now(),
        )
        
        self.experiments[experiment.experiment_id] = experiment
        self.active_experiments[experiment.experiment_id] = experiment
        
        logger.info(f"Starting chaos experiment: {experiment.experiment_id}")
        
        try:
            # Pre-experiment checks
            pre_check_passed = await self._pre_checks(scenario)
            if not pre_check_passed:
                experiment.status = "failed"
                experiment.results = {"error": "Pre-checks failed"}
                return experiment
            
            # Collect metrics before
            experiment.metrics_before = await self._collect_metrics()
            
            # Execute chaos steps
            for step in scenario.steps:
                logger.info(f"Chaos step {step['step']}: {step['action']}")
                await self._execute_step(step, parameters)
            
            # Monitor system during chaos
            await self._monitor_during_chaos(experiment, scenario)
            
            # Execute rollback
            await self._execute_rollback(scenario)
            
            # Collect metrics after
            experiment.metrics_after = await self._collect_metrics()
            
            # Validate success criteria
            success = self._validate_success_criteria(scenario, experiment)
            
            experiment.status = "completed" if success else "failed"
            experiment.completed_at = datetime.now()
            experiment.results = {
                "success": success,
                "metrics_before": experiment.metrics_before,
                "metrics_after": experiment.metrics_after,
            }
            
            logger.info(f"Chaos experiment completed: {experiment.experiment_id} - Success: {success}")
            
            return experiment
        
        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            experiment.status = "failed"
            experiment.results = {"error": str(e)}
            
            # Execute rollback on failure
            await self._execute_rollback(scenario)
            experiment.rollback_executed = True
            
            return experiment
        
        finally:
            if experiment.experiment_id in self.active_experiments:
                del self.active_experiments[experiment.experiment_id]
    
    async def _pre_checks(self, scenario: ChaosScenario) -> bool:
        """Execute pre-experiment safety checks.
        
        Args:
            scenario: Chaos scenario
            
        Returns:
            True if checks pass
        """
        # Run registered safety checks
        for check in self.safety_checks:
            try:
                if not check():
                    logger.warning("Safety check failed")
                    return False
            except Exception as e:
                logger.error(f"Safety check error: {e}")
                return False
        
        # Check prerequisites
        for prereq in scenario.prerequisites:
            if not await self._check_prerequisite(prereq):
                logger.warning(f"Prerequisite not met: {prereq}")
                return False
        
        return True
    
    async def _check_prerequisite(self, prerequisite: str) -> bool:
        """Check if prerequisite is met.
        
        Args:
            prerequisite: Prerequisite name
            
        Returns:
            True if met
        """
        # Simplified - actual implementation would check real system state
        return True
    
    async def _collect_metrics(self) -> dict[str, Any]:
        """Collect system metrics.
        
        Returns:
            Metrics snapshot
        """
        # Simplified - actual implementation would collect real metrics
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_utilization": 45.0,
            "memory_utilization": 60.0,
            "request_latency_p95": 150.0,
            "error_rate": 0.01,
        }
    
    async def _execute_step(self, step: dict[str, Any], parameters: dict[str, Any] = None) -> None:
        """Execute chaos step.
        
        Args:
            step: Step definition
            parameters: Execution parameters
        """
        action = step.get("action")
        params = step.get("params", {})
        
        # Merge with provided parameters
        if parameters:
            params.update(parameters)
        
        # Simplified - actual implementation would execute real chaos actions
        if action == "stop_kafka_broker":
            logger.info(f"Stopping Kafka broker (simulated)")
        elif action == "wait":
            import asyncio
            duration = params.get("duration_seconds", 10)
            await asyncio.sleep(min(duration, 5))  # Cap at 5 seconds for simulation
        elif action == "inject_latency":
            logger.info(f"Injecting latency (simulated)")
        else:
            logger.info(f"Executing chaos action: {action}")
    
    async def _monitor_during_chaos(self, experiment: ChaosExperiment, scenario: ChaosScenario) -> None:
        """Monitor system during chaos execution.
        
        Args:
            experiment: Chaos experiment
            scenario: Chaos scenario
        """
        # Simplified - actual implementation would monitor in real-time
        pass
    
    async def _execute_rollback(self, scenario: ChaosScenario) -> None:
        """Execute rollback steps.
        
        Args:
            scenario: Chaos scenario
        """
        logger.info("Executing rollback steps")
        
        for step in scenario.rollback_steps:
            logger.info(f"Rollback step {step['step']}: {step['action']}")
            await self._execute_step(step)
    
    def _validate_success_criteria(self, scenario: ChaosScenario, experiment: ChaosExperiment) -> bool:
        """Validate experiment success criteria.
        
        Args:
            scenario: Chaos scenario
            experiment: Chaos experiment
            
        Returns:
            True if criteria met
        """
        # Simplified - actual implementation would validate against real metrics
        return True
    
    def add_safety_check(self, check_func: callable) -> None:
        """Add safety check function.
        
        Args:
            check_func: Safety check function
        """
        self.safety_checks.append(check_func)
    
    def get_experiment_summary(self) -> dict[str, Any]:
        """Get experiment summary.
        
        Returns:
            Experiment summary
        """
        total = len(self.experiments)
        successful = len([e for e in self.experiments.values() if e.status == "completed"])
        
        return {
            "total_experiments": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "active_experiments": len(self.active_experiments),
        }


class ChaosValidator:
    """Validate chaos experiment results."""
    
    def __init__(self):
        """Initialize validator."""
        self.validation_rules: list[dict[str, Any]] = []
    
    def add_validation_rule(self, rule: dict[str, Any]) -> None:
        """Add validation rule.
        
        Args:
            rule: Validation rule
        """
        self.validation_rules.append(rule)
    
    def validate_experiment(self, experiment: ChaosExperiment) -> dict[str, Any]:
        """Validate experiment results.
        
        Args:
            experiment: Chaos experiment
            
        Returns:
            Validation result
        """
        results = {
            "experiment_id": experiment.experiment_id,
            "valid": True,
            "checks": [],
        }
        
        for rule in self.validation_rules:
            check_name = rule.get("name")
            check_func = rule.get("check")
            
            try:
                passed = check_func(experiment)
                results["checks"].append({
                    "name": check_name,
                    "passed": passed,
                })
                
                if not passed:
                    results["valid"] = False
            
            except Exception as e:
                results["checks"].append({
                    "name": check_name,
                    "passed": False,
                    "error": str(e),
                })
                results["valid"] = False
        
        return results