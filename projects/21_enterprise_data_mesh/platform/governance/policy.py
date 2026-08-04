"""Data Mesh Governance Policy Models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PolicyType(str, Enum):
    """Types of governance policies."""

    SCHEMA = "schema"
    ACCESS = "access"
    RETENTION = "retention"
    QUALITY = "quality"
    SECURITY = "security"


class EnforcementMode(str, Enum):
    """Policy enforcement modes."""

    PREVENT = "prevent"
    ALERT = "alert"
    AUDIT = "audit"


class PolicyViolation(BaseModel):
    """Represents a policy violation."""

    policy_id: str
    domain: str
    product: str
    severity: str = "warning"  # critical, warning, info
    message: str
    details: dict[str, Any]
    timestamp: datetime = datetime.now()
    resolved: bool = False


@dataclass
class DataPolicy:
    """Governance policy definition."""

    id: str
    domain: str
    policy_type: PolicyType
    rules: dict[str, Any]
    enforcement: EnforcementMode
    version: str
    description: str = ""

    def validate(self, product: dict[str, Any]) -> PolicyViolation | None:
        """Validate a data product against this policy.

        Returns None if validation passes, PolicyViolation if it fails.
        """
        validator = PolicyValidator.create(self.policy_type)
        return validator.validate(product, self)


class PolicyValidator:
    """Factory for policy validators."""

    @staticmethod
    def create(policy_type: PolicyType) -> "BasePolicyValidator":
        """Create appropriate validator for policy type."""
        validators: dict[PolicyType, type["BasePolicyValidator"]] = {
            PolicyType.SCHEMA: SchemaValidator(),
            PolicyType.ACCESS: AccessValidator(),
            PolicyType.RETENTION: RetentionValidator(),
            PolicyType.QUALITY: QualityValidator(),
            PolicyType.SECURITY: SecurityValidator(),
        }
        return validators[policy_type]


class BasePolicyValidator:
    """Base class for policy validators."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        """Validate product against policy. Override in subclasses."""
        raise NotImplementedError


class SchemaValidator(BasePolicyValidator):
    """Validator for schema policies."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        schema = product.get("schema", {})
        fields = schema.get("fields", [])

        # Check required fields
        required_fields = policy.rules.get("required_fields", [])
        field_names = [f.get("name") for f in fields]

        missing = [f for f in required_fields if f not in field_names]
        if missing:
            return PolicyViolation(
                policy_id=policy.id,
                domain=product.get("domain", ""),
                product=product.get("name", ""),
                severity="critical",
                message=f"Missing required fields: {missing}",
                details={"missing_fields": missing},
            )
        return None


class AccessValidator(BasePolicyValidator):
    """Validator for access policies."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        # Check PII handling
        pii_fields = policy.rules.get("pii_fields", [])
        if pii_fields and not policy.rules.get("masking_required"):
            return PolicyViolation(
                policy_id=policy.id,
                domain=product.get("domain", ""),
                product=product.get("name", ""),
                severity="critical",
                message="PII fields require masking",
                details={"pii_fields": pii_fields},
            )
        return None


class RetentionValidator(BasePolicyValidator):
    """Validator for retention policies."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        # Check retention compliance
        days = policy.rules.get("days", 0)
        if days > 3650:
            return PolicyViolation(
                policy_id=policy.id,
                domain=product.get("domain", ""),
                product=product.get("name", ""),
                severity="warning",
                message=f"Long retention period: {days} days",
                details={"retention_days": days},
            )
        return None


class QualityValidator(BasePolicyValidator):
    """Validator for quality policies."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        # Placeholder for quality validation
        return None


class SecurityValidator(BasePolicyValidator):
    """Validator for security policies."""

    def validate(self, product: dict[str, Any], policy: DataPolicy) -> PolicyViolation | None:
        # Check encryption requirements
        if not policy.rules.get("encryption_at_rest", True):
            return PolicyViolation(
                policy_id=policy.id,
                domain=product.get("domain", ""),
                product=product.get("name", ""),
                severity="critical",
                message="Encryption at rest required",
                details={},
            )
        return None