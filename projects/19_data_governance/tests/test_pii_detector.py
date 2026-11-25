"""
Unit tests for PII Detector & Classification
"""

import pytest
from src.classification.pii_detector import PIIDetector, PIIMatch
from src.classification.data_classifier import DataClassifier, ClassificationResult
from src.classification.sensitivity_tagger import SensitivityTagger

def test_pii_detector_email_regex():
    detector = PIIDetector(confidence_threshold=0.5)
    emails = ["john.doe@example.com", "alice.smith@corporate.org", "user@domain.io"]
    match = detector.detect_column_pii("user_email", emails)
    
    assert match is not None
    assert match.pii_type == "EMAIL"
    assert match.confidence_score >= 0.8
    assert match.sensitivity_level == "HIGH"

def test_pii_detector_ssn_regex():
    detector = PIIDetector(confidence_threshold=0.5)
    ssns = ["123-45-6789", "987-65-4321", "456-78-1234"]
    match = detector.detect_column_pii("ssn", ssns)
    
    assert match is not None
    assert match.pii_type == "SSN"
    assert match.sensitivity_level == "CRITICAL"

def test_pii_detector_column_heuristic_fallback():
    detector = PIIDetector()
    match = detector.detect_column_pii("user_phone", [])
    
    assert match is not None
    assert match.pii_type == "PHONE"
    assert match.detection_method == "COLUMN_HEURISTIC"

def test_shannon_entropy_calculation():
    low_entropy = PIIDetector.calculate_shannon_entropy("AAAAAA")
    high_entropy = PIIDetector.calculate_shannon_entropy("a8F!z9#Pq1$")
    
    assert low_entropy == 0.0
    assert high_entropy > low_entropy

def test_data_classifier_dataset_level():
    classifier = DataClassifier()
    dataset_data = {
        "customer_id": ["CUST_001", "CUST_002"],
        "full_name": ["John Doe", "Jane Smith"],
        "email": ["john@example.com", "jane@example.com"],
        "account_balance": [1000.0, 2500.0],
    }
    
    res = classifier.classify_dataset("raw_customers", dataset_data)
    assert isinstance(res, ClassificationResult)
    assert res.overall_sensitivity in ("CONFIDENTIAL", "RESTRICTED")
    assert res.pii_column_count >= 1

def test_sensitivity_tagger():
    classifier = DataClassifier()
    tagger = SensitivityTagger()
    dataset_data = {
        "email": ["john@example.com"],
        "ssn": ["123-45-6789"],
    }
    res = classifier.classify_dataset("sensitive_table", dataset_data)
    tag_results = tagger.tag_classification_result("asset_100", res)
    
    assert len(tag_results) > 0
    asset_tag = tag_results[0]
    assert asset_tag.target_identifier == "asset_100"
    assert asset_tag.sensitivity_level in ("RESTRICTED", "CONFIDENTIAL")
