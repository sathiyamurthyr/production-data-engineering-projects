"""
PII Detection Service
Advanced PII, PHI, and PCI data detection
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """PII data types"""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_RECORD = "medical_record"
    BANK_ACCOUNT = "bank_account"


@dataclass
class PIIMatch:
    """PII detection match"""
    pii_type: PIIType
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    context: str
    metadata: Dict[str, Any]


class PIIDetector:
    """
    Enterprise PII detection service
    Detects and redacts sensitive personal information
    """

    def __init__(self):
        self.patterns = self._load_pii_patterns()
        self.context_window = 50  # Characters before/after match

    async def detect_pii(
        self,
        text: str,
        include_context: bool = True
    ) -> List[PIIMatch]:
        """
        Detect PII in text

        Args:
            text: Text to analyze
            include_context: Include surrounding context

        Returns:
            List of PII matches
        """
        matches = []

        for pii_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    context = self._get_context(text, match.start(), match.end()) if include_context else ""

                    pii_match = PIIMatch(
                        pii_type=pii_type,
                        value=match.group(),
                        confidence=self._calculate_confidence(pii_type, match.group()),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context=context,
                        metadata={"pattern": pattern.pattern}
                    )

                    matches.append(pii_match)

        # Sort by position
        matches.sort(key=lambda m: m.start_pos)

        # Remove overlapping matches (keep highest confidence)
        matches = self._remove_overlaps(matches)

        logger.info(f"Detected {len(matches)} PII instances")

        return matches

    async def detect_pii_in_dict(
        self,
        data: Dict[str, Any]
    ) -> List[PIIMatch]:
        """
        Detect PII in dictionary values

        Args:
            data: Dictionary to scan

        Returns:
            List of PII matches
        """
        matches = []

        for key, value in data.items():
            if isinstance(value, str):
                # Check key name
                key_matches = self._check_key_name(key)
                matches.extend(key_matches)

                # Check value
                value_matches = await self.detect_pii(value)
                matches.extend(value_matches)

        return matches

    async def redact_pii(
        self,
        text: str,
        replacement: str = "[REDACTED]"
    ) -> str:
        """
        Redact PII from text

        Args:
            text: Text to redact
            replacement: Replacement text

        Returns:
            Redacted text
        """
        matches = await self.detect_pii(text, include_context=False)

        # Sort by position (reverse order to maintain positions)
        matches.sort(key=lambda m: m.start_pos, reverse=True)

        redacted = text
        for match in matches:
            redacted = redacted[:match.start_pos] + replacement + redacted[match.end_pos:]

        return redacted

    async def redact_pii_in_dict(
        self,
        data: Dict[str, Any],
        replacement: str = "[REDACTED]"
    ) -> Dict[str, Any]:
        """
        Redact PII in dictionary

        Args:
            data: Dictionary to redact
            replacement: Replacement text

        Returns:
            Redacted dictionary
        """
        redacted = data.copy()

        for key, value in data.items():
            if isinstance(value, str):
                # Check if key indicates PII
                key_matches = self._check_key_name(key)
                if key_matches:
                    redacted[key] = replacement
                else:
                    # Redact PII in value
                    redacted[key] = await self.redact_pii(value, replacement)

        return redacted

    def _check_key_name(self, key: str) -> List[PIIMatch]:
        """
        Check if key name indicates PII

        Args:
            key: Dictionary key

        Returns:
            List of PII matches
        """
        matches = []
        key_lower = key.lower()

        pii_keywords = {
            PIIType.SSN: ["ssn", "social_security", "social security number"],
            PIIType.CREDIT_CARD: ["credit_card", "card_number", "cc_number", "creditcard"],
            PIIType.EMAIL: ["email", "e_mail", "email_address"],
            PIIType.PHONE: ["phone", "telephone", "mobile", "cell"],
            PIIType.DATE_OF_BIRTH: ["dob", "date_of_birth", "birthday", "birth_date"],
            PIIType.MEDICAL_RECORD: ["mrn", "medical_record", "patient_id"],
            PIIType.BANK_ACCOUNT: ["bank_account", "account_number", "routing_number"],
        }

        for pii_type, keywords in pii_keywords.items():
            for keyword in keywords:
                if keyword in key_lower:
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        value=key,
                        confidence=0.9,
                        start_pos=0,
                        end_pos=len(key),
                        context="",
                        metadata={"detected_from": "key_name"}
                    ))
                    break

        return matches

    def _get_context(self, text: str, start: int, end: int) -> str:
        """
        Get context around match

        Args:
            text: Full text
            start: Match start position
            end: Match end position

        Returns:
            Context string
        """
        context_start = max(0, start - self.context_window)
        context_end = min(len(text), end + self.context_window)

        return text[context_start:context_end]

    def _calculate_confidence(self, pii_type: PIIType, value: str) -> float:
        """
        Calculate confidence score for PII match

        Args:
            pii_type: Type of PII
            value: Matched value

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence by type
        base_confidence = {
            PIIType.SSN: 0.95,
            PIIType.CREDIT_CARD: 0.95,
            PIIType.EMAIL: 0.90,
            PIIType.PHONE: 0.85,
            PIIType.IP_ADDRESS: 0.95,
            PIIType.PASSPORT: 0.80,
            PIIType.DRIVER_LICENSE: 0.75,
            PIIType.DATE_OF_BIRTH: 0.80,
            PIIType.MEDICAL_RECORD: 0.70,
            PIIType.BANK_ACCOUNT: 0.85,
        }

        confidence = base_confidence.get(pii_type, 0.70)

        # Validate format
        if pii_type == PIIType.CREDIT_CARD:
            # Luhn algorithm check
            if not self._luhn_check(value):
                confidence *= 0.5

        return confidence

    def _luhn_check(self, card_number: str) -> bool:
        """
        Luhn algorithm for credit card validation

        Args:
            card_number: Credit card number

        Returns:
            True if valid
        """
        # Remove non-digit characters
        digits = [int(d) for d in card_number if d.isdigit()]

        if len(digits) < 13 or len(digits) > 19:
            return False

        # Luhn algorithm
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """
        Remove overlapping matches, keep highest confidence

        Args:
            matches: List of PII matches

        Returns:
            Deduplicated matches
        """
        if not matches:
            return []

        # Sort by start position
        matches.sort(key=lambda m: m.start_pos)

        deduplicated = []
        for match in matches:
            # Check if overlaps with previous match
            overlaps = False
            for existing in deduplicated:
                if (match.start_pos < existing.end_pos and
                    match.end_pos > existing.start_pos):
                    # Keep higher confidence
                    if match.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(match)
                    overlaps = True
                    break

            if not overlaps:
                deduplicated.append(match)

        return deduplicated

    def _load_pii_patterns(self) -> Dict[PIIType, List]:
        """
        Load PII detection patterns

        Returns:
            Dictionary of PII patterns
        """
        return {
            PIIType.SSN: [
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                re.compile(r'\b\d{9}\b'),
            ],
            PIIType.CREDIT_CARD: [
                re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
                re.compile(r'\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b'),  # Amex
            ],
            PIIType.EMAIL: [
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            ],
            PIIType.PHONE: [
                re.compile(r'\b\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b'),
                re.compile(r'\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b'),
                re.compile(r'\b\d{10,13}\b'),
            ],
            PIIType.IP_ADDRESS: [
                re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
            ],
            PIIType.PASSPORT: [
                re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
            ],
            PIIType.DRIVER_LICENSE: [
                re.compile(r'\b[A-Z]\d{7,12}\b'),
            ],
            PIIType.DATE_OF_BIRTH: [
                re.compile(r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b'),
                re.compile(r'\b(?:DOB|Date of Birth|Birthday)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b', re.IGNORECASE),
            ],
            PIIType.MEDICAL_RECORD: [
                re.compile(r'\b(?:MRN|Medical Record|Patient ID)[:\s]+(\w+)\b', re.IGNORECASE),
                re.compile(r'\b(?:Patient|MRN)[#:\s]+(\w+)\b', re.IGNORECASE),
            ],
            PIIType.BANK_ACCOUNT: [
                re.compile(r'\b\d{10,12}\b'),  # Account number
                re.compile(r'\b[0-9]{9}\b'),  # Routing number
            ],
        }

    async def scan_text_file(
        self,
        file_path: str
    ) -> List[PIIMatch]:
        """
        Scan text file for PII

        Args:
            file_path: Path to text file

        Returns:
            List of PII matches
        """
        with open(file_path, "r") as f:
            text = f.read()

        return await self.detect_pii(text)

    async def get_pii_summary(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Get PII detection summary

        Args:
            text: Text to analyze

        Returns:
            Summary statistics
        """
        matches = await self.detect_pii(text)

        summary = {
            "total_pii_instances": len(matches),
            "by_type": {},
            "confidence_distribution": {
                "high": 0,  # >= 0.9
                "medium": 0,  # 0.7-0.9
                "low": 0  # < 0.7
            }
        }

        for match in matches:
            # Count by type
            pii_type = match.pii_type.value
            summary["by_type"][pii_type] = summary["by_type"].get(pii_type, 0) + 1

            # Count by confidence
            if match.confidence >= 0.9:
                summary["confidence_distribution"]["high"] += 1
            elif match.confidence >= 0.7:
                summary["confidence_distribution"]["medium"] += 1
            else:
                summary["confidence_distribution"]["low"] += 1

        return summary