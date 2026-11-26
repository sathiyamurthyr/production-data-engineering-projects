import pytest
from pathlib import Path
from src.silver.silver_orders import SilverOrdersProcessor
from src.silver.silver_events import SilverEventsProcessor
from src.silver.silver_products import SilverProductsProcessor
from src.silver.silver_customers import SilverCustomersProcessor

def test_silver_orders_processing(test_config):
    processor = SilverOrdersProcessor(test_config)
    processor.process()
    
    silver_orders_path = Path(test_config.storage_config["silver_path"]) / "orders"
    assert silver_orders_path.exists()
    assert len(list(silver_orders_path.glob("**/*"))) > 0

def test_silver_events_processing(test_config):
    processor = SilverEventsProcessor(test_config)
    processor.process()
    
    silver_events_path = Path(test_config.storage_config["silver_path"]) / "events"
    assert silver_events_path.exists()
    assert len(list(silver_events_path.glob("**/*"))) > 0

def test_silver_products_processing(test_config):
    processor = SilverProductsProcessor(test_config)
    processor.process()
    
    silver_products_path = Path(test_config.storage_config["silver_path"]) / "products"
    assert silver_products_path.exists()
    assert len(list(silver_products_path.glob("**/*"))) > 0

def test_silver_customers_processing(test_config):
    processor = SilverCustomersProcessor(test_config)
    processor.process()
    
    silver_customers_path = Path(test_config.storage_config["silver_path"]) / "customers"
    assert silver_customers_path.exists()
    assert len(list(silver_customers_path.glob("**/*"))) > 0
