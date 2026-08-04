"""Tests for reliability components."""

import pytest
from datetime import datetime, timedelta

from reliability.slo import (
    SLOManager,
    SLI,
    SLO,
    SLOCompliance,
    ReliabilityEngineer,
)


class TestSLOManager:
    """Test SLO manager."""
    
    def test_define_slo(self):
        """Test defining SLO."""
        manager = SLOManager()
        
        slo = manager.define_slo(
            slo_id="test-slo",
            name="Test SLO",
            description="Test description",
            metric_query="avg(up) * 100",
            target=99.9,
            window_days=30,
        )
        
        assert slo.slo_id == "test-slo"
        assert slo.target == 99.9
        assert slo.window_days == 30
        assert "test-slo" in manager.slos
    
    def test_check_compliance_compliant(self):
        """Test SLO compliance when compliant."""
        manager = SLOManager()
        
        manager.define_slo(
            "test-slo",
            "Test SLO",
            "Test",
            "up",
            target=99.0,
            window_days=30,
        )
        
        compliance = manager.check_compliance("test-slo", 99.5)
        
        assert compliance.compliant is True
        assert compliance.current_value == 99.5
        assert compliance.target == 99.0
    
    def test_check_compliance_non_compliant(self):
        """Test SLO compliance when not compliant."""
        manager = SLOManager()
        
        manager.define_slo(
            "test-slo",
            "Test SLO",
            "Test",
            "up",
            target=99.0,
            window_days=30,
        )
        
        compliance = manager.check_compliance("test-slo", 98.5)
        
        assert compliance.compliant is False
        assert compliance.error_budget_remaining < 100
    
    def test_check_compliance_undefined_slo(self):
        """Test checking compliance for undefined SLO."""
        manager = SLOManager()
        
        with pytest.raises(ValueError):
            manager.check_compliance("undefined", 99.0)
    
    def test_get_error_budget_status(self):
        """Test getting error budget status."""
        manager = SLOManager()
        
        manager.define_slo("test", "Test", "Test", "up", target=99.9, window_days=30)
        manager.check_compliance("test", 99.5)
        
        status = manager.get_error_budget_status("test")
        
        assert "total_budget" in status
        assert "remaining_budget" in status
        assert "status" in status
    
    def test_get_error_budget_status_undefined(self):
        """Test getting error budget for undefined SLO."""
        manager = SLOManager()
        
        status = manager.get_error_budget_status("undefined")
        
        assert status == {}
    
    def test_get_slo_summary(self):
        """Test getting SLO summary."""
        manager = SLOManager()
        
        manager.define_slo("slo1", "SLO 1", "Test", "up", target=99.9, window_days=30)
        manager.define_slo("slo2", "SLO 2", "Test", "up", target=99.5, window_days=30)
        
        summary = manager.get_slo_summary()
        
        assert summary["total_slos"] == 2
        assert len(summary["slos"]) == 2


class TestReliabilityEngineer:
    """Test reliability engineer."""
    
    def test_register_remediation(self):
        """Test registering remediation action."""
        manager = SLOManager()
        engineer = ReliabilityEngineer(manager)
        
        manager.define_slo("test", "Test", "Test", "up", target=99.0, window_days=30)
        
        def test_action(compliance):
            return {"action": "scale_up", "reason": "High error budget burn"}
        
        engineer.register_remediation("test", "error_budget_critical", test_action)
        
        assert "test" in engineer.remediation_actions
        assert len(engineer.remediation_actions["test"]) == 1
    
    def test_evaluate_and_remediate_compliant(self):
        """Test evaluation when SLO is compliant."""
        manager = SLOManager()
        engineer = ReliabilityEngineer(manager)
        
        manager.define_slo("test", "Test", "Test", "up", target=99.0, window_days=30)
        
        result = engineer.evaluate_and_remediate("test", 99.5)
        
        assert result["action_required"] is False
        assert result["compliance"]["compliant"] is True
    
    def test_evaluate_and_remediate_non_compliant(self):
        """Test evaluation when SLO is not compliant."""
        manager = SLOManager()
        engineer = ReliabilityEngineer(manager)
        
        manager.define_slo("test", "Test", "Test", "up", target=99.0, window_days=30)
        
        result = engineer.evaluate_and_remediate("test", 98.0)
        
        assert result["action_required"] is True
        assert result["compliance"]["compliant"] is False
    
    def test_evaluate_and_remediate_with_action(self):
        """Test evaluation with remediation action."""
        manager = SLOManager()
        engineer = ReliabilityEngineer(manager)
        
        manager.define_slo("test", "Test", "Test", "up", target=99.0, window_days=30)
        
        def test_action(compliance):
            return {"action": "scale_up"}
        
        engineer.register_remediation("test", "error_budget_critical", test_action)
        
        result = engineer.evaluate_and_remediate("test", 95.0)
        
        assert result["action_required"] is True
        assert result.get("action_executed") is True