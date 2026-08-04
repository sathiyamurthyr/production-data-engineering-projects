"""
Tests for Service Catalog Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from platform.services.service_catalog import ServiceCatalogService, ServiceCreate
from platform.models.responses import HealthResponse


@pytest.fixture
def service_catalog():
    """Create service catalog instance."""
    return ServiceCatalogService()


@pytest.mark.asyncio
async def test_list_services_empty(service_catalog):
    """Test listing services when empty."""
    services = await service_catalog.list_services()
    assert services == []


@pytest.mark.asyncio
async def test_create_service(service_catalog):
    """Test service creation."""
    service_create = ServiceCreate(
        name="test-service",
        category="data-platform",
        description="Test service",
        version="1.0.0",
        owner_team="data-team",
        tags=["test", "example"]
    )

    service = await service_catalog.create_service(service_create)

    assert service is not None
    assert service.name == "test-service"
    assert service.category == "data-platform"
    assert service.owner_team == "data-team"
    assert service.tags == ["test", "example"]


@pytest.mark.asyncio
async def test_get_service(service_catalog):
    """Test getting service by ID."""
    # Create service first
    service_create = ServiceCreate(
        name="test-service",
        category="data-platform",
        description="Test service",
        version="1.0.0",
        owner_team="data-team"
    )
    created_service = await service_catalog.create_service(service_create)

    # Get service
    service = await service_catalog.get_service(created_service.id)

    assert service is not None
    assert service.id == created_service.id
    assert service.name == "test-service"


@pytest.mark.asyncio
async def test_get_service_not_found(service_catalog):
    """Test getting non-existent service."""
    service = await service_catalog.get_service("nonexistent-id")
    assert service is None


@pytest.mark.asyncio
async def test_list_services_with_filter(service_catalog):
    """Test listing services with filters."""
    # Create multiple services
    await service_catalog.create_service(ServiceCreate(
        name="data-service",
        category="data-platform",
        description="Data service",
        version="1.0.0",
        owner_team="data-team"
    ))

    await service_catalog.create_service(ServiceCreate(
        name="ml-service",
        category="ai-platform",
        description="ML service",
        version="1.0.0",
        owner_team="ml-team"
    ))

    # Filter by category
    data_services = await service_catalog.list_services(category="data-platform")
    assert len(data_services) == 1
    assert data_services[0].name == "data-service"

    # Filter by team
    ml_services = await service_catalog.list_services(team="ml-team")
    assert len(ml_services) == 1
    assert ml_services[0].name == "ml-service"


@pytest.mark.asyncio
async def test_delete_service(service_catalog):
    """Test service deletion."""
    # Create service first
    service_create = ServiceCreate(
        name="test-service",
        category="data-platform",
        description="Test service",
        version="1.0.0",
        owner_team="data-team"
    )
    created_service = await service_catalog.create_service(service_create)

    # Delete service
    result = await service_catalog.delete_service(created_service.id)
    assert result is True

    # Verify deletion
    service = await service_catalog.get_service(created_service.id)
    assert service is None


@pytest.mark.asyncio
async def test_get_categories(service_catalog):
    """Test getting all categories."""
    # Create services with different categories
    await service_catalog.create_service(ServiceCreate(
        name="service1",
        category="data-platform",
        description="Service 1",
        version="1.0.0",
        owner_team="team1"
    ))

    await service_catalog.create_service(ServiceCreate(
        name="service2",
        category="ai-platform",
        description="Service 2",
        version="1.0.0",
        owner_team="team1"
    ))

    categories = await service_catalog.get_categories()
    assert len(categories) == 2
    assert "data-platform" in categories
    assert "ai-platform" in categories


@pytest.mark.asyncio
async def test_get_teams(service_catalog):
    """Test getting all teams."""
    # Create services with different teams
    await service_catalog.create_service(ServiceCreate(
        name="service1",
        category="data-platform",
        description="Service 1",
        version="1.0.0",
        owner_team="team-a"
    ))

    await service_catalog.create_service(ServiceCreate(
        name="service2",
        category="ai-platform",
        description="Service 2",
        version="1.0.0",
        owner_team="team-b"
    ))

    teams = await service_catalog.get_teams()
    assert len(teams) == 2
    assert "team-a" in teams
    assert "team-b" in teams


@pytest.mark.asyncio
async def test_health_check(service_catalog):
    """Test health check."""
    health = await service_catalog.health_check()
    assert "status" in health
    assert health["status"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_search_services(service_catalog):
    """Test service search."""
    # Create services
    await service_catalog.create_service(ServiceCreate(
        name="data-lake-service",
        category="data-platform",
        description="Data lake storage service",
        version="1.0.0",
        owner_team="data-team"
    ))

    await service_catalog.create_service(ServiceCreate(
        name="ml-training-service",
        category="ai-platform",
        description="ML training pipeline",
        version="1.0.0",
        owner_team="ml-team"
    ))

    # Search by name
    results = await service_catalog.list_services(search="data-lake")
    assert len(results) == 1
    assert results[0].name == "data-lake-service"

    # Search by description
    results = await service_catalog.list_services(search="training")
    assert len(results) == 1
    assert results[0].name == "ml-training-service"