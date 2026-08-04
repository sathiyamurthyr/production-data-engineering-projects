"""
Enterprise Compliance Validator
Automated compliance validation and checks
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation status"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Validation result"""
    check_id: str
    check_name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    validated_at: datetime
    metadata: Dict[str, Any]


class ComplianceValidator:
    """
    Enterprise compliance validator
    Automated compliance checking
    """

    def __init__(self):
        self.validation_rules: Dict[str, Dict[str, Any]] = {}
        self.validation_history: List[ValidationResult] = []

    async def validate_encryption(
        self,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate encryption requirements

        Args:
            data: Data to validate

        Returns:
            Validation result
        """
        check_id = "encryption-at-rest"
        errors = []

        # Check if sensitive data is encrypted
        if "sensitive_fields" in data:
            for field in data["sensitive_fields"]:
                if field in data and not data[field].get("encrypted", False):
                    errors.append(f"Field {field} is not encrypted")

        status = ValidationStatus.FAIL if errors else ValidationStatus.PASS

        result = ValidationResult(
            check_id=check_id,
            check_name="Encryption at Rest",
            status=status,
            message="Encryption validation completed",
            details={"errors": errors},
            validated_at=datetime.utcnow(),
            metadata={"category": "encryption"}
        )

        self.validation_history.append(result)

        return result

    async def validate_access_control(
        self,
        access_log: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate access control compliance

        Args:
            access_log: Access log data

        Returns:
            Validation result
        """
        check_id = "access-control"
        errors = []

        # Check for unauthorized access
        if access_log.get("unauthorized_attempts", 0) > 0:
            errors.append(f"Unauthorized access attempts detected: {access_log['unauthorized_attempts']}")

        # Check for privilege escalation
        if access_log.get("privilege_escalations", 0) > 0:
            errors.append(f"Privilege escalation detected: {access_log['privilege_escalations']}")

        status = ValidationStatus.FAIL if errors else ValidationStatus.PASS

        result = ValidationResult(
            check_id=check_id,
            check_name="Access Control",
            status=status,
            message="Access control validation completed",
            details={"errors": errors},
            validated_at=datetime.utcnow(),
            metadata={"category": "access_control"}
        )

        self.validation_history.append(result)

        return result

    async def validate_data_classification(
        self,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate data classification

        Args:
            data: Data to validate

        Returns:
            Validation result
        """
        check_id = "data-classification"
        errors = []
        warnings = []

        # Check if all sensitive fields are classified
        if "fields" in data:
            unclassified = []
            for field_name, field_data in data["fields"].items():
                if field_data.get("sensitive", False) and not field_data.get("classification"):
                    unclassified.append(field_name)

            if unclassified:
                errors.append(f"Unclassified sensitive fields: {', '.join(unclassified)}")

        # Check for proper handling of classified data
        if data.get("classification") == "restricted" and not data.get("encrypted", False):
            errors.append("Restricted data must be encrypted")

        status = ValidationStatus.FAIL if errors else (ValidationStatus.WARNING if warnings else ValidationStatus.PASS)

        result = ValidationResult(
            check_id=check_id,
            check_name="Data Classification",
            status=status,
            message="Data classification validation completed",
            details={"errors": errors, "warnings": warnings},
            validated_at=datetime.utcnow(),
            metadata={"category": "data_classification"}
        )

        self.validation_history.append(result)

        return result

    async def validate_audit_logging(
        self,
        audit_config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate audit logging configuration

        Args:
            audit_config: Audit configuration

        Returns:
            Validation result
        """
        check_id = "audit-logging"
        errors = []

        # Check if audit logging is enabled
        if not audit_config.get("enabled", False):
            errors.append("Audit logging is not enabled")

        # Check retention period
        retention_days = audit_config.get("retention_days", 0)
        if retention_days < 365:
            errors.append(f"Audit log retention period too short: {retention_days} days (minimum 365)")

        # Check required events are logged
        required_events = ["authentication", "authorization", "data_access"]
        logged_events = audit_config.get("logged_events", [])
        missing_events = [e for e in required_events if e not in logged_events]

        if missing_events:
            errors.append(f"Missing audit events: {', '.join(missing_events)}")

        status = ValidationStatus.FAIL if errors else ValidationStatus.PASS

        result = ValidationResult(
            check_id=check_id,
            check_name="Audit Logging",
            status=status,
            message="Audit logging validation completed",
            details={"errors": errors},
            validated_at=datetime.utcnow(),
            metadata={"category": "audit"}
        )

        self.validation_history.append(result)

        return result

    async def validate_password_policy(
        self,
        password_policy: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate password policy

        Args:
            password_policy: Password policy

        Returns:
            Validation result
        """
        check_id = "password-policy"
        errors = []
        warnings = []

        # Check minimum length
        min_length = password_policy.get("min_length", 0)
        if min_length < 12:
            errors.append(f"Password minimum length too short: {min_length} (minimum 12)")

        # Check complexity requirements
        if not password_policy.get("require_uppercase", False):
            warnings.append("Password policy does not require uppercase letters")

        if not password_policy.get("require_lowercase", False):
            warnings.append("Password policy does not require lowercase letters")

        if not password_policy.get("require_numbers", False):
            warnings.append("Password policy does not require numbers")

        if not password_policy.get("require_special_chars", False):
            warnings.append("Password policy does not require special characters")

        # Check expiration
        max_age_days = password_policy.get("max_age_days", 0)
        if max_age_days == 0:
            warnings.append("Password expiration not configured")
        elif max_age_days > 90:
            warnings.append(f"Password expiration too long: {max_age_days} days (recommended: 90)")

        status = ValidationStatus.FAIL if errors else (ValidationStatus.WARNING if warnings else ValidationStatus.PASS)

        result = ValidationResult(
            check_id=check_id,
            check_name="Password Policy",
            status=status,
            message="Password policy validation completed",
            details={"errors": errors, "warnings": warnings},
            validated_at=datetime.utcnow(),
            metadata={"category": "authentication"}
        )

        self.validation_history.append(result)

        return result

    async def validate_network_security(
        self,
        network_config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate network security

        Args:
            network_config: Network configuration

        Returns:
            Validation result
        """
        check_id = "network-security"
        errors = []

        # Check TLS configuration
        if not network_config.get("tls_enabled", False):
            errors.append("TLS is not enabled")

        # Check TLS version
        min_tls_version = network_config.get("min_tls_version", "")
        if min_tls_version not in ["1.2", "1.3"]:
            errors.append(f"Weak TLS version: {min_tls_version} (minimum 1.2)")

        # Check firewall rules
        firewall_rules = network_config.get("firewall_rules", [])
        if not firewall_rules:
            errors.append("No firewall rules configured")

        # Check for open ports
        open_ports = network_config.get("open_ports", [])
        dangerous_ports = [22, 3389, 3306, 5432]  # SSH, RDP, MySQL, PostgreSQL
        exposed_dangerous = [p for p in open_ports if p in dangerous_ports]

        if exposed_dangerous:
            errors.append(f"Dangerous ports exposed: {exposed_dangerous}")

        status = ValidationStatus.FAIL if errors else ValidationStatus.PASS

        result = ValidationResult(
            check_id=check_id,
            check_name="Network Security",
            status=status,
            message="Network security validation completed",
            details={"errors": errors},
            validated_at=datetime.utcnow(),
            metadata={"category": "network"}
        )

        self.validation_history.append(result)

        return result

    async def run_full_validation(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run full compliance validation

        Args:
            config: Configuration to validate

        Returns:
            Validation report
        """
        report = {
            "validated_at": datetime.utcnow().isoformat(),
            "results": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }

        # Run all validations
        validations = [
            ("encryption", self.validate_encryption(config.get("encryption", {}))),
            ("access_control", self.validate_access_control(config.get("access_control", {}))),
            ("data_classification", self.validate_data_classification(config.get("data_classification", {}))),
            ("audit_logging", self.validate_audit_logging(config.get("audit_logging", {}))),
            ("password_policy", self.validate_password_policy(config.get("password_policy", {}))),
            ("network_security", self.validate_network_security(config.get("network_security", {}))),
        ]

        for check_name, validation in validations:
            report["results"][check_name] = {
                "check_id": validation.check_id,
                "check_name": validation.check_name,
                "status": validation.status.value,
                "message": validation.message,
                "details": validation.details
            }

            report["summary"]["total_checks"] += 1

            if validation.status == ValidationStatus.PASS:
                report["summary"]["passed"] += 1
            elif validation.status == ValidationStatus.FAIL:
                report["summary"]["failed"] += 1
            elif validation.status == ValidationStatus.WARNING:
                report["summary"]["warnings"] += 1

        return report

    async def get_validation_history(
        self,
        check_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ValidationResult]:
        """
        Get validation history

        Args:
            check_id: Filter by check ID
            limit: Maximum results

        Returns:
            List of validation results
        """
        results = self.validation_history

        if check_id:
            results = [r for r in results if r.check_id == check_id]

        # Sort by timestamp (newest first)
        results.sort(key=lambda r: r.validated_at, reverse=True)

        return results[:limit]


class ComplianceReporter:
    """
    Compliance reporting service
    Generates compliance reports
    """

    def __init__(self, validator: ComplianceValidator):
        self.validator = validator

    async def generate_compliance_summary(
        self,
        framework: str
    ) -> Dict[str, Any]:
        """
        Generate compliance summary

        Args:
            framework: Compliance framework

        Returns:
            Compliance summary
        """
        summary = {
            "framework": framework,
            "generated_at": datetime.utcnow().isoformat(),
            "overall_status": "compliant",
            "checks": {},
            "failed_checks": [],
            "warnings": []
        }

        # Get recent validations
        history = await self.validator.get_validation_history(limit=100)

        for result in history:
            check_name = result.check_name

            if check_name not in summary["checks"]:
                summary["checks"][check_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "warnings": 0
                }

            summary["checks"][check_name]["total"] += 1

            if result.status == ValidationStatus.PASS:
                summary["checks"][check_name]["passed"] += 1
            elif result.status == ValidationStatus.FAIL:
                summary["checks"][check_name]["failed"] += 1
                summary["failed_checks"].append({
                    "check": check_name,
                    "message": result.message,
                    "details": result.details
                })
            elif result.status == ValidationStatus.WARNING:
                summary["checks"][check_name]["warnings"] += 1
                summary["warnings"].append({
                    "check": check_name,
                    "message": result.message
                })

        # Determine overall status
        if summary["failed_checks"]:
            summary["overall_status"] = "non_compliant"

        return summary