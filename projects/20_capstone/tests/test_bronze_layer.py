import pytest
from pathlib import Path
from src.bronze.bronze_orders import BronzeOrdersIngestor
from src.bronze.bronze_events import BronzeEventsIngestor
from src.bronze.bronze_catalog import BronzeCatalogIngestor

def test_bronze_orders_ingestion(test_config):
    """Verifies that BronzeOrdersIngestor executes without errors and creates files."""
    ingestor = BronzeOrdersIngestor(test_config)
    ingestor.ingest()
    
    bronze_orders_path = Path(test_config.storage_config["bronze_path"]) / "orders"
    assert bronze_orders_path.exists()
    
    # Check if there are parquet files (fallback mode output) or delta files
    files = list(bronze_orders_path.glob("**/*"))
    assert len(files) > 0

def test_bronze_events_ingestion(test_config):
    """Verifies that BronzeEventsIngestor executes without errors and creates files."""
    ingestor = BronzeEventsIngestor(test_config)
    ingestor.ingest()
    
    bronze_events_path = Path(test_config.storage_config["bronze_path"]) / "events"
    assert bronze_events_path.exists()
    
    files = list(bronze_events_path.glob("**/*"))
    assert len(files) > 0

def test_bronze_catalog_ingestion(test_config):
    """Verifies that BronzeCatalogIngestor executes without errors and creates catalog files."""
    ingestor = BronzeCatalogIngestor(test_config)
    ingestor.ingest()
    
    bronze_products_path = Path(test_config.storage_config["bronze_path"]) / "products"
    bronze_customers_path = Path(test_config.storage_config["bronze_path"]) / "customers"
    
    assert bronze_products_path.exists()
    assert bronze_customers_path.exists()
    
    prod_files = list(bronze_products_path.glob("**/*"))
    cust_files = list(bronze_customers_path.glob("**/*"))
    
    assert len(prod_files) > 0
    assert len(cust_files) > 0
