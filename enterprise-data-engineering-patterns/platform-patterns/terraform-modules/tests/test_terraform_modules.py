"""Unit tests for the Terraform Modules pattern."""

import pytest

from src.terraform_modules import TerraformModules, TerraformModulesConfig


class TestTerraformModulesConfig:
    """Tests for TerraformModulesConfig."""

    def test_default_config(self) -> None:
        config = TerraformModulesConfig()
        assert config.pattern_name == "terraform-modules"


class TestTerraformModules:
    """Tests for TerraformModules."""

    def test_init_default_config(self) -> None:
        pattern = TerraformModules()
        assert pattern.config.pattern_name == "terraform-modules"

    def test_init_custom_config(self) -> None:
        config = TerraformModulesConfig()
        pattern = TerraformModules(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TerraformModules()
        result = pattern.execute("test_data")
        assert result == "test_data"
