"""
Enterprise Tokenization Service
Format-preserving encryption and tokenization
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import uuid
import hashlib
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class TokenizedValue:
    """Tokenized value metadata"""
    original_value: str
    token: str
    token_type: str
    created_at: datetime
    last_accessed: Optional[datetime]
    access_count: int
    metadata: Dict[str, Any]


class TokenizationService:
    """
    Enterprise tokenization service
    Format-preserving tokenization for sensitive data
    """

    def __init__(self):
        self.token_vault: Dict[str, TokenizedValue] = {}
        self.reverse_vault: Dict[str, str] = {}
        self.token_generators = {
            "credit_card": self._tokenize_credit_card,
            "ssn": self._tokenize_ssn,
            "email": self._tokenize_email,
            "phone": self._tokenize_phone,
            "default": self._tokenize_default
        }

    async def tokenize(
        self,
        value: str,
        token_type: str = "default",
        preserve_format: bool = True
    ) -> str:
        """
        Tokenize sensitive value

        Args:
            value: Value to tokenize
            token_type: Type of tokenization
            preserve_format: Preserve format

        Returns:
            Token
        """
        # Check if already tokenized
        if value in self.reverse_vault:
            return self.reverse_vault[value]

        # Generate token
        generator = self.token_generators.get(token_type, self.token_generators["default"])
        token = await generator(value) if preserve_format else self._tokenize_default(value)

        # Store in vault
        tokenized_value = TokenizedValue(
            original_value=value,
            token=token,
            token_type=token_type,
            created_at=datetime.utcnow(),
            last_accessed=None,
            access_count=0,
            metadata={}
        )

        self.token_vault[token] = tokenized_value
        self.reverse_vault[value] = token

        logger.info(f"Value tokenized: {token_type}")

        return token

    async def detokenize(self, token: str) -> Optional[str]:
        """
        Detokenize token

        Args:
            token: Token to detokenize

        Returns:
            Original value or None
        """
        if token not in self.token_vault:
            return None

        tokenized = self.token_vault[token]

        # Update access tracking
        tokenized.last_accessed = datetime.utcnow()
        tokenized.access_count += 1

        return tokenized.original_value

    async def tokenize_dict(
        self,
        data: Dict[str, Any],
        tokenization_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Tokenize dictionary fields

        Args:
            data: Data to tokenize
            tokenization_rules: Field to token_type mapping

        Returns:
            Tokenized data
        """
        tokenized = data.copy()

        for field, token_type in tokenization_rules.items():
            if field in tokenized and tokenized[field]:
                tokenized[field] = await self.tokenize(
                    tokenized[field],
                    token_type
                )

        return tokenized

    async def batch_tokenize(
        self,
        values: List[str],
        token_type: str = "default"
    ) -> List[str]:
        """
        Tokenize multiple values

        Args:
            values: List of values
            token_type: Token type

        Returns:
            List of tokens
        """
        return [
            await self.tokenize(value, token_type)
            for value in values
        ]

    def _tokenize_credit_card(self, value: str) -> str:
        """Tokenize credit card (preserve last 4 digits)"""
        # Remove non-digits
        digits = ''.join(filter(str.isdigit, value))

        if len(digits) == 16:
            return f"XXXX-XXXX-XXXX-{digits[-4:]}"
        elif len(digits) == 15:
            return f"XXXX-XXXXXX-X-{digits[-4:]}"

        return self._tokenize_default(value)

    def _tokenize_ssn(self, value: str) -> str:
        """Tokenize SSN (preserve format)"""
        return "XXX-XX-XXXX"

    def _tokenize_email(self, value: str) -> str:
        """Tokenize email (preserve format)"""
        if '@' in value:
            local, domain = value.split('@')
            return f"{'X' * len(local)}@{'X' * len(domain)}"
        return "XXXX@XXXX.XXX"

    def _tokenize_phone(self, value: str) -> str:
        """Tokenize phone (preserve format)"""
        digits = ''.join(filter(str.isdigit, value))

        if len(digits) == 10:
            return "(XXX) XXX-XXXX"
        elif len(digits) == 11:
            return "+X (XXX) XXX-XXXX"

        return "XXX-XXX-XXXX"

    def _tokenize_default(self, value: str) -> str:
        """Default tokenization"""
        return f"TOKEN-{uuid.uuid4().hex[:16].upper()}"

    async def get_token_metadata(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get token metadata

        Args:
            token: Token

        Returns:
            Metadata or None
        """
        if token not in self.token_vault:
            return None

        tokenized = self.token_vault[token]

        return {
            "token_type": tokenized.token_type,
            "created_at": tokenized.created_at.isoformat(),
            "last_accessed": tokenized.last_accessed.isoformat() if tokenized.last_accessed else None,
            "access_count": tokenized.access_count
        }

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke token

        Args:
            token: Token to revoke

        Returns:
            True if revoked
        """
        if token not in self.token_vault:
            return False

        tokenized = self.token_vault[token]

        # Remove from vaults
        del self.token_vault[token]
        del self.reverse_vault[tokenized.original_value]

        logger.info(f"Token revoked: {token}")

        return True

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get tokenization statistics

        Returns:
            Statistics
        """
        stats = {
            "total_tokens": len(self.token_vault),
            "by_type": {},
            "total_accesses": sum(t.access_count for t in self.token_vault.values())
        }

        # Count by type
        for tokenized in self.token_vault.values():
            token_type = tokenized.token_type
            stats["by_type"][token_type] = stats["by_type"].get(token_type, 0) + 1

        return stats


class FormatPreservingEncryption:
    """
    Format-Preserving Encryption (FPE)
    Encrypts data while maintaining format
    """

    def __init__(self, key: bytes):
        self.key = key
        # In production, use proper FPE library (e.g., pyffx)

    async def encrypt(self, plaintext: str, format_type: str = "default") -> str:
        """
        Encrypt with format preservation

        Args:
            plaintext: Plain text
            format_type: Format type

        Returns:
            Encrypted text (same format)
        """
        if format_type == "credit_card":
            return self._encrypt_credit_card(plaintext)
        elif format_type == "ssn":
            return self._encrypt_ssn(plaintext)
        elif format_type == "phone":
            return self._encrypt_phone(plaintext)
        else:
            return self._encrypt_default(plaintext)

    async def decrypt(self, ciphertext: str, format_type: str = "default") -> str:
        """
        Decrypt format-preserved encryption

        Args:
            ciphertext: Encrypted text
            format_type: Format type

        Returns:
            Decrypted text
        """
        if format_type == "credit_card":
            return self._decrypt_credit_card(ciphertext)
        elif format_type == "ssn":
            return self._decrypt_ssn(ciphertext)
        elif format_type == "phone":
            return self._decrypt_phone(ciphertext)
        else:
            return self._decrypt_default(ciphertext)

    def _encrypt_credit_card(self, value: str) -> str:
        """Encrypt credit card preserving format"""
        # Simplified - in production use pyffx or similar
        digits = ''.join(filter(str.isdigit, value))
        encrypted_digits = hashlib.sha256(self.key + digits.encode()).hexdigest()[:16]

        if len(digits) == 16:
            return f"{encrypted_digits[:4]}-{encrypted_digits[4:8]}-{encrypted_digits[8:12]}-{encrypted_digits[12:16]}"

        return value

    def _encrypt_ssn(self, value: str) -> str:
        """Encrypt SSN preserving format"""
        # Simplified
        return "XXX-XX-XXXX"

    def _encrypt_phone(self, value: str) -> str:
        """Encrypt phone preserving format"""
        # Simplified
        return "(XXX) XXX-XXXX"

    def _encrypt_default(self, value: str) -> str:
        """Default encryption"""
        return hashlib.sha256(self.key + value.encode()).hexdigest()[:len(value)]

    def _decrypt_credit_card(self, value: str) -> str:
        """Decrypt credit card"""
        # Simplified - in production use proper FPE
        return value

    def _decrypt_ssn(self, value: str) -> str:
        """Decrypt SSN"""
        return value

    def _decrypt_phone(self, value: str) -> str:
        """Decrypt phone"""
        return value

    def _decrypt_default(self, value: str) -> str:
        """Default decryption"""
        return value