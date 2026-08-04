"""
Policy Engine for Cross-Cloud Governance

This module provides policy enforcement across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Policy types"""
    SECURITY = "security"
    COMPLIANCE = "compliance"
    COST = "cost"
    OPERATIONS = "operations"
    DATA = "data"


class PolicySeverity(str, Enum):
    """Policy violation severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Policy(BaseModel):
    """Policy definition"""
    policy_id: str
    name: str
    description: str
    policy_type: PolicyType
    cloud: Optional[CloudProvider] = None  # None for cross-cloud
    severity: PolicySeverity
    rules: Dict[str, Any]
    remediation: str
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class PolicyViolation(BaseModel):
    """Policy violation"""
    violation_id: str
    policy_id: str
    resource_id: str
    resource_type: str
    cloud: CloudProvider
    severity: PolicySeverity
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class PolicyEngine:
    """
    Cross-cloud policy engine
    
    This service provides:
    - Policy definition and management
    - Policy evaluation
    - Violation detection
    - Automated remediation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize policy engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.policies: Dict[str, Policy] = {}
        self.violations: Dict[str, PolicyViolation] = {}
        
        # Load default policies
        self._load_default_policies()
        
        logger.info("Policy Engine initialized")
    
    def _load_default_policies(self) -> None:
        """Load default policies"""
        default_policies = [
            Policy(
                policy_id="require-encryption-at-rest",
                name="Require Encryption at Rest",
                description="All storage resources must have encryption at rest enabled",
                policy_type=PolicyType.SECURITY,
                severity=PolicySeverity.CRITICAL,
                rules={
                    "resource_types": ["storage_account", "s3_bucket", "rds_instance"],
                    "encryption_required": True
                },
                remediation="Enable encryption at rest for the resource",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Policy(
                policy_id="deny-public-access",
                name="Deny Public Access",
                description="Resources must not have public access enabled",
                policy_type=PolicyType.SECURITY,
                severity=PolicySeverity.CRITICAL,
                rules={
                    "resource_types": ["storage_account", "s3_bucket", "sql_database"],
                    "public_access_allowed": False
                },
                remediation="Disable public access for the resource",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Policy(
                policy_id="require-tags",
                name="Require Resource Tags",
                description="All resources must have mandatory tags",
                policy_type=PolicyType.OPERATIONS,
                severity=PolicySeverity.HIGH,
                rules={
                    "required_tags": ["environment", "team", "cost-center"],
                    "resource_types": ["*"]
                },
                remediation="Add required tags to the resource",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Policy(
                policy_id="cost-budget-limit",
                name="Cost Budget Limit",
                description="Monthly cost must not exceed budget",
                policy_type=PolicyType.COST,
                severity=PolicySeverity.HIGH,
                rules={
                    "max_monthly_cost": 10000,
                    "alert_threshold": 0.8
                },
                remediation="Review and optimize resource costs",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Policy(
                policy_id="require-backup",
                name="Require Backup Policy",
                description="Critical resources must have backup enabled",
                policy_type=PolicyType.OPERATIONS,
                severity=PolicySeverity.HIGH,
                rules={
                    "resource_types": ["database", "vm"],
                    "backup_required": True
                },
                remediation="Enable backup for the resource",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for policy in default_policies:
            self.policies[policy.policy_id] = policy
    
    async def create_policy(self, policy: Policy) -> Policy:
        """
        Create new policy
        
        Args:
            policy: Policy definition
            
        Returns:
            Created policy
        """
        logger.info(f"Creating policy: {policy.policy_id}")
        
        if policy.policy_id in self.policies:
            raise ValueError(f"Policy already exists: {policy.policy_id}")
        
        self.policies[policy.policy_id] = policy
        
        logger.info(f"Policy created: {policy.policy_id}")
        return policy
    
    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get policy by ID
        
        Args:
            policy_id: Policy ID
            
        Returns:
            Policy if found, None otherwise
        """
        return self.policies.get(policy_id)
    
    async def evaluate_resource(
        self,
        resource_id: str,
        resource_type: str,
        cloud: CloudProvider,
        resource_config: Dict[str, Any]
    ) -> List[PolicyViolation]:
        """
        Evaluate resource against policies
        
        Args:
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            resource_config: Resource configuration
            
        Returns:
            List of policy violations
        """
        logger.info(f"Evaluating resource {resource_id} against policies")
        
        violations = []
        
        for policy in self.policies.values():
            # Skip if policy is disabled
            if not policy.enabled:
                continue
            
            # Skip if policy is cloud-specific and doesn't match
            if policy.cloud and policy.cloud != cloud:
                continue
            
            # Evaluate policy
            violation = await self._evaluate_policy(
                policy, resource_id, resource_type, cloud, resource_config
            )
            
            if violation:
                violations.append(violation)
        
        logger.info(f"Found {len(violations)} violations for resource {resource_id}")
        return violations
    
    async def _evaluate_policy(
        self,
        policy: Policy,
        resource_id: str,
        resource_type: str,
        cloud: CloudProvider,
        resource_config: Dict[str, Any]
    ) -> Optional[PolicyViolation]:
        """
        Evaluate single policy against resource
        
        Args:
            policy: Policy to evaluate
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            resource_config: Resource configuration
            
        Returns:
            Policy violation if found, None otherwise
        """
        rules = policy.rules
        
        # Check resource type
        if "*" not in rules.get("resource_types", []) and resource_type not in rules.get("resource_types", []):
            return None
        
        # Check encryption at rest
        if rules.get("encryption_required") and not resource_config.get("encrypted", False):
            return PolicyViolation(
                violation_id=f"violation-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{resource_id}",
                policy_id=policy.policy_id,
                resource_id=resource_id,
                resource_type=resource_type,
                cloud=cloud,
                severity=policy.severity,
                description=f"Resource {resource_id} does not have encryption at rest enabled",
                detected_at=datetime.utcnow()
            )
        
        # Check public access
        if "public_access_allowed" in rules and resource_config.get("public_access", True) == rules["public_access_allowed"]:
            return PolicyViolation(
                violation_id=f"violation-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{resource_id}",
                policy_id=policy.policy_id,
                resource_id=resource_id,
                resource_type=resource_type,
                cloud=cloud,
                severity=policy.severity,
                description=f"Resource {resource_id} has public access enabled",
                detected_at=datetime.utcnow()
            )
        
        # Check required tags
        required_tags = rules.get("required_tags", [])
        if required_tags:
            resource_tags = resource_config.get("tags", {})
            missing_tags = [tag for tag in required_tags if tag not in resource_tags]
            
            if missing_tags:
                return PolicyViolation(
                    violation_id=f"violation-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{resource_id}",
                    policy_id=policy.policy_id,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    cloud=cloud,
                    severity=policy.severity,
                    description=f"Resource {resource_id} is missing required tags: {', '.join(missing_tags)}",
                    detected_at=datetime.utcnow()
                )
        
        return None
    
    async def resolve_violation(
        self,
        violation_id: str,
        resolution: str,
        resolved_by: str
    ) -> Optional[PolicyViolation]:
        """
        Resolve policy violation
        
        Args:
            violation_id: Violation ID
            resolution: Resolution description
            resolved_by: User who resolved
            
        Returns:
            Updated policy violation
        """
        violation = self.violations.get(violation_id)
        if not violation:
            logger.warning(f"Policy violation not found: {violation_id}")
            return None
        
        # Update violation
        violation.resolved_at = datetime.utcnow()
        violation.resolution = resolution
        
        logger.info(f"Policy violation resolved: {violation_id}")
        return violation
    
    async def list_policies(
        self,
        policy_type: Optional[PolicyType] = None,
        cloud: Optional[CloudProvider] = None
    ) -> List[Policy]:
        """
        List policies
        
        Args:
            policy_type: Policy type (optional)
            cloud: Cloud provider (optional)
            
        Returns:
            List of policies
        """
        policies = list(self.policies.values())
        
        if policy_type:
            policies = [p for p in policies if p.policy_type == policy_type]
        
        if cloud:
            policies = [p for p in policies if p.cloud is None or p.cloud == cloud]
        
        return policies
    
    async def list_violations(
        self,
        cloud: Optional[CloudProvider] = None,
        severity: Optional[PolicySeverity] = None,
        resolved: Optional[bool] = None
    ) -> List[PolicyViolation]:
        """
        List policy violations
        
        Args:
            cloud: Cloud provider (optional)
            severity: Severity level (optional)
            resolved: Resolution status (optional)
            
        Returns:
            List of violations
        """
        violations = list(self.violations.values())
        
        if cloud:
            violations = [v for v in violations if v.cloud == cloud]
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        if resolved is not None:
            violations = [v for v in violations if (v.resolved_at is not None) == resolved]
        
        return violations
    
    async def get_policy_analytics(self) -> Dict:
        """
        Get policy analytics
        
        Returns:
            Policy statistics
        """
        total_policies = len(self.policies)
        enabled_policies = len([p for p in self.policies.values() if p.enabled])
        
        total_violations = len(self.violations)
        unresolved_violations = len([v for v in self.violations.values() if v.resolved_at is None])
        
        # Count by severity
        by_severity = {}
        for violation in self.violations.values():
            severity = violation.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Count by type
        by_type = {}
        for policy in self.policies.values():
            policy_type = policy.policy_type.value
            by_type[policy_type] = by_type.get(policy_type, 0) + 1
        
        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "total_violations": total_violations,
            "unresolved_violations": unresolved_violations,
            "violations_by_severity": by_severity,
            "policies_by_type": by_type
        }