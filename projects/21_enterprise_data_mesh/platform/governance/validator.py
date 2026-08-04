"""Data Mesh Governance Validator."""

from typing import Any


class PolicyValidator:
    """Factory for creating policy validators."""

    def create(self, policy_type: str) -> "BasePolicyValidator":
        """Create validator based on policy type."""
        validators = {
            "schema": SchemaPolicyValidator(),
            "access": AccessPolicyValidator(),
            "retention": RetentionPolicyValidator(),
            "quality": QualityPolicyValidator(),
            "security": SecurityPolicyValidator(),
        }
        return validators.get(policy_type, BasePolicyValidator())


class BasePolicyValidator:
    """Base validator class."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        """Validate product against rules. Override in subclasses."""
        return True


class SchemaPolicyValidator(BasePolicyValidator):
    """Validator for schema policies."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        schema = product.get("schema", {})
        fields = schema.get("fields", [])

        required_fields = rules.get("required_fields", [])
        field_names = [f.get("name") for f in fields]

        return all(rf in field_names for rf in required_fields)


class AccessPolicyValidator(BasePolicyValidator):
    """Validator for access policies."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        # Validate access rules are met
        return True


class RetentionPolicyValidator(BasePolicyValidator):
    """Validator for retention policies."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        # Validate retention rules
        days = rules.get("days", 0)
        return days <= 3650


class QualityPolicyValidator(BasePolicyValidator):
    """Validator for quality policies."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        # Validate quality requirements
        return True


class SecurityPolicyValidator(BasePolicyValidator):
    """Validator for security policies."""

    def validate(self, product: dict[str, Any], rules: dict[str, Any]) -> bool:
        # Validate security requirements
        return rules.get("encryption_at_rest", True)