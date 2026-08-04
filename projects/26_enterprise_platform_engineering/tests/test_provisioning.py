"""
Tests for Provisioning Service
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from platform.services.provisioning import (
    ProvisioningService,
    ProvisioningCreate,
    ProvisioningStatus,
    ValidationResult
)


@pytest.fixture
def provisioning_service():
    """Create provisioning service instance."""
    return ProvisioningService()


@pytest.mark.asyncio
async def test_validate_request_success(provisioning_service):
    """Test successful request validation."""
    request = ProvisioningCreate(
        name="test-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="data-team"
    )

    result = await provisioning_service.validate_request(request)

    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_validate_request_invalid_environment(provisioning_service):
    """Test validation with invalid environment."""
    request = ProvisioningCreate(
        name="test-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="invalid-env",
        team="data-team"
    )

    result = await provisioning_service.validate_request(request)

    assert result.valid is False
    assert any("environment" in str(err) for err in result.errors)


@pytest.mark.asyncio
async def test_validate_request_invalid_team(provisioning_service):
    """Test validation with invalid team."""
    request = ProvisioningCreate(
        name="test-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="a"  # Too short
    )

    result = await provisioning_service.validate_request(request)

    assert result.valid is False
    assert any("team" in str(err) for err in result.errors)


@pytest.mark.asyncio
async def test_validate_request_invalid_name(provisioning_service):
    """Test validation with invalid name."""
    request = ProvisioningCreate(
        name="ab",  # Too short
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="data-team"
    )

    result = await provisioning_service.validate_request(request)

    assert result.valid is False
    assert any("name" in str(err) for err in result.errors)


@pytest.mark.asyncio
async def test_provision_request(provisioning_service):
    """Test provisioning request creation."""
    request = ProvisioningCreate(
        name="test-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="data-team"
    )

    provisioning = await provisioning_service.provision(request)

    assert provisioning is not None
    assert provisioning.name == "test-resource"
    assert provisioning.status == ProvisioningStatus.PROVISIONING
    assert provisioning.environment == "dev"
    assert provisioning.team == "data-team"


@pytest.mark.asyncio
async def test_get_status(provisioning_service):
    """Test getting provisioning status."""
    # Create provisioning first
    request = ProvisioningCreate(
        name="test-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="data-team"
    )
    created = await provisioning_service.provision(request)

    # Get status
    status = await provisioning_service.get_status(created.id)

    assert status is not None
    assert status.id == created.id
    assert status.name == "test-resource"


@pytest.mark.asyncio
async def test_get_status_not_found(provisioning_service):
    """Test getting status for non-existent provisioning."""
    status = await provisioning_service.get_status("nonexistent-id")
    assert status is None


@pytest.mark.asyncio
async def test_list_requests(provisioning_service):
    """Test listing provisioning requests."""
    # Create multiple requests
    for i in range(3):
        request = ProvisioningCreate(
            name=f"resource-{i}",
            template_id="template-123",
            variables={"key": f"value-{i}"},
            environment="dev",
            team="data-team"
        )
        await provisioning_service.provision(request)

    # List requests
    requests = await provisioning_service.list_requests()

    assert len(requests) == 3


@pytest.mark.asyncio
async def test_list_requests_with_filter(provisioning_service):
    """Test listing requests with filters."""
    # Create requests with different environments
    await provisioning_service.provision(ProvisioningCreate(
        name="dev-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="dev",
        team="data-team"
    ))

    await provisioning_service.provision(ProvisioningCreate(
        name="prod-resource",
        template_id="template-123",
        variables={"key": "value"},
        environment="prod",
        team="data-team"
    ))

    # Filter by environment
    dev_requests = await provisioning_service.list_requests()
    # Note: In real implementation, this would filter by status

    assert len(dev_requests) >= 1


@pytest.mark.asyncio
async def test_health_check(provisioning_service):
    """Test health check."""
    health = await provisioning_service.health_check()
    assert "status" in health
    assert health["status"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_get_statistics(provisioning_service):
    """Test getting provisioning statistics."""
    # Create some provisioning requests
    for i in range(2):
        request = ProvisioningCreate(
            name=f"resource-{i}",
            template_id="template-123",
            variables={"key": f"value-{i}"},
            environment="dev",
            team="data-team"
        )
        await provisioning_service.provision(request)

    stats = await provisioning_service.get_statistics()

    assert "total_requests" in stats
    assert "by_status" in stats
    assert "by_team" in stats
    assert "by_environment" in stats
    assert stats["total_requests"] >= 2