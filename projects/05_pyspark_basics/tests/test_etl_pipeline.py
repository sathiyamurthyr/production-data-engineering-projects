"""
test_etl_pipeline.py
====================
Integration test suite for src/etl_pipeline.py using pytest.
"""

from __future__ import annotations

import os
import pytest
from pyspark.sql import SparkSession

from src.etl_pipeline import PySparkETLPipeline


def test_etl_pipeline_end_to_end(spark: SparkSession, tmp_path):
    # Setup custom temporary paths config
    config_dict = {
        "app": {"name": "TestETLPipeline", "environment": "test"},
        "spark_config": {"spark.sql.shuffle.partitions": "2"},
        "paths": {
            "raw_sales_csv": "sample-data/sales_data.csv",
            "raw_events_json": "sample-data/customer_events.json",
            "raw_products_csv": "sample-data/product_catalog.csv",
            "output_processed_sales": str(tmp_path / "processed_sales"),
            "output_category_summary": str(tmp_path / "category_summary"),
            "output_quarantine": str(tmp_path / "quarantine"),
        },
        "pipeline": {
            "min_order_amount": 0.0,
            "valid_statuses": ["Completed", "Shipped"],
        },
    }

    pipeline = PySparkETLPipeline()
    pipeline.config = config_dict
    pipeline.spark = spark
    from src.io_operations import PySparkIO
    pipeline.io = PySparkIO(spark)

    # Execute extraction
    sales, events, products = pipeline.extract_sources()
    assert sales.count() > 0
    assert events.count() > 0
    assert products.count() > 0

    # Audit & quarantine
    valid_sales, quarantine = pipeline.audit_and_quarantine(sales)
    assert valid_sales.count() > 0

    # Transform & enrich
    enriched = pipeline.transform_and_enrich(valid_sales, products)
    assert "gross_amount" in enriched.columns
    assert "calculated_total" in enriched.columns

    # Compute analytics
    cat_summary, top_prods, running_totals = pipeline.compute_analytics(enriched)
    assert cat_summary.count() > 0
    assert top_prods.count() > 0
    assert running_totals.count() > 0

    # Load outputs
    pipeline.load_outputs(enriched, cat_summary, quarantine)

    assert os.path.exists(str(tmp_path / "processed_sales"))
    assert os.path.exists(str(tmp_path / "category_summary"))
