"""Service Level Objectives (SLO) Management."""

import logging
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SLI(BaseModel):
    """Service Level Indicator definition."""
    name: str
    description: str
    metric_query: str  # PromQL query
    unit: str  # percent, ms, count, etc.
    category: str  # availability, latency, throughput, etc.


class SLO(BaseModel):
    """Service Level Objective definition."""
    slo_id: str
    name: str
    description: str
    sli: SLI
    target: float  # Target value (e.g., 99.9 for 99.9% availability)
    window_days: int  # Rolling window in days
    alert_threshold: float  # Error budget burn rate alert threshold
    
    
class SLOCompliance(BaseModel):
    """SLO compliance check result."""
    slo_id: str
    compliant: bool
    current_value: float
    target: float
    error_budget_remaining: float
    error_budget_burn_rate: float
    timestamp: datetime


class SLOManager:
    """Manage Service Level Objectives."""
    
    def __init__(self):
        """Initialize SLO manager."""
        self.slos: dict[str, SLO] = {}
        self.compliance_history: dict[str, list[SLOCompliance]] = {}
    
    def define_slo(
        self,
        slo_id: str,
        name: str,
        description: str,
        metric_query: str,
        target: float,
        window_days: int = 30,
        unit: str = "percent",
        category: str = "availability",
    ) -> SLO:
        """Define a new SLO.
        
        Args:
            slo_id: SLO identifier
            name: SLO name
            description: SLO description
            metric_query: PromQL query for SLI
            target: Target value
            window_days: Rolling window in days
            unit: Unit of measurement
            category: SLO category
            
        Returns:
            SLO definition
        """
        sli = SLI(
            name=name,
            description=description,
            metric_query=metric_query,
            unit=unit,
            category=category,
        )
        
        slo = SLO(
            slo_id=slo_id,
            name=name,
            description=description,
            sli=sli,
            target=target,
            window_days=window_days,
            alert_threshold=10.0,  # Alert when 10% of error budget consumed
        )
        
        self.slos[slo_id] = slo
        self.compliance_history[slo_id] = []
        
        logger.info(f"Defined SLO: {slo_id} - {name}")
        return slo
    
    def check_compliance(
        self,
        slo_id: str,
        current_value: float,
    ) -> SLOCompliance:
        """Check SLO compliance.
        
        Args:
            slo_id: SLO identifier
            current_value: Current SLI value
            
        Returns:
            Compliance result
        """
        slo = self.slos.get(slo_id)
        if not slo:
            raise ValueError(f"SLO not found: {slo_id}")
        
        # Calculate error budget
        error_budget_total = 100 - slo.target
        error_budget_remaining = self._calculate_error_budget(
            current_value,
            slo.target,
        )
        
        # Calculate burn rate
        burn_rate = self._calculate_burn_rate(
            error_budget_total,
            error_budget_remaining,
            slo.window_days,
        )
        
        # Check compliance
        compliant = current_value >= slo.target
        
        compliance = SLOCompliance(
            slo_id=slo_id,
            compliant=compliant,
            current_value=current_value,
            target=slo.target,
            error_budget_remaining=error_budget_remaining,
            error_budget_burn_rate=burn_rate,
            timestamp=datetime.now(),
        )
        
        # Record compliance
        self.compliance_history[slo_id].append(compliance)
        
        if not compliant:
            logger.warning(
                f"SLO breach: {slo_id} - "
                f"Current: {current_value}{slo.sli.unit}, Target: {slo.target}{slo.sli.unit}"
            )
        
        return compliance
    
    def get_error_budget_status(self, slo_id: str) -> dict[str, Any]:
        """Get error budget status.
        
        Args:
            slo_id: SLO identifier
            
        Returns:
            Error budget status
        """
        slo = self.slos.get(slo_id)
        if not slo:
            return {}
        
        history = self.compliance_history.get(slo_id, [])
        
        if not history:
            return {
                "slo_id": slo_id,
                "total_budget": 100 - slo.target,
                "remaining_budget": 100 - slo.target,
                "status": "healthy",
            }
        
        # Calculate remaining budget
        latest = history[-1]
        remaining = latest.error_budget_remaining
        
        # Determine status
        if remaining > 50:
            status = "healthy"
        elif remaining > 20:
            status = "warning"
        elif remaining > 0:
            status = "critical"
        else:
            status = "exhausted"
        
        return {
            "slo_id": slo_id,
            "total_budget": 100 - slo.target,
            "remaining_budget": remaining,
            "remaining_percent": remaining / (100 - slo.target) * 100 if slo.target < 100 else 0,
            "status": status,
            "burn_rate": latest.error_budget_burn_rate,
        }
    
    def get_slo_summary(self) -> dict[str, Any]:
        """Get summary of all SLOs.
        
        Returns:
            SLO summary
        """
        summary = {
            "total_slos": len(self.slos),
            "slos": [],
        }
        
        for slo_id, slo in self.slos.items():
            budget_status = self.get_error_budget_status(slo_id)
            
            summary["slos"].append({
                "slo_id": slo_id,
                "name": slo.name,
                "target": slo.target,
                "window_days": slo.window_days,
                "error_budget_remaining": budget_status.get("remaining_budget", 0),
                "status": budget_status.get("status", "unknown"),
            })
        
        return summary
    
    def _calculate_error_budget(self, current: float, target: float) -> float:
        """Calculate remaining error budget.
        
        Args:
            current: Current value
            target: Target value
            
        Returns:
            Remaining error budget percentage
        """
        if current >= target:
            return 100 - target
        
        error_rate = target - current
        return (target - error_rate) / target * 100
    
    def _calculate_burn_rate(
        self,
        total_budget: float,
        remaining_budget: float,
        window_days: int,
    ) -> float:
        """Calculate error budget burn rate.
        
        Args:
            total_budget: Total error budget
            remaining_budget: Remaining error budget
            window_days: Window in days
            
        Returns:
            Burn rate
        """
        consumed = total_budget - remaining_budget
        if total_budget == 0:
            return 0.0
        
        burn_rate = (consumed / total_budget) * 100
        
        # Normalize to daily rate
        daily_burn_rate = burn_rate / window_days
        
        return daily_burn_rate


class ReliabilityEngineer:
    """Automate reliability engineering tasks."""
    
    def __init__(self, slo_manager: SLOManager):
        """Initialize reliability engineer.
        
        Args:
            slo_manager: SLO manager instance
        """
        self.slo_manager = slo_manager
        self.remediation_actions: dict[str, list[dict[str, Any]]] = {}
    
    def register_remediation(
        self,
        slo_id: str,
        condition: str,
        action: callable,
    ) -> None:
        """Register remediation action.
        
        Args:
            slo_id: SLO identifier
            condition: Condition to trigger action
            action: Remediation action
        """
        if slo_id not in self.remediation_actions:
            self.remediation_actions[slo_id] = []
        
        self.remediation_actions[slo_id].append({
            "condition": condition,
            "action": action,
        })
    
    def evaluate_and_remediate(self, slo_id: str, current_value: float) -> dict[str, Any]:
        """Evaluate SLO and apply remediation if needed.
        
        Args:
            slo_id: SLO identifier
            current_value: Current SLI value
            
        Returns:
            Remediation result
        """
        compliance = self.slo_manager.check_compliance(slo_id, current_value)
        
        if compliance.compliant:
            return {
                "action_required": False,
                "compliance": compliance.dict(),
            }
        
        # Check for remediation actions
        actions = self.remediation_actions.get(slo_id, [])
        
        for action_def in actions:
            if self._evaluate_condition(action_def["condition"], compliance):
                try:
                    result = action_def["action"](compliance)
                    logger.info(f"Remediation action executed for {slo_id}")
                    return {
                        "action_required": True,
                        "action_executed": True,
                        "result": result,
                        "compliance": compliance.dict(),
                    }
                except Exception as e:
                    logger.error(f"Remediation action failed: {e}")
                    return {
                        "action_required": True,
                        "action_executed": False,
                        "error": str(e),
                        "compliance": compliance.dict(),
                    }
        
        return {
            "action_required": True,
            "action_executed": False,
            "reason": "No remediation action defined",
            "compliance": compliance.dict(),
        }
    
    def _evaluate_condition(self, condition: str, compliance: SLOCompliance) -> bool:
        """Evaluate remediation condition.
        
        Args:
            condition: Condition string
            compliance: SLO compliance
            
        Returns:
            True if condition met
        """
        # Simplified - actual implementation would parse conditions
        if condition == "error_budget_critical":
            return compliance.error_budget_remaining < 20
        elif condition == "error_budget_exhausted":
            return compliance.error_budget_remaining <= 0
        elif condition == "high_burn_rate":
            return compliance.error_budget_burn_rate > 5.0
        
        return False