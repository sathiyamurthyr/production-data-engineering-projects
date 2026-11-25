"""
PII Detector Module
===================
Scans column values and text assets using regex patterns and column heuristics
to identify Personally Identifiable Information (PII).
"""

import re
import yaml
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)

@dataclass
class PIIMatch:
    """Represents a detected PII match details."""
    pii_type: str
    confidence_score: float
    sensitivity_level: str
    detection_method: str = "REGEX"


class PIIDetector:
    """
    Scans raw column values or general text using pre-defined regular expressions
    to detect Personally Identifiable Information (PII).
    """
    def __init__(self, config_path: str = "configs/governance_config.yaml", confidence_threshold: float = 0.7):
        self.config_path = config_path
        self.patterns = []
        self.confidence_threshold = confidence_threshold
        self._load_config()

    def _load_config(self):
        """Loads regex patterns and detection thresholds from config file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                classification_conf = config.get("classification", {})
                
                # Update confidence threshold if not explicitly set in constructor
                if self.confidence_threshold == 0.7:  # default value
                    self.confidence_threshold = classification_conf.get("pii_detection", {}).get("confidence_threshold", 0.7)
                
                patterns_list = classification_conf.get("pii_detection", {}).get("patterns", [])
                for pat in patterns_list:
                    compiled = re.compile(pat["regex"])
                    self.patterns.append({
                        "name": pat["name"],
                        "regex": compiled,
                        "score": pat["score"],
                        "classification": pat["classification"]
                    })
            logger.info(f"Loaded {len(self.patterns)} PII detection patterns from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load governance config: {str(e)}. Using fallback basic patterns.")
            # Fallback basic configurations if file not found
            self.patterns = [
                {
                    "name": "EMAIL",
                    "regex": re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'),
                    "score": 0.95,
                    "classification": "PII_RESTRICTED"
                },
                {
                    "name": "PHONE",
                    "regex": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                    "score": 0.85,
                    "classification": "PII_CONFIDENTIAL"
                },
                {
                    "name": "SSN",
                    "regex": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                    "score": 1.0,
                    "classification": "PII_RESTRICTED"
                },
                {
                    "name": "CREDIT_CARD",
                    "regex": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                    "score": 0.95,
                    "classification": "PII_RESTRICTED"
                }
            ]

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """Computes the Shannon Entropy of a string to estimate randomness/information density."""
        if not text:
            return 0.0
        frequencies = {}
        for char in text:
            frequencies[char] = frequencies.get(char, 0) + 1
        entropy = 0.0
        total = len(text)
        for count in frequencies.values():
            p = count / total
            entropy -= p * math.log2(p)
        return entropy

    def scan_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans a single text string against all loaded patterns.
        
        Returns:
            List of matches with pattern name, matching text, confidence score, and classification.
        """
        matches = []
        if not text:
            return matches
            
        for pattern in self.patterns:
            finds = pattern["regex"].findall(text)
            if finds:
                matches.append({
                    "pattern_name": pattern["name"],
                    "match_count": len(finds),
                    "confidence_score": pattern["score"],
                    "classification": pattern["classification"]
                })
        return matches

    def scan_column(self, values: List[Any]) -> Tuple[str, float]:
        """
        Scans a list of values representing a column and determines if it contains PII.
        
        Args:
            values: List of string or string-convertible items.
            
        Returns:
            A tuple of (classification_label, confidence_score). 
            If no PII is detected, returns ('PUBLIC', 0.0).
        """
        match = self.detect_column_pii("unknown_col", values)
        if match:
            # Map PII type to classification labels used in schema updates
            sens = match.sensitivity_level
            label = "PUBLIC"
            if sens == "CRITICAL":
                label = "RESTRICTED"
            elif sens == "HIGH":
                label = "CONFIDENTIAL"
            return label, match.confidence_score
        return "PUBLIC", 0.0

    def detect_column_pii(self, column_name: str, values: List[Any]) -> Optional[PIIMatch]:
        """
        Analyzes a column's name and its values to determine if it is a PII column.
        Supports both empty lists (heuristic fallback) and populated lists (regex evaluation).
        """
        clean_col = column_name.lower().strip()
        
        # 1. Fallback heuristics for empty or small value lists
        if not values or len([v for v in values if v is not None and str(v).strip() != ""]) == 0:
            if "email" in clean_col:
                return PIIMatch("EMAIL", 0.8, "HIGH", "COLUMN_HEURISTIC")
            if "ssn" in clean_col or "social" in clean_col:
                return PIIMatch("SSN", 0.9, "CRITICAL", "COLUMN_HEURISTIC")
            if "phone" in clean_col or "mobile" in clean_col or "tele" in clean_col:
                return PIIMatch("PHONE", 0.8, "HIGH", "COLUMN_HEURISTIC")
            if "card" in clean_col or "credit" in clean_col or "cc" in clean_col:
                return PIIMatch("CREDIT_CARD", 0.8, "CRITICAL", "COLUMN_HEURISTIC")
            return None

        # 2. Extract non-empty sample values
        sample_values = [str(v).strip() for v in values if v is not None and str(v).strip() != ""][:100]
        if not sample_values:
            return None

        best_match: Optional[PIIMatch] = None
        
        # 3. Scan values against compiled regular expressions
        for pattern in self.patterns:
            matches_count = 0
            for val in sample_values:
                if pattern["regex"].search(val):
                    matches_count += 1
            
            if matches_count > 0:
                match_ratio = matches_count / len(sample_values)
                # Compute confidence as pattern score weighted by matching ratio
                conf_score = pattern["score"] * match_ratio
                
                if conf_score >= self.confidence_threshold:
                    # Map pattern classification to sensitivity levels (CRITICAL, HIGH, etc.)
                    cls_label = pattern["classification"]
                    sens_level = "HIGH"
                    if "RESTRICTED" in cls_label or pattern["name"] in ("SSN", "CREDIT_CARD"):
                        sens_level = "CRITICAL"
                    elif "CONFIDENTIAL" in cls_label:
                        sens_level = "HIGH"
                    
                    match = PIIMatch(
                        pii_type=pattern["name"],
                        confidence_score=conf_score,
                        sensitivity_level=sens_level,
                        detection_method="REGEX"
                    )
                    
                    if not best_match or conf_score > best_match.confidence_score:
                        best_match = match
                        
        return best_match
