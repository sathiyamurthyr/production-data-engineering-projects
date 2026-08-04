"""
Enterprise Compliance Policy Engine
Policy management, validation, and enforcement
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    CCPA = "ccpa"
    NIST = "nist"
    FISMA = "fisma"


class PolicyStatus(str, Enum):
    """Policy status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ControlStatus(str, Enum):
    """Control implementation status"""
    NOT_IMPLEMENTED = "not_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    AUTOMATED = "automated"


@dataclass
class ComplianceControl:
    """Compliance control"""
    control_id: str
    framework: ComplianceFramework
    name: str
    description: str
    status: ControlStatus
    implementation_notes: str
    automated_checks: List[str]
    manual_checks: List[str]
    evidence_required: List[str]
    metadata: Dict[str, Any]


@dataclass
class CompliancePolicy:
    """Compliance policy"""
    policy_id: str
    name: str
    description: str
    framework: ComplianceFramework
    controls: List[ComplianceControl]
    status: PolicyStatus
    effective_date: datetime
    review_date: datetime
    owner: str
    metadata: Dict[str, Any]


class CompliancePolicyEngine:
    """
    Enterprise compliance policy engine
    Manages compliance policies and controls
    """

    def __init__(self):
        self.policies: Dict[str, CompliancePolicy] = {}
        self.control_registry: Dict[str, ComplianceControl] = {}

    async def create_policy(self, policy: CompliancePolicy) -> CompliancePolicy:
        """
        Create compliance policy

        Args:
            policy: Compliance policy

        Returns:
            Created policy
        """
        self.policies[policy.policy_id] = policy

        # Register controls
        for control in policy.controls:
            self.control_registry[control.control_id] = control

        logger.info(f"Compliance policy created - {policy.policy_id}")

        return policy

    async def get_policy(self, policy_id: str) -> Optional[CompliancePolicy]:
        """
        Get compliance policy

        Args:
            policy_id: Policy identifier

        Returns:
            Compliance policy or None
        """
        return self.policies.get(policy_id)

    async def list_policies(
        self,
        framework: Optional[ComplianceFramework] = None
    ) -> List[CompliancePolicy]:
        """
        List compliance policies

        Args:
            framework: Filter by framework

        Returns:
            List of policies
        """
        policies = list(self.policies.values())

        if framework:
            policies = [p for p in policies if p.framework == framework]

        return policies

    async def validate_compliance(
        self,
        policy_id: str,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate compliance against policy

        Args:
            policy_id: Policy identifier
            evidence: Compliance evidence

        Returns:
            Validation result
        """
        if policy_id not in self.policies:
            raise ValueError("Policy not found")

        policy = self.policies[policy_id]

        validation_result = {
            "policy_id": policy_id,
            "framework": policy.framework.value,
            "validated_at": datetime.utcnow().isoformat(),
            "controls": {},
            "overall_compliance": 0.0
        }

        # Validate each control
        compliant_controls = 0

        for control in policy.controls:
            control_result = await self._validate_control(control, evidence)
            validation_result["controls"][control.control_id] = control_result

            if control_result["compliant"]:
                compliant_controls += 1

        # Calculate overall compliance
        validation_result["overall_compliance"] = (
            compliant_controls / len(policy.controls) if policy.controls else 0.0
        )

        return validation_result

    async def _validate_control(
        self,
        control: ComplianceControl,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate single control"""
        result = {
            "control_id": control.control_id,
            "name": control.name,
            "compliant": False,
            "evidence_provided": [],
            "evidence_missing": [],
            "findings": []
        }

        # Check automated controls
        for check in control.automated_checks:
            if check in evidence:
                result["evidence_provided"].append(check)
            else:
                result["evidence_missing"].append(check)

        # Check manual controls
        for check in control.manual_checks:
            if check in evidence:
                result["evidence_provided"].append(check)
            else:
                result["evidence_missing"].append(check)

        # Determine compliance
        if not result["evidence_missing"]:
            result["compliant"] = True
        else:
            result["findings"].append(f"Missing evidence: {', '.join(result['evidence_missing'])}")

        return result

    async def add_control(
        self,
        policy_id: str,
        control: ComplianceControl
    ):
        """
        Add control to policy

        Args:
            policy_id: Policy identifier
            control: Compliance control
        """
        if policy_id not in self.policies:
            raise ValueError("Policy not found")

        self.policies[policy_id].controls.append(control)
        self.control_registry[control.control_id] = control

        logger.info(f"Control {control.control_id} added to policy {policy_id}")

    async def get_control(self, control_id: str) -> Optional[ComplianceControl]:
        """
        Get compliance control

        Args:
            control_id: Control identifier

        Returns:
            Compliance control or None
        """
        return self.control_registry.get(control_id)

    async def update_control_status(
        self,
        control_id: str,
        status: ControlStatus
    ):
        """
        Update control implementation status

        Args:
            control_id: Control identifier
            status: New status
        """
        if control_id not in self.control_registry:
            raise ValueError("Control not found")

        self.control_registry[control_id].status = status
        logger.info(f"Control {control_id} status updated to {status}")

    async def generate_compliance_report(
        self,
        framework: ComplianceFramework
    ) -> Dict[str, Any]:
        """
        Generate compliance report

        Args:
            framework: Compliance framework

        Returns:
            Compliance report
        """
        report = {
            "framework": framework.value,
            "generated_at": datetime.utcnow().isoformat(),
            "total_policies": 0,
            "total_controls": 0,
            "controls_by_status": {
                "not_implemented": 0,
                "partially_implemented": 0,
                "implemented": 0,
                "automated": 0
            },
            "policies": []
        }

        # Aggregate data
        for policy in self.policies.values():
            if policy.framework != framework:
                continue

            report["total_policies"] += 1

            policy_data = {
                "policy_id": policy.policy_id,
                "name": policy.name,
                "controls": len(policy.controls),
                "compliance_score": 0.0
            }

            compliant_controls = 0

            for control in policy.controls:
                report["total_controls"] += 1
                report["controls_by_status"][control.status.value] += 1

                if control.status in [
                    ControlStatus.IMPLEMENTED,
                    ControlStatus.AUTOMATED
                ]:
                    compliant_controls += 1

            if policy.controls:
                policy_data["compliance_score"] = (
                    compliant_controls / len(policy.controls)
                )

            report["policies"].append(policy_data)

        return report


class ControlAutomation:
    """
    Compliance control automation
    """

    def __init__(self, policy_engine: CompliancePolicyEngine):
        self.policy_engine = policy_engine
        self.automated_checks: Dict[str, callable] = {}

    def register_check(self, check_name: str, check_function: callable):
        """
        Register automated compliance check

        Args:
            check_name: Check name
            check_function: Check function
        """
        self.automated_checks[check_name] = check_function
        logger.info(f"Automated check registered: {check_name}")

    async def run_automated_checks(
        self,
        control_id: str
    ) -> Dict[str, Any]:
        """
        Run automated compliance checks

        Args:
            control_id: Control identifier

        Returns:
            Check results
        """
        control = await self.policy_engine.get_control(control_id)

        if not control:
            raise ValueError("Control not found")

        results = {
            "control_id": control_id,
            "checks": {},
            "passed": 0,
            "failed": 0
        }

        for check_name in control.automated_checks:
            if check_name in self.automated_checks:
                try:
                    check_result = await self.automated_checks[check_name]()
                    results["checks"][check_name] = {
                        "status": "passed" if check_result else "failed",
                        "result": check_result
                    }

                    if check_result:
                        results["passed"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    results["checks"][check_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    results["failed"] += 1

        return results

    async def schedule_compliance_scan(
        self,
        policy_id: str,
        schedule_cron: str
    ):
        """
        Schedule automated compliance scan

        Args:
            policy_id: Policy identifier
            schedule_cron: Cron schedule
        """
        # In production, integrate with scheduler (Airflow, etc.)
        logger.info(f"Compliance scan scheduled for policy {policy_id}: {schedule_cron}")