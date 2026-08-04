"""Tests for Search Service."""

import pytest

from platform.metadata.models import Asset, AssetType, SensitivityLevel
from platform.metadata.repository import MetadataRepository
from platform.catalog.catalog import CatalogService
from platform.search.search import SearchService


@pytest.fixture
def repository():
    """Create a test repository."""
    return MetadataRepository()


@pytest.fixture
def catalog(repository):
    """Create a test catalog service."""
    return CatalogService(repository)


@pytest.fixture
def search(catalog):
    """Create a test search service."""
    return SearchService(catalog)


def test_search_by_name(search, catalog):
    """Test searching by asset name."""
    asset1 = Asset(
        name="customer_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
    )
    asset2 = Asset(
        name="order_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.order",
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    results = search.search("customer")
    assert len(results) > 0
    assert results[0]["asset"].name == "customer_table"


def test_search_by_description(search, catalog):
    """Test searching by description."""
    asset = Asset(
        name="sales_data",
        description="Contains all sales transactions and revenue data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.sales",
    )
    catalog.register_asset(asset)
    
    results = search.search("revenue")
    assert len(results) > 0
    assert results[0]["asset"].name == "sales_data"


def test_search_by_tags(search, catalog):
    """Test searching by tags."""
    asset = Asset(
        name="customer_data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        tags=["pii", "customer", "restricted"],
    )
    catalog.register_asset(asset)
    
    results = search.search("pii")
    assert len(results) > 0
    assert results[0]["asset"].name == "customer_data"


def test_search_suggestions(search, catalog):
    """Test search suggestions."""
    asset = Asset(
        name="customer_transactions",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.transactions",
    )
    catalog.register_asset(asset)
    
    suggestions = search.get_suggestions("cust")
    assert len(suggestions) > 0
    assert any("customer" in s for s in suggestions)


def test_search_by_type(search, catalog):
    """Test searching by asset type."""
    table = Asset(
        name="table1",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table1",
    )
    stream = Asset(
        name="stream1",
        asset_type=AssetType.STREAM,
        platform="kafka",
        platform_id="topic1",
    )
    
    catalog.register_asset(table)
    catalog.register_asset(stream)
    
    results = search.search_by_type("table", AssetType.TABLE.value)
    assert len(results) > 0
    assert all(r["asset"].asset_type == AssetType.TABLE for r in results)


def test_search_by_platform(search, catalog):
    """Test searching by platform."""
    snowflake_asset = Asset(
        name="snowflake_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.table1",
    )
    kafka_asset = Asset(
        name="kafka_topic",
        asset_type=AssetType.STREAM,
        platform="kafka",
        platform_id="topic1",
    )
    
    catalog.register_asset(snowflake_asset)
    catalog.register_asset(kafka_asset)
    
    results = search.search_by_platform("table", "snowflake")
    assert len(results) > 0
    assert all(r["asset"].platform == "snowflake" for r in results)


def test_faceted_search(search, catalog):
    """Test faceted search."""
    asset1 = Asset(
        name="customer_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        domain="sales",
    )
    asset2 = Asset(
        name="order_stream",
        asset_type=AssetType.STREAM,
        platform="kafka",
        platform_id="topic1",
        domain="sales",
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    result = search.get_faceted_search("sales")
    assert "results" in result
    assert "facets" in result
    assert result["total"] == 2


def test_search_scoring(search, catalog):
    """Test search result scoring."""
    asset = Asset(
        name="customer_data",
        description="Customer information and data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
    )
    catalog.register_asset(asset)
    
    results = search.search("customer")
    assert len(results) > 0
    assert "score" in results[0]
    assert results[0]["score"] > 0


def test_match_reason(search, catalog):
    """Test match reason generation."""
    asset = Asset(
        name="customer_table",
        description="Customer data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        tags=["pii"],
        glossary_terms=["Customer"],
    )
    catalog.register_asset(asset)
    
    results = search.search("customer")
    assert len(results) > 0
    assert "match_reason" in results[0]
    assert len(results[0]["match_reason"]) > 0