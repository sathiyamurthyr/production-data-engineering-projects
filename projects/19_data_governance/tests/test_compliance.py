"""
Unit tests for GDPR Compliance, Retention Manager, and OpenMetadata Client
"""

import pytest
from src.catalog.data_catalog import DataCatalog, CatalogEntry
from src.access_control.audit_logger import AuditLogger
from src.compliance.gdpr_compliance import GDPRComplianceChecker
from src.compliance.data_retention import DataRetentionManager
from src.compliance.compliance_reporter import ComplianceReporter
from src.openmetadata.om_client import OpenMetadataClient

def test_gdpr_subject_access_request():
    catalog = DataCatalog()
    checker = GDPRComplianceChecker(catalog)
    
    datasets = {
        "raw_customers": [
            {"customer_id": "CUST_1001", "name": "John Doe", "email": "john@example.com"},
            {"customer_id": "CUST_1002", "name": "Jane Smith", "email": "jane@example.com"},
        ],
        "orders": [
            {"order_id": "ORD_01", "customer_id": "CUST_1001", "amount": 150.0},
        ],
    }
    
    sar_res = checker.process_subject_access_request("CUST_1001", datasets)
    assert sar_res.subject_id == "CUST_1001"
    assert sar_res.total_records_found == 2
    assert "raw_customers" in sar_res.retrieved_records
    assert "orders" in sar_res.retrieved_records

def test_gdpr_right_to_be_forgotten_deletion():
    catalog = DataCatalog()
    checker = GDPRComplianceChecker(catalog)
    
    datasets = {
        "raw_customers": [
            {"customer_id": "CUST_1001", "name": "John Doe"},
            {"customer_id": "CUST_1002", "name": "Jane Smith"},
        ]
    }
    
    rtbf_res = checker.process_right_to_be_forgotten("CUST_1001", datasets)
    assert rtbf_res.records_erased_count == 1
    assert len(datasets["raw_customers"]) == 1
    assert datasets["raw_customers"][0]["customer_id"] == "CUST_1002"

def test_gdpr_right_to_be_forgotten_anonymization():
    catalog = DataCatalog()
    checker = GDPRComplianceChecker(catalog)
    
    datasets = {
        "raw_customers": [
            {"customer_id": "CUST_1001", "name": "John Doe", "email": "john@example.com"},
        ]
    }
    
    rtbf_res = checker.process_right_to_be_forgotten("CUST_1001", datasets, anonymize_fields=["name", "email"])
    assert rtbf_res.records_anonymized_count == 1
    assert datasets["raw_customers"][0]["name"] == "[ANONYMIZED]"
    assert datasets["raw_customers"][0]["email"] == "[ANONYMIZED]"

def test_data_retention_evaluation():
    ret_mgr = DataRetentionManager()
    
    # Evaluate 10-year old marketing dataset (retention limit is 365 days -> action PURGE)
    action = ret_mgr.evaluate_asset_age("old_mktg", "2013-01-01T00:00:00Z", "marketing")
    assert action.action_required == "PURGE"
    
    # Evaluate recent customer dataset (limit 1825 days) -> action NONE
    action_recent = ret_mgr.evaluate_asset_age("new_cust", "2026-01-01T00:00:00Z", "customer_360")
    assert action_recent.action_required == "NONE"

def test_compliance_reporter_summary():
    catalog = DataCatalog()
    catalog.register_asset(CatalogEntry("a1", "raw_cust", "customer_360", "owner@co.com", "table", "RESTRICTED", "s3://path"))
    
    audit_logger = AuditLogger()
    audit_logger.log_access("u1", "READ", "a1", "DENY")
    
    ret_mgr = DataRetentionManager()
    reporter = ComplianceReporter(catalog, audit_logger, ret_mgr)
    
    summary = reporter.generate_summary_report()
    assert summary.total_assets == 1
    assert summary.pii_asset_count == 1
    assert summary.unauthorized_attempt_count == 1
    assert summary.compliance_score <= 100.0

def test_openmetadata_client_simulation():
    om_client = OpenMetadataClient(simulation_mode=True)
    assert om_client.health_check() is True
    
    entry = CatalogEntry("a10", "users_table", "finance", "fin@co.com", "table", "CONFIDENTIAL", "s3://fin")
    res = om_client.publish_table_entity(entry)
    assert res["name"] == "users_table"
    assert "a10" in om_client.get_published_entities()
