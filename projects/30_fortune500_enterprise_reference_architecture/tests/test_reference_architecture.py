"""
Tests for Fortune 500 Enterprise Reference Architecture

This test suite validates:
- Enterprise architecture completeness
- Project integration
- Architecture artifacts
"""

import pytest
import os
import sys

# Add reference implementations to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference-implementations"))

from enterprise_validator import EnterpriseValidator, PROJECTS_01_29, ArtifactStatus


class TestEnterpriseValidator:
    """Tests for enterprise architecture validator"""

    def setup_method(self):
        base_path = os.path.join(os.path.dirname(__file__), "..")
        self.validator = EnterpriseValidator(base_path)

    def test_validate_artifacts(self):
        """Test artifact validation"""
        summary = self.validator.validate()
        assert summary["total_artifacts"] == len(EnterpriseValidator.REQUIRED_ARTIFACTS)
        assert summary["complete"] >= summary["critical_complete"]

    def test_critical_artifacts_complete(self):
        """Test critical artifacts are complete"""
        summary = self.validator.validate()
        assert summary["critical_ready"] is True

    def test_project_integration(self):
        """Test integration with prior projects"""
        result = self.validator.validate_project_integration(PROJECTS_01_29)
        assert result["total_projects"] >= 10
        assert result["ready_projects"] >= 10

    def test_required_files(self):
        """Test required files exist"""
        base_path = os.path.join(os.path.dirname(__file__), "..")
        
        required_files = [
            "README.md",
            "executive-summary.md",
            "architecture.md",
            "governance.md",
            "security.md",
            "operations.md",
            "deployment-guide.md",
            "disaster-recovery.md",
            "requirements.txt",
        ]
        
        for file_name in required_files:
            path = os.path.join(base_path, file_name)
            assert os.path.exists(path), f"Missing required file: {file_name}"