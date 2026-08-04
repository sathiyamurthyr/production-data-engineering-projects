"""Tests for Data Discovery Service."""

import pytest

from platform.metadata.models import Asset, AssetType, SensitivityLevel, Column
from platform.metadata.repository import MetadataRepository
from platform.catalog.catalog import CatalogService
from platform.search.search import SearchService
from platform.discovery.discovery import DataDiscoveryService


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


@pytest.fixture
def discovery(catalog, search):
    """Create a test discovery service."""
    return DataDiscoveryService(catalog, search)


def test_discover_sensitive_data_pii(discovery, catalog):
    """Test PII data discovery."""
    asset = Asset(
        name="customer_data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        columns=[
            Column(name="customer_id", data_type="string"),
            Column(name="email", data_type="string"),
            Column(name="phone_number", data_type="string"),
            Column(name="ssn", data_type="string"),
        ],
    )
    catalog.register_asset(asset)
    
    findings = discovery.discover_sensitive_data(asset)
    assert len(findings["pii"]) > 0
    assert findings["confidence_score"] > 0


def test_discover_sensitive_data_phi(discovery, catalog):
    """Test PHI data discovery."""
    asset = Asset(
        name="patient_records",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.patient",
        columns=[
            Column(name="patient_id", data_type="string"),
            Column(name="medical_record", data_type="string"),
            Column(name="diagnosis", data_type="string"),
            Column(name="doctor_notes", data_type="string"),
        ],
    )
    catalog.register_asset(asset)
    
    findings = discovery.discover_sensitive_data(asset)
    assert len(findings["phi"]) > 0


def test_classify_sensitivity_pii(discovery, catalog):
    """Test PII sensitivity classification."""
    asset = Asset(
        name="customer_emails",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.emails",
        columns=[Column(name="email", data_type="string")],
    )
    catalog.register_asset(asset)
    
    sensitivity = discovery.classify_sensitivity(asset)
    assert sensitivity == SensitivityLevel.PII


def test_classify_sensitivity_phi(discovery, catalog):
    """Test PHI sensitivity classification."""
    asset = Asset(
        name="medical_records",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.medical",
        columns=[
            Column(name="patient_id", data_type="string"),
            Column(name="diagnosis", data_type="string"),
        ],
    )
    catalog.register_asset(asset)
    
    sensitivity = discovery.classify_sensitivity(asset)
    assert sensitivity == SensitivityLevel.PHI


def test_auto_tag_asset(discovery, catalog):
    """Test automatic asset tagging."""
    asset = Asset(
        name="customer_orders",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.orders",
    )
    catalog.register_asset(asset)
    
    tags = discovery.auto_tag_asset(asset)
    assert "customer_data" in tags
    assert "transactional_data" in tags
    assert "snowflake" in tags


def test_suggest_business_terms(discovery, catalog):
    """Test business term suggestions."""
    asset = Asset(
        name="customer_transactions",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.transactions",
    )
    catalog.register_asset(asset)
    
    suggestions = discovery.suggest_business_terms(asset)
    assert "Customer" in suggestions
    assert "Transaction" in suggestions


def test_discover_orphaned_assets(discovery, catalog):
    """Test orphaned asset discovery."""
    asset1 = Asset(
        name="standalone_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.standalone",
    )
    asset2 = Asset(
        name="connected_table",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.connected",
        upstream_assets=[asset1.urn],
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    orphaned = discovery.discover_orphaned_assets()
    assert len(orphaned) == 0  # asset1 has downstream asset2
    
    # Make both orphaned
    asset2.upstream_assets = []
    catalog.update_asset(asset2.urn, {"upstream_assets": []})
    
    orphaned = discovery.discover_orphaned_assets()
    assert len(orphaned) == 2


def test_discover_duplicate_assets(discovery, catalog):
    """Test duplicate asset discovery."""
    asset1 = Asset(
        name="customer_data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
    )
    asset2 = Asset(
        name="customer_data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema2.customer",
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    duplicates = discovery.discover_duplicate_assets()
    assert len(duplicates) > 0
    assert duplicates[0]["normalized_name"] == "customerdata"


def test_discover_data_products(discovery, catalog):
    """Test data product discovery."""
    asset = Asset(
        name="sales_dashboard",
        description="Executive sales dashboard with KPIs and metrics",
        asset_type=AssetType.DASHBOARD,
        platform="tableau",
        platform_id="sales_dashboard",
        quality_score=0.95,
    )
    catalog.register_asset(asset)
    
    data_products = discovery.discover_data_products()
    assert len(data_products) == 1
    assert data_products[0]["name"] == "sales_dashboard"


def test_get_discovery_report(discovery, catalog):
    """Test discovery report generation."""
    asset1 = Asset(
        name="customer_data",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.customer",
        columns=[Column(name="email", data_type="string")],
    )
    asset2 = Asset(
        name="medical_records",
        asset_type=AssetType.TABLE,
        platform="snowflake",
        platform_id="db.schema.medical",
        columns=[Column(name="diagnosis", data_type="string")],
    )
    
    catalog.register_asset(asset1)
    catalog.register_asset(asset2)
    
    report = discovery.get_discovery_report()
    assert report["total_assets"] == 2
    assert report["pii_assets"] >= 1
    assert report["phi_assets"] >= 1
    assert report["sensitive_assets"] >= 1
    assert len(report["recommendations"]) >= 0