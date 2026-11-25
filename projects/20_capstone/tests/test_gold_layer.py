import pytest
from pathlib import Path
from src.gold.gold_dim_date import GoldDimDateGenerator
from src.gold.gold_dim_products import GoldDimProductsProcessor
from src.gold.gold_dim_customers import GoldDimCustomersProcessor
from src.gold.gold_fact_orders import GoldFactOrdersProcessor
from src.gold.gold_marketing_metrics import GoldMarketingMetricsProcessor
from src.gold.gold_sales_analytics import GoldSalesAnalyticsProcessor

def test_gold_dimensions(test_config):
    # 1. Date
    date_gen = GoldDimDateGenerator(test_config)
    date_gen.generate()
    gold_date_path = Path(test_config.storage_config["gold_path"]) / "dim_date"
    assert gold_date_path.exists()
    assert len(list(gold_date_path.glob("**/*"))) > 0

    # 2. Products
    prod_proc = GoldDimProductsProcessor(test_config)
    prod_proc.process()
    gold_products_path = Path(test_config.storage_config["gold_path"]) / "dim_products"
    assert gold_products_path.exists()
    assert len(list(gold_products_path.glob("**/*"))) > 0

    # 3. Customers
    cust_proc = GoldDimCustomersProcessor(test_config)
    cust_proc.process()
    gold_customers_path = Path(test_config.storage_config["gold_path"]) / "dim_customers"
    assert gold_customers_path.exists()
    assert len(list(gold_customers_path.glob("**/*"))) > 0

def test_gold_facts_and_analytics(test_config):
    # Fact Orders
    fact_proc = GoldFactOrdersProcessor(test_config)
    fact_proc.process()
    gold_fact_path = Path(test_config.storage_config["gold_path"]) / "fact_orders"
    assert gold_fact_path.exists()
    assert len(list(gold_fact_path.glob("**/*"))) > 0

    # Marketing metrics
    mkt_proc = GoldMarketingMetricsProcessor(test_config)
    mkt_proc.process()
    gold_mkt_path = Path(test_config.storage_config["gold_path"]) / "marketing_metrics"
    assert gold_mkt_path.exists()
    assert len(list(gold_mkt_path.glob("**/*"))) > 0

    # Sales analytics
    sales_proc = GoldSalesAnalyticsProcessor(test_config)
    sales_proc.process()
    gold_sales_path = Path(test_config.storage_config["gold_path"]) / "sales_analytics"
    assert (gold_sales_path / "category_sales").exists()
    assert (gold_sales_path / "daily_sales").exists()
    assert len(list((gold_sales_path / "category_sales").glob("**/*"))) > 0
    assert len(list((gold_sales_path / "daily_sales").glob("**/*"))) > 0
