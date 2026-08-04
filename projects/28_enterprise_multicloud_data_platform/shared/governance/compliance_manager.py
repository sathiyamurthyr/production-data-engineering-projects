"""
Compliance Manager for Cross-Cloud Governance

This module provides compliance monitoring and reporting across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider
from .policy_engine import PolicyViolation, PolicySeverity

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci-dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"


class ComplianceStatus(str, Enum):
    """Compliance status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non-compliant"
    PARTIALLY_COMPLIANT = "partially-compliant"
    UNKNOWN = "unknown"


class ComplianceControl(BaseModel):
    """Compliance control"""
    control_id: str
    framework: ComplianceFramework
    name: str
    description: str
    requirements: List[str]
    implementation: str
    status: ComplianceStatus
    last_checked: datetime
    evidence: List[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    """Compliance report"""
    report_id: str
    framework: ComplianceFramework
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    overall_status: ComplianceStatus
    controls: List[ComplianceControl]
    violations: List[PolicyViolation]
    recommendations: List[str]
    generated_by: str


class ComplianceManager:
    """
    Cross-cloud compliance manager
    
    This service provides:
    - Compliance framework management
    - Control assessment
    - Compliance reporting
    - Gap analysis
    """
    
    def __init__(self, config: Dict):
        """
        Initialize compliance manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.controls: Dict[str, ComplianceControl] = {}
        self.reports: Dict[str, ComplianceReport] = {}
        
        # Load default controls
        self._load_default_controls()
        
        logger.info("Compliance Manager initialized")
    
    def _load_default_controls(self) -> None:
        """Load default compliance controls"""
        default_controls = [
            ComplianceControl(
                control_id="gdpr-encryption",
                framework=ComplianceFramework.GDPR,
                name="Data Encryption",
                description="Personal data must be encrypted at rest and in transit",
                requirements=[
                    "All storage must have encryption at rest",
                    "All network traffic must use TLS 1.2+",
                    "Encryption keys must be managed securely"
                ],
                implementation="Use cloud-native encryption with customer-managed keys",
                status=ComplianceStatus.COMPLIANT,
                last_checked=datetime.utcnow(),
                evidence=["encryption-policy.pdf", "key-management-config.yaml"]
            ),
            ComplianceControl(
                control_id="gdpr-access-control",
                framework=ComplianceFramework.GDPR,
                name="Access Control",
                description="Access to personal data must be restricted and audited",
                requirements=[
                    "RBAC must be implemented",
                    "Access must be logged",
                    "Regular access reviews must be conducted"
                ],
                implementation="Azure AD RBAC with audit logging",
                status=ComplianceStatus.COMPLIANT,
                last_checked=datetime.utcnow(),
                evidence=["rbac-policy.pdf", "access-logs-sample.txt"]
            ),
            ComplianceControl(
                control_id="hipaa-audit-logging",
                framework=ComplianceFramework.HIPAA,
                name="Audit Logging",
                description="All access to PHI must be logged and monitored",
                requirements=[
                    "Comprehensive audit logging enabled",
                    "Logs retained for 6 years",
                    "Regular log review"
                ],
                implementation="Cloud-native audit logging with centralized storage",
                status=ComplianceStatus.COMPLIANT,
                last_checked=datetime.utcnow(),
                evidence=["audit-logging-policy.pdf", "log-retention-config.yaml"]
            ),
            ComplianceControl(
                control_id="pci-data-protection",
                framework=ComplianceFramework.PCI_DSS,
                name="Data Protection",
                description="Cardholder data must be protected",
                requirements=[
                    "Encryption of cardholder data",
                    "Network segmentation",
                    "Regular vulnerability scanning"
                ],
                implementation="Encryption at rest and in transit, network isolation",
                status=ComplianceStatus.PARTIALLY_COMPLIANT,
                last_checked=datetime.utcnow(),
                evidence=["encryption-config.yaml", "network-policy.pdf"]
            ),
            ComplianceControl(
                control_id="soc2-security",
                framework=ComplianceFramework.SOC2,
                name="Security Controls",
                description="Security controls must be implemented and monitored",
                requirements=[
                    "Firewall protection",
                    "Intrusion detection",
                    "Security monitoring"
                ],
                implementation="Cloud-native security controls with SIEM integration",
                status=ComplianceStatus.COMPLIANT,
                last_checked=datetime.utcnow(),
                evidence=["security-architecture.pdf", "soc2-report.pdf"]
            )
        ]
        
        for control in default_controls:
            self.controls[control.control_id] = control
    
    async def create_control(
        self,
        control: ComplianceControl
    ) -> ComplianceControl:
        """
        Create new compliance control
        
        Args:
            control: Compliance control
            
        Returns:
            Created control
        """
        logger.info(f"Creating compliance control: {control.control_id}")
        
        if control.control_id in self.controls:
            raise ValueError(f"Control already exists: {control.control_id}")
        
        self.controls[control.control_id] = control
        
        logger.info(f"Compliance control created: {control.control_id}")
        return control
    
    async def get_control(
        self,
        control_id: str
    ) -> Optional[ComplianceControl]:
        """
        Get compliance control by ID
        
        Args:
            control_id: Control ID
            
        Returns:
            Control if found, None otherwise
        """
        return self.controls.get(control_id)
    
    async def assess_control(
        self,
        control_id: str,
        status: ComplianceStatus,
        evidence: List[str],
        assessed_by: str
    ) -> Optional[ComplianceControl]:
        """
        Assess compliance control
        
        Args:
            control_id: Control ID
            status: Compliance status
            evidence: List of evidence
            assessed_by: User who assessed
            
        Returns:
            Updated control
        """
        control = self.controls.get(control_id)
        if not control:
            logger.warning(f"Compliance control not found: {control_id}")
            return None
        
        # Update control
        control.status = status
        control.last_checked = datetime.utcnow()
        control.evidence = evidence
        
        logger.info(f"Compliance control assessed: {control_id} - {status}")
        return control
    
    async def evaluate_compliance(
        self,
        framework: ComplianceFramework,
        cloud: Optional[CloudProvider] = None
    ) -> Dict[str, Any]:
        """
        Evaluate compliance for framework
        
        Args:
            framework: Compliance framework
            cloud: Cloud provider (optional)
            
        Returns:
            Compliance evaluation results
        """
        logger.info(f"Evaluating compliance for {framework}")
        
        # Get controls for framework
        framework_controls = [
            c for c in self.controls.values()
            if c.framework == framework
        ]
        
        if not framework_controls:
            return {
                "framework": framework.value,
                "status": ComplianceStatus.UNKNOWN,
                "compliant_controls": 0,
                "total_controls": 0,
                "compliance_percentage": 0
            }
        
        # Count compliant controls
        compliant = len([c for c in framework_controls if c.status == ComplianceStatus.COMPLIANT])
        total = len(framework_controls)
        
        # Determine overall status
        if compliant == total:
            overall_status = ComplianceStatus.COMPLIANT
        elif compliant == 0:
            overall_status = ComplianceStatus.NON_COMPLIANT
        else:
            overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        
        return {
            "framework": framework.value,
            "status": overall_status,
            "compliant_controls": compliant,
            "total_controls": total,
            "compliance_percentage": (compliant / total * 100) if total > 0 else 0,
            "controls": [
                {
                    "control_id": c.control_id,
                    "name": c.name,
                    "status": c.status,
                    "last_checked": c.last_checked.isoformat()
                }
                for c in framework_controls
            ]
        }
    
    async def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        period_days: int = 30,
        generated_by: str = "system"
    ) -> ComplianceReport:
        """
        Generate compliance report
        
        Args:
            framework: Compliance framework
            period_days: Report period in days
            generated_by: User who generated
            
        Returns:
            Compliance report
        """
        logger.info(f"Generating compliance report for {framework}")
        
        # Generate report ID
        report_id = f"report-{framework.value}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Get controls for framework
        framework_controls = [
            c for c in self.controls.values()
            if c.framework == framework
        ]
        
        # Evaluate compliance
        evaluation = await self.evaluate_compliance(framework)
        
        # Get violations
        violations = []  # In real implementation, get from policy engine
        
        # Generate recommendations
        recommendations = []
        for control in framework_controls:
            if control.status != ComplianceStatus.COMPLIANT:
                recommendations.append(
                    f"Remediate {control.name}: {control.implementation}"
                )
        
        # Create report
        report = ComplianceReport(
            report_id=report_id,
            framework=framework,
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            overall_status=evaluation["status"],
            controls=framework_controls,
            violations=violations,
            recommendations=recommendations,
            generated_by=generated_by
        )
        
        # Store report
        self.reports[report_id] = report
        
        logger.info(f"Compliance report generated: {report_id}")
        return report
    
    async def get_compliance_dashboard(
        self
    ) -> Dict[str, Any]:
        """
        Get compliance dashboard data
        
        Returns:
            Dashboard data
        """
        dashboard = {
            "total_controls": len(self.controls),
            "compliant_controls": len([c for c in self.controls.values() if c.status == ComplianceStatus.COMPLIANT]),
            "non_compliant_controls": len([c for c in self.controls.values() if c.status == ComplianceStatus.NON_COMPLIANT]),
            "partially_compliant_controls": len([c for c in self.controls.values() if c.status == ComplianceStatus.PARTIALLY_COMPLIANT]),
            "by_framework": {},
            "recent_reports": []
        }
        
        # Count by framework
        for framework in ComplianceFramework:
            framework_controls = [c for c in self.controls.values() if c.framework == framework]
            if framework_controls:
                compliant = len([c for c in framework_controls if c.status == ComplianceStatus.COMPLIANT])
                dashboard["by_framework"][framework.value] = {
                    "total": len(framework_controls),
                    "compliant": compliant,
                    "percentage": (compliant / len(framework_controls) * 100) if framework_controls else 0
                }
        
        # Recent reports
        recent_reports = sorted(
            self.reports.values(),
            key=lambda r: r.generated_at,
            reverse=True
        )[:10]
        
        dashboard["recent_reports"] = [
            {
                "report_id": r.report_id,
                "framework": r.framework.value,
                "status": r.overall_status,
                "generated_at": r.generated_at.isoformat()
            }
            for r in recent_reports
        ]
        
        return dashboard
    
    async def identify_gaps(
        self,
        framework: ComplianceFramework
    ) -> List[Dict[str, Any]]:
        """
        Identify compliance gaps
        
        Args:
            framework: Compliance framework
            
        Returns:
            List of gaps
        """
        gaps = []
        
        # Get controls for framework
        framework_controls = [
            c for c in self.controls.values()
            if c.framework == framework
        ]
        
        for control in framework_controls:
            if control.status != ComplianceStatus.COMPLIANT:
                gaps.append({
                    "control_id": control.control_id,
                    "name": control.name,
                    "status": control.status,
                    "requirements": control.requirements,
                    "implementation": control.implementation,
                    "recommendation": f"Implement {control.name}"
                })
        
        return gaps
    
    async def list_controls(
        self,
        framework: Optional[ComplianceFramework] = None,
        status: Optional[ComplianceStatus] = None
    ) -> List[ComplianceControl]:
        """
        List compliance controls
        
        Args:
            framework: Compliance framework (optional)
            status: Compliance status (optional)
            
        Returns:
            List of controls
        """
        controls = list(self.controls.values())
        
        if framework:
            controls = [c for c in controls if c.framework == framework]
        
        if status:
            controls = [c for c in controls if c.status == status]
        
        return controls
    
    async def list_reports(
        self,
        framework: Optional[ComplianceFramework] = None,
        limit: int = 50
    ) -> List[ComplianceReport]:
        """
        List compliance reports
        
        Args:
            framework: Compliance framework (optional)
            limit: Maximum number of reports
            
        Returns:
            List of reports
        """
        reports = list(self.reports.values())
        
        if framework:
            reports = [r for r in reports if r.framework == framework]
        
        # Sort by generated_at desc
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        
        return reports[:limit]