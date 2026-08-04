"""
Enterprise Data Classification Service
Automatic data classification and sensitive data discovery
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ClassificationLevel(str, Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"
    PHI = "phi"
    PCI = "pci"


@dataclass
class DataClassification:
    """Data classification result"""
    resource_id: str
    resource_type: str
    classification: ClassificationLevel
    confidence_score: float
    detected_patterns: List[str]
    sensitive_fields: List[str]
    classified_at: datetime
    classified_by: str
    metadata: Dict[str, Any]


class DataClassifier:
    """
    Enterprise data classification service
    Automatically discovers and classifies sensitive data
    """

    def __init__(self):
        self.classifications: Dict[str, DataClassification] = {}
        self.patterns = self._load_patterns()

    async def classify_resource(
        self,
        resource_id: str,
        resource_type: str,
        data_sample: Any,
        classified_by: str = "system"
    ) -> DataClassification:
        """
        Classify resource based on data sample

        Args:
            resource_id: Resource identifier
            resource_type: Type of resource
            data_sample: Sample data to analyze
            classified_by: Who/what performed classification

        Returns:
            Data classification result
        """
        # Detect sensitive patterns
        detected_patterns = self._detect_patterns(data_sample)

        # Determine classification level
        classification, confidence = self._determine_classification(detected_patterns)

        # Identify sensitive fields
        sensitive_fields = self._identify_sensitive_fields(data_sample, detected_patterns)

        result = DataClassification(
            resource_id=resource_id,
            resource_type=resource_type,
            classification=classification,
            confidence_score=confidence,
            detected_patterns=detected_patterns,
            sensitive_fields=sensitive_fields,
            classified_at=datetime.utcnow(),
            classified_by=classified_by,
            metadata={}
        )

        self.classifications[resource_id] = result
        logger.info(f"Resource classified: {resource_id} -> {classification}")

        return result

    async def classify_database_table(
        self,
        table_name: str,
        columns: List[Dict[str, Any]]
    ) -> DataClassification:
        """
        Classify database table based on columns

        Args:
            table_name: Table name
            columns: List of column definitions

        Returns:
            Data classification
        """
        detected_patterns = []
        sensitive_fields = []

        for column in columns:
            column_name = column.get("name", "").lower()
            data_type = column.get("type", "").lower()

            # Check column name patterns
            patterns = self._check_column_patterns(column_name)
            detected_patterns.extend(patterns)

            if patterns:
                sensitive_fields.append(column_name)

        # Determine classification
        classification, confidence = self._determine_classification(detected_patterns)

        result = DataClassification(
            resource_id=table_name,
            resource_type="database_table",
            classification=classification,
            confidence_score=confidence,
            detected_patterns=list(set(detected_patterns)),
            sensitive_fields=sensitive_fields,
            classified_at=datetime.utcnow(),
            classified_by="system",
            metadata={"column_count": len(columns)}
        )

        self.classifications[table_name] = result
        logger.info(f"Table classified: {table_name} -> {classification}")

        return result

    async def get_classification(
        self,
        resource_id: str
    ) -> Optional[DataClassification]:
        """
        Get classification for resource

        Args:
            resource_id: Resource identifier

        Returns:
            Classification result or None
        """
        return self.classifications.get(resource_id)

    async def update_classification(
        self,
        resource_id: str,
        classification: ClassificationLevel,
        updated_by: str
    ) -> DataClassification:
        """
        Manually update classification

        Args:
            resource_id: Resource identifier
            classification: New classification level
            updated_by: Who updated

        Returns:
            Updated classification
        """
        if resource_id not in self.classifications:
            raise ValueError("Resource not found")

        self.classifications[resource_id].classification = classification
        self.classifications[resource_id].classified_by = updated_by
        self.classifications[resource_id].classified_at = datetime.utcnow()

        logger.info(f"Classification updated: {resource_id} -> {classification}")

        return self.classifications[resource_id]

    def _detect_patterns(self, data_sample: Any) -> List[str]:
        """
        Detect sensitive data patterns

        Args:
            data_sample: Data to analyze

        Returns:
            List of detected patterns
        """
        detected = []

        # Convert to string for pattern matching
        if not isinstance(data_sample, str):
            data_str = str(data_sample)
        else:
            data_str = data_sample

        # Check each pattern category
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(data_str):
                    detected.append(category)
                    break

        return detected

    def _check_column_patterns(self, column_name: str) -> List[str]:
        """
        Check column name for sensitive patterns

        Args:
            column_name: Column name to check

        Returns:
            List of matched pattern categories
        """
        matched = []

        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(column_name):
                    matched.append(category)
                    break

        return matched

    def _determine_classification(
        self,
        detected_patterns: List[str]
    ) -> tuple[ClassificationLevel, float]:
        """
        Determine classification level from patterns

        Args:
            detected_patterns: List of detected patterns

        Returns:
            Tuple of (classification, confidence_score)
        """
        if not detected_patterns:
            return ClassificationLevel.PUBLIC, 1.0

        # Priority order
        if "pci" in detected_patterns:
            return ClassificationLevel.PCI, 0.95
        elif "phi" in detected_patterns:
            return ClassificationLevel.PHI, 0.95
        elif "pii" in detected_patterns:
            return ClassificationLevel.PII, 0.90
        elif "sensitive" in detected_patterns:
            return ClassificationLevel.CONFIDENTIAL, 0.85
        elif "internal" in detected_patterns:
            return ClassificationLevel.INTERNAL, 0.80

        return ClassificationLevel.PUBLIC, 0.70

    def _identify_sensitive_fields(
        self,
        data_sample: Any,
        detected_patterns: List[str]
    ) -> List[str]:
        """
        Identify sensitive fields in data

        Args:
            data_sample: Data sample
            detected_patterns: Detected patterns

        Returns:
            List of sensitive field names
        """
        sensitive_fields = []

        if isinstance(data_sample, dict):
            for field_name, value in data_sample.items():
                field_lower = field_name.lower()
                for category in detected_patterns:
                    patterns = self.patterns.get(category, [])
                    for pattern in patterns:
                        if pattern.search(field_lower):
                            sensitive_fields.append(field_name)
                            break

        return sensitive_fields

    def _load_patterns(self) -> Dict[str, List]:
        """
        Load pattern definitions for sensitive data

        Returns:
            Dictionary of pattern categories
        """
        import re

        return {
            "pii": [
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN
                re.compile(r'\b\d{9,11}\b'),  # SSN without dashes
                re.compile(r'\b[A-Z]{2}\d{6,9}\b'),  # Passport number
                re.compile(r'\b\d{10,13}\b'),  # Phone number
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
                re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),  # IP address
            ],
            "phi": [
                re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN (also PHI)
                re.compile(r'\b\d{10,13}\b'),  # Phone number
                re.compile(r'\b(?:DOB|Date of Birth|Birthday)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b', re.IGNORECASE),
                re.compile(r'\b(?:Patient|MRN|Medical Record)[:\s]+(\w+)\b', re.IGNORECASE),
            ],
            "pci": [
                re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),  # Credit card
                re.compile(r'\b\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3}\b'),  # Amex
                re.compile(r'\b(?:CVV|CVC|Security Code)[:\s]+(\d{3,4})\b', re.IGNORECASE),
            ],
            "sensitive": [
                re.compile(r'\b(?:password|secret|token|api_key|api_key|private_key)\b', re.IGNORECASE),
                re.compile(r'\b(?:confidential|classified|secret|restricted)\b', re.IGNORECASE),
            ],
            "internal": [
                re.compile(r'\b(?:internal|proprietary|trade.secret)\b', re.IGNORECASE),
                re.compile(r'\b(?:employee|staff|personnel)\b', re.IGNORECASE),
            ],
        }

    async def scan_database(
        self,
        connection_string: str,
        tables: List[str]
    ) -> List[DataClassification]:
        """
        Scan database tables for sensitive data

        Args:
            connection_string: Database connection
            tables: List of tables to scan

        Returns:
            List of classifications
        """
        classifications = []

        for table in tables:
            # In production, query actual table metadata
            # Simplified example
            classification = await self.classify_database_table(
                table,
                []  # Column definitions
            )
            classifications.append(classification)

        return classifications

    async def get_classification_report(self) -> Dict[str, Any]:
        """
        Get classification summary report

        Returns:
            Classification report
        """
        report = {
            "total_classified": len(self.classifications),
            "by_level": {},
            "by_type": {},
            "high_confidence": 0
        }

        for classification in self.classifications.values():
            # Count by level
            level = classification.classification.value
            report["by_level"][level] = report["by_level"].get(level, 0) + 1

            # Count by type
            resource_type = classification.resource_type
            report["by_type"][resource_type] = report["by_type"].get(resource_type, 0) + 1

            # Count high confidence
            if classification.confidence_score >= 0.9:
                report["high_confidence"] += 1

        return report