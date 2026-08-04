"""
Enterprise Data Masking Service
Dynamic and static data masking, tokenization
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class MaskingType(str, Enum):
    """Data masking types"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    TOKENIZATION = "tokenization"
    NULLIFICATION = "nullification"
    HASHING = "hashing"
    SHUFFLING = "shuffling"


class MaskingRule(str, Enum):
    """Masking rules"""
    FULL_MASK = "full_mask"
    PARTIAL_MASK = "partial_mask"
    HASH = "hash"
    REDACT = "redact"
    REPLACE = "replace"
    FORMAT_PRESERVING = "format_preserving"


@dataclass
class MaskingPolicy:
    """Data masking policy"""
    policy_id: str
    name: str
    description: str
    data_classification: str
    masking_type: MaskingType
    masking_rule: MaskingRule
    fields: List[str]
    conditions: Dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class DataMaskingService:
    """
    Enterprise data masking service
    Supports dynamic and static data masking
    """

    def __init__(self):
        self.policies: Dict[str, MaskingPolicy] = {}
        self.token_vault: Dict[str, str] = {}
        self.reverse_vault: Dict[str, str] = {}

    async def mask_data(
        self,
        data: Union[Dict[str, Any], str],
        policy_id: str,
        user_context: Dict[str, Any] = None
    ) -> Union[Dict[str, Any], str]:
        """
        Apply masking policy to data

        Args:
            data: Data to mask
            policy_id: Masking policy ID
            user_context: User context for dynamic masking

        Returns:
            Masked data
        """
        if policy_id not in self.policies:
            raise ValueError("Policy not found")

        policy = self.policies[policy_id]

        if not policy.enabled:
            return data

        # Check conditions
        if not self._evaluate_conditions(policy.conditions, user_context):
            return data

        # Apply masking based on type
        if policy.masking_type == MaskingType.STATIC:
            return self._apply_static_masking(data, policy)
        elif policy.masking_type == MaskingType.DYNAMIC:
            return self._apply_dynamic_masking(data, policy, user_context)
        elif policy.masking_type == MaskingType.TOKENIZATION:
            return self._apply_tokenization(data, policy)
        else:
            return data

    async def create_policy(self, policy: MaskingPolicy) -> MaskingPolicy:
        """
        Create masking policy

        Args:
            policy: Masking policy

        Returns:
            Created policy
        """
        self.policies[policy.policy_id] = policy
        logger.info(f"Masking policy created - {policy.policy_id}")
        return policy

    def _apply_static_masking(
        self,
        data: Union[Dict[str, Any], str],
        policy: MaskingPolicy
    ) -> Union[Dict[str, Any], str]:
        """Apply static masking"""
        if isinstance(data, dict):
            masked = data.copy()
            for field in policy.fields:
                if field in masked:
                    masked[field] = self._mask_value(
                        masked[field],
                        policy.masking_rule
                    )
            return masked
        else:
            return self._mask_value(data, policy.masking_rule)

    def _apply_dynamic_masking(
        self,
        data: Union[Dict[str, Any], str],
        policy: MaskingPolicy,
        user_context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """Apply dynamic masking based on user context"""
        # Check if user has permission to view unmasked data
        if user_context and self._has_unmasked_permission(user_context, policy):
            return data

        return self._apply_static_masking(data, policy)

    def _apply_tokenization(
        self,
        data: Union[Dict[str, Any], str],
        policy: MaskingPolicy
    ) -> Union[Dict[str, Any], str]:
        """Apply tokenization"""
        if isinstance(data, dict):
            tokenized = data.copy()
            for field in policy.fields:
                if field in tokenized:
                    tokenized[field] = self._tokenize_value(tokenized[field])
            return tokenized
        else:
            return self._tokenize_value(data)

    def _mask_value(
        self,
        value: Any,
        rule: MaskingRule
    ) -> Any:
        """Apply masking rule to value"""
        if value is None:
            return None

        value_str = str(value)

        if rule == MaskingRule.FULL_MASK:
            return "[REDACTED]"

        elif rule == MaskingRule.PARTIAL_MASK:
            # Keep first and last character
            if len(value_str) > 2:
                return value_str[0] + "*" * (len(value_str) - 2) + value_str[-1]
            return "*" * len(value_str)

        elif rule == MaskingRule.HASH:
            import hashlib
            return hashlib.sha256(value_str.encode()).hexdigest()[:16]

        elif rule == MaskingRule.REDACT:
            return "[REDACTED]"

        elif rule == MaskingRule.REPLACE:
            return "XXXXXX"

        elif rule == MaskingRule.FORMAT_PRESERVING:
            # Preserve format but mask content
            return self._preserve_format(value_str)

        return value

    def _tokenize_value(self, value: str) -> str:
        """Tokenize value"""
        if value in self.token_vault:
            return self.token_vault[value]

        # Generate token
        import uuid
        token = f"TOKEN-{uuid.uuid4().hex[:16].upper()}"

        # Store in vault
        self.token_vault[value] = token
        self.reverse_vault[token] = value

        return token

    def _preserve_format(self, value: str) -> str:
        """Preserve format while masking"""
        # Replace alphanumeric characters with X
        return re.sub(r'[A-Za-z0-9]', 'X', value)

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> bool:
        """Evaluate masking conditions"""
        if not conditions:
            return True

        # Check user role
        if "allowed_roles" in conditions:
            user_role = user_context.get("role")
            if user_role not in conditions["allowed_roles"]:
                return True  # Apply masking

        # Check environment
        if "environments" in conditions:
            environment = user_context.get("environment")
            if environment not in conditions["environments"]:
                return True

        return False

    def _has_unmasked_permission(
        self,
        user_context: Dict[str, Any],
        policy: MaskingPolicy
    ) -> bool:
        """Check if user has permission to view unmasked data"""
        # Check if user has special permission
        return user_context.get("can_view_sensitive", False)

    def detokenize(self, token: str) -> Optional[str]:
        """
        Detokenize token to original value

        Args:
            token: Token to detokenize

        Returns:
            Original value or None
        """
        return self.reverse_vault.get(token)

    async def mask_database_table(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        policy_id: str
    ) -> List[Dict[str, Any]]:
        """
        Mask database table data

        Args:
            table_name: Table name
            data: Table data
            policy_id: Masking policy

        Returns:
            Masked data
        """
        masked_data = []

        for row in data:
            masked_row = await self.mask_data(row, policy_id)
            masked_data.append(masked_row)

        logger.info(f"Masked {len(masked_data)} rows from {table_name}")

        return masked_data

    async def get_masking_policies(
        self,
        data_classification: Optional[str] = None
    ) -> List[MaskingPolicy]:
        """
        Get masking policies

        Args:
            data_classification: Filter by classification

        Returns:
            List of policies
        """
        policies = list(self.policies.values())

        if data_classification:
            policies = [p for p in policies if p.data_classification == data_classification]

        return policies


class TokenizationService:
    """
    Enterprise tokenization service
    Reversible data protection
    """

    def __init__(self):
        self.token_vault: Dict[str, str] = {}
        self.reverse_vault: Dict[str, str] = {}

    async def tokenize(
        self,
        value: str,
        data_type: str
    ) -> str:
        """
        Tokenize sensitive data

        Args:
            value: Value to tokenize
            data_type: Type of data

        Returns:
            Token
        """
        # Check if already tokenized
        if value in self.token_vault:
            return self.token_vault[value]

        # Generate format-preserving token
        token = self._generate_format_preserving_token(value, data_type)

        # Store mapping
        self.token_vault[value] = token
        self.reverse_vault[token] = value

        logger.info(f"Data tokenized: {data_type}")

        return token

    async def detokenize(self, token: str) -> Optional[str]:
        """
        Detokenize token

        Args:
            token: Token to detokenize

        Returns:
            Original value
        """
        return self.reverse_vault.get(token)

    def _generate_format_preserving_token(
        self,
        value: str,
        data_type: str
    ) -> str:
        """Generate format-preserving token"""
        import secrets

        if data_type == "credit_card":
            # Preserve credit card format
            if len(value) == 16:
                return "XXXX-XXXX-XXXX-" + value[-4:]
            elif len(value) == 15:
                return "XXXX-XXXXXX-X-" + value[-4:]

        elif data_type == "ssn":
            # Preserve SSN format
            return "XXX-XX-XXXX"

        elif data_type == "email":
            # Preserve email format
            return "XXXX@XXXX.XXX"

        elif data_type == "phone":
            # Preserve phone format
            return "(XXX) XXX-XXXX"

        # Default: return token
        return f"TOKEN-{secrets.token_hex(8).upper()}"

    async def tokenize_database_row(
        self,
        row: Dict[str, Any],
        tokenization_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Tokenize database row

        Args:
            row: Database row
            tokenization_rules: Field to data_type mapping

        Returns:
            Tokenized row
        """
        tokenized = row.copy()

        for field, data_type in tokenization_rules.items():
            if field in tokenized and tokenized[field]:
                tokenized[field] = await self.tokenize(
                    tokenized[field],
                    data_type
                )

        return tokenized

    def get_tokenization_stats(self) -> Dict[str, Any]:
        """
        Get tokenization statistics

        Returns:
            Tokenization stats
        """
        return {
            "total_tokens": len(self.token_vault),
            "total_detokenizations": len(self.reverse_vault)
        }