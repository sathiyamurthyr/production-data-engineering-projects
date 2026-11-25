"""
Unit tests for Medallion Architecture Pipeline (Bronze -> Silver -> Gold).
"""

import os
import pytest
from pyspark.sql import SparkSession

from src.medallion_pipeline import run_medallion_pipeline


def test_medallion_pipeline_execution(spark: SparkSession, temp_delta_dir: str):
    """Test full Medallion pipeline from raw sample JSON to Gold aggregates."""
    raw_data_file = os.path.join(
        "d:/engineering-projects/production-data-engineering-projects/projects/06_delta_lake",
        "sample-data",
        "raw_events.json"
    )
    
    # Run full pipeline
    pipeline_results = run_medallion_pipeline(
        spark=spark,
        raw_data_path=raw_data_file,
        output_base_dir=temp_delta_dir
    )
    
    bronze_df = pipeline_results["bronze"]
    silver_df = pipeline_results["silver"]
    gold_df = pipeline_results["gold"]
    
    # Check Bronze
    assert "_ingested_at" in bronze_df.columns
    assert "_source_file" in bronze_df.columns
    assert bronze_df.count() >= 10
    
    # Check Silver (Deduplicated on event_id)
    assert "event_date" in silver_df.columns
    # Check duplicate evt-001 was deduplicated
    evt_count = silver_df.filter(silver_df.event_id == "evt-001").count()
    assert evt_count == 1
    
    # Check Gold (Aggregated user daily metrics)
    assert "total_events" in gold_df.columns
    assert "total_amount" in gold_df.columns
    assert gold_df.count() > 0
