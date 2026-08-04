"""
Governance Service
Manages platform policies, compliance, and governance workflows
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://platform:platform@platform-postgres:5432/platform"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ============================================================================
# Enums
# ============================================================================

class PolicyType(str, Enum):
    """Policy type enumeration."""
    SECURITY = "security"
    COST = "cost"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    NAMING = "naming"


class PolicySeverity(str, Enum):
    """Policy severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EvaluationResult(str, Enum):
    """Policy evaluation result."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


# ============================================================================
# Database Models
# ============================================================================

class PolicyModel(Base):
    """Policy database model."""
    __tablename__ = "policies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    policy_type = Column(String, nullable=False, index=True)
    severity = Column(String, default=PolicySeverity.MEDIUM.value)
    description = Column(Text)
    rego_code = Column(Text)  # OPA Rego policy code
    sentinel_code = Column(Text)  # Terraform Sentinel code
    enabled = Column(Boolean, default=True)
    tags = Column(JSON)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)


class PolicyViolationModel(Base):
    """Policy violation database model."""
    __tablename__ = "policy_violations"

    id = Column(String, primary_key=True)
    policy_id = Column(String, nullable=False, index=True)
    resource_id = Column(String, index=True)
    resource_type = Column(String, index=True)
    severity = Column(String, index=True)
    message = Column(Text)
    remediation = Column(Text)
    context = Column(JSON)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ComplianceFrameworkModel(Base):
    """Compliance framework database model."""
    __tablename__ = "compliance_frameworks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    version = Column(String)
    description = Column(Text)
    controls = Column(JSON)  # List of controls
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLogModel(Base):
    """Audit log database model."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    severity = Column(String, index=True)
    user_id = Column(String, index=True)
    resource_id = Column(String, index=True)
    resource_type = Column(String, index=True)
    action = Column(String)
    result = Column(String)
    details = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class Policy(BaseModel):
    """Policy model."""
    id: str
    name: str
    policy_type: PolicyType
    severity: PolicySeverity
    description: str
    rego_code: Optional[str] = None
    sentinel_code: Optional[str] = None
    enabled: bool = True
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    created_by: str


class PolicyViolation(BaseModel):
    """Policy violation model."""
    id: str
    policy_id: str
    resource_id: str
    resource_type: str
    severity: PolicySeverity
    message: str
    remediation: Optional[str] = None
    context: Dict[str, Any] = {}
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime


class ComplianceFramework(BaseModel):
    """Compliance framework model."""
    id: str
    name: str
    version: str
    description: str
    controls: List[Dict[str, Any]]
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class AuditLog(BaseModel):
    """Audit log model."""
    id: str
    event_type: str
    severity: str
    user_id: str
    resource_id: str
    resource_type: str
    action: str
    result: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class PolicyEvaluationRequest(BaseModel):
    """Policy evaluation request."""
    resource: Dict[str, Any]
    policy_types: Optional[List[PolicyType]] = None


class PolicyEvaluationResult(BaseModel):
    """Policy evaluation result."""
    allowed: bool
    violations: List[PolicyViolation]
    warnings: List[str]


class ComplianceCheckRequest(BaseModel):
    """Compliance check request."""
    framework_id: str
    start_time: datetime
    end_time: datetime


class ComplianceReport(BaseModel):
    """Compliance report model."""
    framework_id: str
    framework_name: str
    total_controls: int
    passed_controls: int
    failed_controls: int
    compliance_score: float
    violations: List[PolicyViolation]
    generated_at: datetime


# ============================================================================
# Governance Service
# ============================================================================

class GovernanceService:
    """Governance management service."""

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.violations: Dict[str, List[PolicyViolation]] = {}
        self.audit_logs: List[AuditLog] = []

    async def initialize(self):
        """Initialize governance service."""
        logger.info("Initializing governance service...")

        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Load policies from database
        await self._load_policies()

        logger.info(f"Governance service initialized with {len(self.policies)} policies")

    async def _load_policies(self):
        """Load policies from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(PolicyModel).where(PolicyModel.enabled == True))
            policies = result.scalars().all()

            for policy in policies:
                self.policies[policy.id] = Policy(
                    id=policy.id,
                    name=policy.name,
                    policy_type=PolicyType(policy.policy_type),
                    severity=PolicySeverity(policy.severity),
                    description=policy.description,
                    rego_code=policy.rego_code,
                    sentinel_code=policy.sentinel_code,
                    enabled=policy.enabled,
                    tags=policy.tags or [],
                    metadata=policy.metadata or {},
                    created_at=policy.created_at,
                    updated_at=policy.updated_at,
                    created_by=policy.created_by
                )

    async def health_check(self) -> Dict[str, str]:
        """Health check for governance service."""
        try:
            # Test database connection
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                await session.execute(select(PolicyModel).limit(1))

            return {
                "status": "healthy",
                "policy_count": str(len(self.policies)),
                "enabled_policies": str(sum(1 for p in self.policies.values() if p.enabled))
            }
        except Exception as e:
            logger.error(f"Governance service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def list_policies(
        self,
        policy_type: Optional[PolicyType] = None,
        enabled: Optional[bool] = None
    ) -> List[Policy]:
        """
        List all policies with optional filters.
        
        Args:
            policy_type: Filter by policy type
            enabled: Filter by enabled status
            
        Returns:
            List of policies
        """
        policies = list(self.policies.values())

        if policy_type:
            policies = [p for p in policies if p.policy_type == policy_type]

        if enabled is not None:
            policies = [p for p in policies if p.enabled == enabled]

        return policies

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Policy or None if not found
        """
        return self.policies.get(policy_id)

    async def create_policy(self, policy: Policy) -> Policy:
        """
        Create a new policy.
        
        Args:
            policy: Policy to create
            
        Returns:
            Created policy
        """
        # Save to database
        async with AsyncSessionLocal() as session:
            model = PolicyModel(
                id=policy.id,
                name=policy.name,
                policy_type=policy.policy_type.value,
                severity=policy.severity.value,
                description=policy.description,
                rego_code=policy.rego_code,
                sentinel_code=policy.sentinel_code,
                enabled=policy.enabled,
                tags=policy.tags,
                metadata=policy.metadata,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
                created_by=policy.created_by
            )
            session.add(model)
            await session.commit()

        # Add to cache
        self.policies[policy.id] = policy

        logger.info(f"Created policy: {policy.id} - {policy.name}")
        return policy

    async def evaluate_template(self, request: Any) -> PolicyEvaluationResult:
        """
        Evaluate template against policies.
        
        Args:
            request: Template request
            
        Returns:
            Evaluation result
        """
        violations = []
        warnings = []

        # Get applicable policies
        applicable_policies = [
            p for p in self.policies.values()
            if p.enabled and p.policy_type in [PolicyType.SECURITY, PolicyType.COST]
        ]

        # Evaluate each policy
        for policy in applicable_policies:
            # This is a simplified evaluation
            # In production, this would use OPA or Sentinel
            result = await self._evaluate_policy(policy, request.variables)

            if result == EvaluationResult.DENY:
                violation = PolicyViolation(
                    id=str(uuid.uuid4()),
                    policy_id=policy.id,
                    resource_id=request.template_id,
                    resource_type="template",
                    severity=policy.severity,
                    message=f"Template violates policy: {policy.name}",
                    remediation=await self._get_remediation(policy),
                    created_at=datetime.utcnow()
                )
                violations.append(violation)

                # Save violation
                await self._save_violation(violation)

        return PolicyEvaluationResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )

    async def evaluate_provisioning(
        self,
        request: Any,
        user: Any
    ) -> PolicyEvaluationResult:
        """
        Evaluate provisioning request against policies.
        
        Args:
            request: Provisioning request
            user: Requesting user
            
        Returns:
            Evaluation result
        """
        violations = []
        warnings = []

        # Get applicable policies
        applicable_policies = [
            p for p in self.policies.values()
            if p.enabled
        ]

        # Evaluate each policy
        for policy in applicable_policies:
            # This is a simplified evaluation
            # In production, this would use OPA or Sentinel
            result = await self._evaluate_provisioning_policy(policy, request, user)

            if result == EvaluationResult.DENY:
                violation = PolicyViolation(
                    id=str(uuid.uuid4()),
                    policy_id=policy.id,
                    resource_id=request.name,
                    resource_type="provisioning",
                    severity=policy.severity,
                    message=f"Provisioning violates policy: {policy.name}",
                    remediation=await self._get_remediation(policy),
                    context={
                        "environment": request.environment,
                        "team": request.team,
                        "user": user.username if user else "system"
                    },
                    created_at=datetime.utcnow()
                )
                violations.append(violation)

                # Save violation
                await self._save_violation(violation)

            elif result == EvaluationResult.WARN:
                warnings.append(f"Warning: {policy.name}")

        # Check if approval is required
        requires_approval = any(v.severity in [PolicySeverity.HIGH, PolicySeverity.CRITICAL] for v in violations)

        return PolicyEvaluationResult(
            allowed=len([v for v in violations if v.severity == PolicySeverity.CRITICAL]) == 0,
            violations=violations,
            warnings=warnings,
            requires_approval=requires_approval
        )

    async def _evaluate_policy(self, policy: Policy, context: Dict[str, Any]) -> EvaluationResult:
        """
        Evaluate a single policy.
        
        Args:
            policy: Policy to evaluate
            context: Evaluation context
            
        Returns:
            Evaluation result
        """
        # This is a simplified evaluation
        # In production, this would call OPA or Sentinel

        # Example: Check for expensive instance types
        if policy.policy_type == PolicyType.COST:
            variables = context.get("variables", {})
            instance_type = variables.get("instance_type", "")

            expensive_instances = ["p4d.24xlarge", "p3.16xlarge", "p2.8xlarge"]
            if instance_type in expensive_instances:
                return EvaluationResult.DENY

        # Example: Check for encryption
        if policy.policy_type == PolicyType.SECURITY:
            variables = context.get("variables", {})
            encryption_enabled = variables.get("encryption_enabled", False)

            if not encryption_enabled:
                return EvaluationResult.DENY

        return EvaluationResult.ALLOW

    async def _evaluate_provisioning_policy(
        self,
        policy: Policy,
        request: Any,
        user: Any
    ) -> EvaluationResult:
        """
        Evaluate provisioning policy.
        
        Args:
            policy: Policy to evaluate
            request: Provisioning request
            user: Requesting user
            
        Returns:
            Evaluation result
        """
        # This is a simplified evaluation
        # In production, this would call OPA or Sentinel

        # Example: Check environment
        if policy.policy_type == PolicyType.OPERATIONAL:
            if hasattr(request, 'environment'):
                if request.environment == "prod":
                    # Require approval for production
                    return EvaluationResult.WARN

        # Example: Check naming convention
        if policy.policy_type == PolicyType.NAMING:
            if hasattr(request, 'name'):
                # Check naming convention
                if not request.name.startswith(request.team):
                    return EvaluationResult.DENY

        return EvaluationResult.ALLOW

    async def _get_remediation(self, policy: Policy) -> str:
        """Get remediation steps for policy violation."""
        if policy.policy_type == PolicyType.COST:
            return "Consider using a smaller instance type or request budget approval"
        elif policy.policy_type == PolicyType.SECURITY:
            return "Enable encryption and security features"
        elif policy.policy_type == PolicyType.COMPLIANCE:
            return "Review compliance requirements and adjust configuration"
        else:
            return "Review policy requirements and adjust request"

    async def _save_violation(self, violation: PolicyViolation):
        """Save policy violation to database."""
        async with AsyncSessionLocal() as session:
            model = PolicyViolationModel(
                id=violation.id,
                policy_id=violation.policy_id,
                resource_id=violation.resource_id,
                resource_type=violation.resource_type,
                severity=violation.severity.value,
                message=violation.message,
                remediation=violation.remediation,
                context=violation.context,
                resolved=violation.resolved,
                resolved_at=violation.resolved_at,
                resolved_by=violation.resolved_by,
                created_at=violation.created_at
            )
            session.add(model)
            await session.commit()

        # Add to cache
        if violation.resource_id not in self.violations:
            self.violations[violation.resource_id] = []

        self.violations[violation.resource_id].append(violation)

    async def log_audit_event(
        self,
        event_type: str,
        severity: str,
        user_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        result: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log audit event.
        
        Args:
            event_type: Type of event
            severity: Event severity
            user_id: User ID
            resource_id: Resource ID
            resource_type: Resource type
            action: Action performed
            result: Result of action
            details: Additional details
            ip_address: IP address
            user_agent: User agent
        """
        event_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create audit log
        audit_log = AuditLog(
            id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now
        )

        # Save to database
        async with AsyncSessionLocal() as session:
            model = AuditLogModel(
                id=event_id,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                action=action,
                result=result,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=now
            )
            session.add(model)
            await session.commit()

        # Add to cache
        self.audit_logs.append(audit_log)

        logger.debug(f"Logged audit event: {event_type}")

    async def get_violations(
        self,
        resource_id: Optional[str] = None,
        policy_id: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[PolicyViolation]:
        """
        Get policy violations with optional filters.
        
        Args:
            resource_id: Filter by resource ID
            policy_id: Filter by policy ID
            resolved: Filter by resolved status
            
        Returns:
            List of violations
        """
        violations = []

        for violation_list in self.violations.values():
            violations.extend(violation_list)

        # Apply filters
        if resource_id:
            violations = [v for v in violations if v.resource_id == resource_id]

        if policy_id:
            violations = [v for v in violations if v.policy_id == policy_id]

        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]

        # Sort by created_at descending
        violations.sort(key=lambda v: v.created_at, reverse=True)

        return violations

    async def resolve_violation(
        self,
        violation_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """
        Resolve a policy violation.
        
        Args:
            violation_id: Violation ID
            resolved_by: User resolving the violation
            resolution_notes: Optional resolution notes
            
        Returns:
            True if resolved, False if not found
        """
        # Find violation
        for violation_list in self.violations.values():
            for violation in violation_list:
                if violation.id == violation_id:
                    violation.resolved = True
                    violation.resolved_at = datetime.utcnow()
                    violation.resolved_by = resolved_by

                    # Update database
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import update
                        stmt = update(PolicyViolationModel).where(
                            PolicyViolationModel.id == violation_id
                        ).values(
                            resolved=True,
                            resolved_at=datetime.utcnow(),
                            resolved_by=resolved_by
                        )
                        await session.execute(stmt)
                        await session.commit()

                    logger.info(f"Resolved violation: {violation_id}")
                    return True

        return False

    async def check_compliance(
        self,
        framework_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> ComplianceReport:
        """
        Check compliance for a framework.
        
        Args:
            framework_id: Framework ID
            start_time: Start time for check
            end_time: End time for check
            
        Returns:
            Compliance report
        """
        # Get framework
        framework = await self._get_compliance_framework(framework_id)
        if not framework:
            raise ValueError(f"Compliance framework {framework_id} not found")

        # Check controls
        controls = framework.controls
        passed = 0
        failed = 0
        violations = []

        for control in controls:
            # This is a simplified check
            # In production, this would evaluate actual controls
            control_passed = await self._check_control(control, start_time, end_time)

            if control_passed:
                passed += 1
            else:
                failed += 1
                violation = PolicyViolation(
                    id=str(uuid.uuid4()),
                    policy_id=control.get("policy_id"),
                    resource_id=framework_id,
                    resource_type="compliance",
                    severity=PolicySeverity.HIGH,
                    message=f"Control failed: {control.get('name')}",
                    remediation=control.get("remediation"),
                    created_at=datetime.utcnow()
                )
                violations.append(violation)

        # Calculate compliance score
        total = len(controls)
        score = (passed / total * 100) if total > 0 else 0

        return ComplianceReport(
            framework_id=framework_id,
            framework_name=framework.name,
            total_controls=total,
            passed_controls=passed,
            failed_controls=failed,
            compliance_score=score,
            violations=violations,
            generated_at=datetime.utcnow()
        )

    async def _get_compliance_framework(self, framework_id: str) -> Optional[ComplianceFramework]:
        """Get compliance framework by ID."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(ComplianceFrameworkModel).where(ComplianceFrameworkModel.id == framework_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return ComplianceFramework(
                id=model.id,
                name=model.name,
                version=model.version,
                description=model.description,
                controls=model.controls,
                enabled=model.enabled,
                created_at=model.created_at,
                updated_at=model.updated_at
            )

    async def _check_control(
        self,
        control: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if a control is compliant."""
        # This is a simplified check
        # In production, this would evaluate actual control requirements
        return True

    async def get_audit_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs with optional filters.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            
        Returns:
            List of audit logs
        """
        logs = self.audit_logs

        # Apply filters
        if event_type:
            logs = [l for l in logs if l.event_type == event_type]

        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        if start_time:
            logs = [l for l in logs if l.created_at >= start_time]

        if end_time:
            logs = [l for l in logs if l.created_at <= end_time]

        # Sort by created_at descending
        logs.sort(key=lambda l: l.created_at, reverse=True)

        return logs[:limit]

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get governance statistics.
        
        Returns:
            Statistics dictionary
        """
        # Count violations by severity
        violations_by_severity = {}
        for violation_list in self.violations.values():
            for violation in violation_list:
                severity = violation.severity.value
                violations_by_severity[severity] = violations_by_severity.get(severity, 0) + 1

        # Count policies by type
        policies_by_type = {}
        for policy in self.policies.values():
            policy_type = policy.policy_type.value
            policies_by_type[policy_type] = policies_by_type.get(policy_type, 0) + 1

        return {
            "total_policies": len(self.policies),
            "enabled_policies": sum(1 for p in self.policies.values() if p.enabled),
            "policies_by_type": policies_by_type,
            "total_violations": sum(len(v) for v in self.violations.values()),
            "violations_by_severity": violations_by_severity,
            "unresolved_violations": sum(
                1 for vlist in self.violations.values()
                for v in vlist if not v.resolved
            )
        }