"""
Unit tests for RBAC Manager, Policy Engine, and Audit Logger
"""

import pytest
from src.access_control.rbac_manager import RBACManager
from src.access_control.policy_engine import PolicyEngine
from src.access_control.audit_logger import AuditLogger

def test_rbac_user_registration_and_permissions():
    rbac = RBACManager()
    rbac.register_user("u100", "analyst_alice", roles={"DATA_ANALYST"})
    
    assert rbac.check_permission("u100", "read") is True
    assert rbac.check_permission("u100", "read_masked_pii") is True
    assert rbac.check_permission("u100", "read_unmasked_pii") is False
    assert rbac.check_permission("u100", "delete") is False

def test_rbac_admin_permissions():
    rbac = RBACManager()
    rbac.register_user("u999", "admin_bob", roles={"DATA_ADMIN"})
    
    assert rbac.check_permission("u999", "read_unmasked_pii") is True
    assert rbac.check_permission("u999", "delete") is True
    assert rbac.check_permission("u999", "manage_policy") is True

def test_policy_engine_data_masking():
    rbac = RBACManager()
    rbac.register_user("u_analyst", "analyst", roles={"DATA_ANALYST"})
    rbac.register_user("u_admin", "admin", roles={"DATA_ADMIN"})
    
    engine = PolicyEngine(rbac)
    raw_email = "john.doe@company.com"
    raw_ssn = "123-45-6789"
    
    # Analyst sees masked values
    analyst_email_res = engine.evaluate_field_access("u_analyst", raw_email, pii_type="EMAIL", sensitivity_level="RESTRICTED")
    assert analyst_email_res["decision"] == "MASK"
    assert analyst_email_res["value"] != raw_email
    assert "j***@company.com" in analyst_email_res["value"] or "a***@domain.com" in analyst_email_res["value"]
    
    # Admin sees unmasked raw values
    admin_email_res = engine.evaluate_field_access("u_admin", raw_email, pii_type="EMAIL", sensitivity_level="RESTRICTED")
    assert admin_email_res["decision"] == "ALLOW"
    assert admin_email_res["value"] == raw_email

def test_policy_engine_masking_strategies():
    assert PolicyEngine.mask_value("secret", "GENERAL", "REDACT") == "[REDACTED]"
    assert PolicyEngine.mask_value("john.doe@domain.com", "EMAIL", "PARTIAL_EMAIL") == "j***@domain.com"
    assert PolicyEngine.mask_value("123-45-6789", "SSN", "PARTIAL_SSN") == "XXX-XX-6789"
    assert len(PolicyEngine.mask_value("password123", "GENERAL", "HASH")) == 16

def test_audit_logger():
    logger_inst = AuditLogger()
    logger_inst.log_access("u100", "READ", "customer_table", "ALLOW")
    logger_inst.log_access("u100", "READ_UNMASKED", "ssn_col", "DENY", {"reason": "Insufficient permissions"})
    
    assert logger_inst.total_events_count() == 2
    unauth = logger_inst.get_unauthorized_attempts()
    assert len(unauth) == 1
    assert unauth[0].asset_id == "ssn_col"
