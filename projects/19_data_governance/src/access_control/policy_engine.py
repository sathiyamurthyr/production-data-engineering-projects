"""
Policy Engine & Dynamic Data Masking Module
===========================================
Evaluates attribute-based policies (ABAC/PBAC) and dynamically masks sensitive
values (Redaction, Hashing, Partial Obfuscation) based on user roles and sensitivity tags.
"""

import hashlib
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from src.access_control.rbac_manager import RBACManager

logger = logging.getLogger(__name__)

@dataclass
class PolicyRule:
    """Represents an access control or masking rule."""
    rule_id: str
    target_sensitivity: str  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    required_permission: str
    action: str  # "ALLOW", "DENY", "MASK"
    masking_type: Optional[str] = None  # "REDACT", "HASH", "PARTIAL_EMAIL", "PARTIAL_PHONE", "PARTIAL_SSN"


@dataclass
class Policy:
    """Represents a named policy collection."""
    policy_id: str
    policy_name: str
    rules: List[PolicyRule] = field(default_factory=list)


class PolicyEngine:
    """
    Evaluates policy rules and executes data masking transformations.
    """

    MASK_REDACTED = "REDACTED"

    def __init__(self, rbac_manager: RBACManager) -> None:
        self.rbac = rbac_manager
        self._default_policy = self._build_default_policy()

    def _build_default_policy(self) -> Policy:
        rules = [
            PolicyRule("R1_PUBLIC", "PUBLIC", "read", "ALLOW"),
            PolicyRule("R2_INTERNAL", "INTERNAL", "read", "ALLOW"),
            PolicyRule("R3_CONFIDENTIAL_FULL", "CONFIDENTIAL", "read_unmasked_pii", "ALLOW"),
            PolicyRule("R4_CONFIDENTIAL_MASKED", "CONFIDENTIAL", "read_masked_pii", "MASK", "HASH"),
            PolicyRule("R5_RESTRICTED_FULL", "RESTRICTED", "read_unmasked_pii", "ALLOW"),
            PolicyRule("R6_RESTRICTED_MASKED", "RESTRICTED", "read_masked_pii", "MASK", "REDACT"),
        ]
        return Policy("POL_DEFAULT", "Enterprise Standard Data Governance Policy", rules)

    @staticmethod
    def mask_value(value: Any, pii_type: str, masking_type: str) -> str:
        """
        Apply data masking transformation to a single scalar value.
        
        Args:
            value: Raw input value.
            pii_type: PII type string (EMAIL, PHONE, SSN, CREDIT_CARD, etc.).
            masking_type: Transformation method ("REDACT", "HASH", "PARTIAL_EMAIL", etc.).
            
        Returns:
            Masked string representation of the value.
        """
        if value is None or str(value).strip() == "":
            return ""

        val_str = str(value).strip()

        if masking_type == "REDACT":
            return "[REDACTED]"

        if masking_type == "HASH":
            return hashlib.sha256(val_str.encode("utf-8")).hexdigest()[:16]

        if masking_type == "PARTIAL_EMAIL" or (masking_type == "PARTIAL" and pii_type == "EMAIL"):
            if "@" in val_str:
                name, domain = val_str.split("@", 1)
                masked_name = name[0] + "***" if len(name) > 1 else "*"
                return f"{masked_name}@{domain}"
            return "a***@domain.com"

        if masking_type == "PARTIAL_PHONE" or (masking_type == "PARTIAL" and pii_type == "PHONE"):
            digits = re.sub(r"\D", "", val_str)
            if len(digits) >= 4:
                return f"***-***-{digits[-4:]}"
            return "***-***-XXXX"

        if masking_type == "PARTIAL_SSN" or (masking_type == "PARTIAL" and pii_type == "SSN"):
            digits = re.sub(r"\D", "", val_str)
            if len(digits) >= 4:
                return f"XXX-XX-{digits[-4:]}"
            return "XXX-XX-XXXX"

        # Default fallback
        return "[MASKED]"

    def evaluate_field_access(
        self,
        user_id: str,
        value: Any,
        pii_type: str,
        sensitivity_level: str = "RESTRICTED",
    ) -> Dict[str, Any]:
        """
        Evaluate user policy and return either raw or masked value based on permissions.
        
        Args:
            user_id: User requesting access.
            value: Raw field value.
            pii_type: Type of PII.
            sensitivity_level: Field sensitivity level.
            
        Returns:
            Dict containing {"decision": "ALLOW"|"MASK"|"DENY", "value": masked_or_raw_val}
        """
        # Admin / unmasked PII permission -> return raw value
        if self.rbac.check_permission(user_id, "read_unmasked_pii"):
            return {"decision": "ALLOW", "value": value, "masked": False}

        # Masked PII permission -> return masked value
        if self.rbac.check_permission(user_id, "read_masked_pii") or self.rbac.check_permission(user_id, "read"):
            masking_type = "HASH" if sensitivity_level == "CONFIDENTIAL" else "PARTIAL"
            masked_val = self.mask_value(value, pii_type, masking_type)
            return {"decision": "MASK", "value": masked_val, "masked": True}

        # No permission -> DENY
        return {"decision": "DENY", "value": "[ACCESS_DENIED]", "masked": True}
