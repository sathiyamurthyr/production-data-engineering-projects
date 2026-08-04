"""Tests for Catalog Service."""

import pytest
from uuid import uuid4

from platform.metadata.models import Asset, AssetType, SensitivityLevel, Column
from platform.metadata.repository import MetadataRepository
from platform.catalog.catalog import CatalogService


@pytest.fixture
def repository():
    """Create a test repository."""
    return MetadataRepository()


@pytest.fixture
def catalog(repository):
    """Create a test catalog service."""
    return CatalogService(repository)


def test_register_asset(catalog):
    """Test asset registration."""
    asset = Asset(
        name="test_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table",
    )
    
    registered = catalog.register_asset(asset)
    assert registered.id == asset.id
    assert catalog.get_asset(asset.urn) == asset


def test_get_asset_by_id(catalog):
    """Test getting asset by ID."""
    asset = Asset(
        name="test_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table",
    )
    catalog.register_asset(asset)
    
    found = catalog.get_asset_by_id(str(asset.id))
    assert found == asset


def test_update_asset(catalog):
    """Test asset update."""
    asset = Asset(
        name="test_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table",
    )
    catalog.register_asset(asset)
    
    updated = catalog.update_asset(asset.urn, {"description": "Updated description"})
    assert updated.description == "Updated description"


def test_delete_asset(catalog):
    """Test asset deletion."""
    asset = Asset(
        name="test_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table",
    )
    catalog.register_asset(asset)
    
    success = catalog.delete_asset(asset.urn)
    assert success is True
    assert catalog.get_asset(asset.urn) is None


def test_list_assets_with_filters(catalog):
    """Test listing assets with filters."""
    asset1 = Asset(
        name="table1",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table1",
        domain="sales",
    )
    asset2 = Asset(
        name="table2",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table2",
        domain="marketing",
    )
    asset3 = Asset(
        name="stream1",
        asset_type=AssetType.STREAM,
        platform="kafka",
        platform_id="topic1",
        domain="sales",
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    catalog.register_asset(asset3)
    
    # Filter by platform
    snowflake_assets = catalog.list_assets(platform="snowflake")
    assert len(snowflake_assets) == 2
    
    # Filter by domain
    sales_assets = catalog.list_assets(domain="sales")
    assert len(sales_assets) == 2
    
    # Filter by asset type
    tables = catalog.list_assets(asset_type=AssetType.TABLE)
    assert len(tables) == 2
    
    streams = catalog.list_assets(asset_type=AssetType.STREAM)
    assert len(streams) == 1


def test_search_assets(catalog):
    """Test asset search."""
    asset1 = Asset(
        name="customer_table",
        description="Contains customer information",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        tags=["customer", "pii"],
    )
    asset2 = Asset(
        name="order_table",
        description="Contains order data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.order",
        tags=["order"],
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    # Search by name
    results = catalog.search_assets("customer")
    assert len(results) == 1
    assert results[0].name == "customer_table"
    
    # Search by description
    results = catalog.search_assets("order")
    assert len(results) == 1
    assert results[0].name == "order_table"
    
    # Search by tag
    results = catalog.search_assets("pii")
    assert len(results) == 1
    assert results[0].name == "customer_table"


def test_asset_lineage(catalog):
    """Test asset lineage."""
    asset1 = Asset(
        name="source_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.source",
    )
    asset2 = Asset(
        name="transform_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.transform",
        upstream_assets=[asset1.urn],
    )
    asset3 = Asset(
        name="report_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.report",
        upstream_assets=[asset2.urn],
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    catalog.register_asset(asset3)
    
    lineage = catalog.get_asset_lineage(asset3.urn)
    assert len(lineage["nodes"]) == 3
    assert len(lineage["edges"]) == 2


def test_catalog_stats(catalog):
    """Test catalog statistics."""
    asset1 = Asset(
        name="table1",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table1",
        domain="sales",
    )
    asset2 = Asset(
        name="stream1",
        asset_type=AssetType.STREAM,
        platform="kafka",
        platform_id="topic1",
        domain="marketing",
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    stats = catalog.get_catalog_stats()
    assert stats["total_assets"] == 2
    assert stats["by_platform"]["snowflake"] == 1
    assert stats["by_platform"]["kafka"] == 1
    assert stats["by_domain"]["sales"] == 1
    assert stats["by_domain"]["marketing"] == 1