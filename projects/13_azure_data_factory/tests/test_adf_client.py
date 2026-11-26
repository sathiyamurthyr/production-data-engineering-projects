"""
test_adf_client.py - Unit tests for ADFClient and ADFConfig
============================================================
Comprehensive test suite testing authentication, configuration, lifecycle management, and mock mode fallback.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from src.adf_client import ADFClient, ADFConfig


def test_adf_config_from_environment(monkeypatch):
    """Test creating ADFConfig from environment variables."""
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-subscription-id")
    monkeypatch.setenv("ADF_RESOURCE_GROUP", "test-rg")
    monkeypatch.setenv("ADF_FACTORY_NAME", "test-adf")
    monkeypatch.setenv("MOCK_ADF", "false")

    config = ADFConfig.from_environment()

    assert config.tenant_id == "test-tenant-id"
    assert config.client_id == "test-client-id"
    assert config.client_secret == "test-client-secret"
    assert config.subscription_id == "test-subscription-id"
    assert config.resource_group == "test-rg"
    assert config.factory_name == "test-adf"
    assert not config.mock_mode


def test_adf_config_mock_mode_fallback(monkeypatch):
    """Test automatic fallback to mock mode when env vars are missing."""
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("MOCK_ADF", raising=False)

    config = ADFConfig.from_environment()
    assert config.mock_mode is True


def test_adf_client_mock_mode():
    """Test ADFClient methods in mock mode."""
    config = ADFConfig(
        tenant_id="mock",
        client_id="mock",
        client_secret="mock",
        subscription_id="00000000-0000-0000-0000-000000000000",
        resource_group="rg-test",
        factory_name="adf-test",
        mock_mode=True,
    )
    client = ADFClient(config)

    # Management client
    mgmt = client.get_management_client()
    assert mgmt is not None

    # Resource client
    res = client.get_resource_client()
    assert res is not None

    # Create factory
    factory = client.create_data_factory(
        resource_group="rg-test",
        factory_name="adf-test",
        location="eastus",
        tags={"env": "test"},
    )
    assert factory["name"] == "adf-test"
    assert factory["provisioning_state"] == "Succeeded"

    # Get factory
    got_factory = client.get_data_factory("rg-test", "adf-test")
    assert got_factory["name"] == "adf-test"

    # List factories
    factories = client.list_data_factories("rg-test")
    assert len(factories) > 0
    assert factories[0]["name"] == "adf-test"

    # Git info
    git_info = client.get_factory_git_info("rg-test", "adf-test")
    assert git_info["git_configured"] is True

    # Delete factory (no error raised)
    client.delete_data_factory("rg-test", "adf-test")


def test_adf_client_default_credential():
    """Test creating ADFClient via DefaultAzureCredential."""
    client = ADFClient.from_default_credential(
        subscription_id="sub-12345",
        resource_group="rg-dev",
        factory_name="adf-dev",
    )
    assert client.config.use_default_cred is True
    assert client.config.subscription_id == "sub-12345"
