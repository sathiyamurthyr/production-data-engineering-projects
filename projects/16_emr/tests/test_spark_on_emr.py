"""
PyTest suite for PySpark ETL pipeline.
Spins up a local Spark session to test data transformation, filtering, and writing.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import os
import shutil
import pytest
from pyspark.sql import SparkSession
from src.spark_on_emr import create_spark_session, run_etl


@pytest.fixture(scope="module")
def spark_session():
    """
    Initializes a local SparkSession for testing.
    """
    spark = create_spark_session(app_name="Test-Spark-ETL", is_local=True)
    yield spark
    spark.stop()


def test_spark_session_creation(spark_session):
    assert isinstance(spark_session, SparkSession)
    assert spark_session.conf.get("spark.sql.shuffle.partitions") == "4"


def test_run_etl(spark_session, tmp_path):
    # Setup test file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(current_dir, "../sample-data/large_dataset.csv")
    output_parquet_dir = os.path.join(tmp_path, "analytics_output")

    # Verify input file exists
    assert os.path.exists(input_csv), f"Sample dataset not found at: {input_csv}"

    # Execute PySpark ETL
    run_etl(spark_session, input_csv, output_parquet_dir)

    # Assert Parquet output was written
    assert os.path.exists(output_parquet_dir), "ETL did not write parquet output"
    
    # Read output back to verify schema and data integrity
    df_result = spark_session.read.parquet(output_parquet_dir)
    
    # Assert columns are correct
    expected_cols = {"category", "total_sales_amount", "transaction_count", "processed_at", "year", "month", "country"}
    assert set(df_result.columns) == expected_cols

    # Verify the filtering logic works: "FAILED" transactions should not be counted
    # Let's read raw input directly
    df_raw = spark_session.read.option("header", "true").csv(input_csv)
    raw_failed_count = df_raw.filter(df_raw.status == "FAILED").count()
    assert raw_failed_count > 0, "Input dataset must have FAILED rows to test the filter logic"

    # Gather results from output parquet
    # Note that total transactions count in output parquet must equal the total non-failed transactions in raw
    raw_non_failed_count = df_raw.filter(df_raw.status != "FAILED").count()
    total_processed_transactions = df_result.groupBy().sum("transaction_count").collect()[0][0]
    
    assert total_processed_transactions == raw_non_failed_count, (
        f"Expected {raw_non_failed_count} processed transactions, but got {total_processed_transactions}"
    )

    # Verify partitioning directories are created by scanning files
    # Parquet partitions will look like: analytics_output/year=2026/month=7/country=USA/*.parquet
    # We check if 'year=2026' directory exists
    partition_dirs = os.listdir(output_parquet_dir)
    assert any("year=" in d for d in partition_dirs), "Parquet partition directories (year=) were not created"
