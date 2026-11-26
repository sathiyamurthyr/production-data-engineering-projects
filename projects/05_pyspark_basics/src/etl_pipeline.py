"""
etl_pipeline.py
===============
End-to-End PySpark ETL Pipeline Orchestrator.

Business Use Case:
    Orchestrates the entire batch ingestion, quality validation, enrichment, windowing,
    aggregation, and multi-format output writing for sales e-commerce analytics.

Pipeline Stages:
    1. SparkSession Initialization via `SparkSessionFactory`
    2. Extraction: Read raw CSV sales data, JSON customer events, and CSV product catalog with explicit schemas.
    3. Data Quality Audit: Validate primary key uniqueness, null bounds, split into valid and quarantine records.
    4. Transformation & Enrichment: Join sales with product catalog, add calculated monetary metrics (gross, discount, total).
    5. Windowing Analytics: Calculate top products per category and running totals per region.
    6. Aggregation: Generate summarized category rollups.
    7. Persistence: Write partitioned Parquet files to target directory.

Interview Questions:
    Q: How do you structure an enterprise PySpark ETL pipeline for testability?
    A: Separate SparkSession lifecycle management from business transformation functions.
       Pass DataFrames directly to modular transformation functions so unit tests can invoke
       each step independently using mock in-memory DataFrames without reading disk I/O.

    Q: How do you handle schema drift or corrupted rows in an automated ETL job?
    A: Enforce explicit StructType schemas on ingestion, set permissive read modes with `_corrupt_record`,
       and execute quality rules to write failing records to a dedicated quarantine sink before main pipeline execution.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Dict, Tuple

import yaml
from pyspark.sql import DataFrame, SparkSession

from src.aggregations import summarize_sales_by_category
from src.data_quality import check_null_counts, check_uniqueness, validate_value_ranges
from src.dataframe_basics import CUSTOMER_EVENT_SCHEMA, PRODUCT_SCHEMA, SALES_SCHEMA
from src.io_operations import PySparkIO
from src.joins import execute_broadcast_join
from src.spark_session import SparkSessionFactory
from src.transformations import add_derived_metrics, filter_sales
from src.window_functions import calculate_running_totals_and_moving_avg, calculate_top_n_per_category

logger = logging.getLogger(__name__)


class PySparkETLPipeline:
    """
    Production E-Commerce Sales ETL Pipeline Orchestrator.
    """

    def __init__(self, config_path: str = "configs/spark_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.spark: SparkSession = None
        self.io: PySparkIO = None

    def _load_config(self) -> Dict:
        """Load YAML configuration settings."""
        if not os.path.exists(self.config_path):
            logger.warning("Config file '%s' not found. Using fallback defaults.", self.config_path)
            return {
                "app": {"name": "PySparkBasicsETLPipeline", "environment": "local"},
                "spark_config": {"spark.sql.shuffle.partitions": "4"},
                "paths": {
                    "raw_sales_csv": "sample-data/sales_data.csv",
                    "raw_events_json": "sample-data/customer_events.json",
                    "raw_products_csv": "sample-data/product_catalog.csv",
                    "output_processed_sales": "output/processed_sales_parquet",
                    "output_category_summary": "output/category_summary_parquet",
                    "output_quarantine": "output/quarantine_records",
                },
                "pipeline": {
                    "min_order_amount": 0.0,
                    "valid_statuses": ["Completed", "Shipped"],
                },
            }

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def initialize_spark(self) -> None:
        """Create configured SparkSession instance."""
        app_name = self.config.get("app", {}).get("name", "PySparkBasicsETLPipeline")
        extra_conf = self.config.get("spark_config", {})

        self.spark = SparkSessionFactory.create_local(
            app_name=app_name,
            extra_config=extra_conf,
            log_level="WARN",
        )
        self.io = PySparkIO(self.spark)
        logger.info("Spark context initialized successfully.")

    def extract_sources(self) -> Tuple[DataFrame, DataFrame, DataFrame]:
        """
        Extract raw data from file sources with explicit schemas.

        Returns:
            Tuple of (sales_df, events_df, products_df).
        """
        paths = self.config["paths"]
        logger.info("Extracting sales, customer events, and products datasets...")

        sales_df = self.io.read_csv(paths["raw_sales_csv"], schema=SALES_SCHEMA)
        events_df = self.io.read_json(paths["raw_events_json"], schema=CUSTOMER_EVENT_SCHEMA)
        products_df = self.io.read_csv(paths["raw_products_csv"], schema=PRODUCT_SCHEMA)

        logger.info(
            "Extracted counts -> Sales: %d, Events: %d, Products: %d",
            sales_df.count(), events_df.count(), products_df.count()
        )
        return sales_df, events_df, products_df

    def audit_and_quarantine(self, sales_df: DataFrame) -> Tuple[DataFrame, DataFrame]:
        """
        Perform quality checks on sales data and isolate invalid records.

        Checks:
        - Check nulls in mandatory fields (sale_id, order_date)
        - Validate total_amount >= 0 and quantity > 0

        Returns:
            Tuple of (valid_sales_df, quarantine_sales_df).
        """
        logger.info("Running Data Quality Audit stage...")
        null_counts = check_null_counts(sales_df, ["sale_id", "order_date"])
        logger.info("Null counts audit: %s", null_counts)

        # Range rule verification
        range_rules = {"quantity": (1, 1000), "total_amount": (0.0, 100000.0)}
        valid_df, quarantine_df = validate_value_ranges(sales_df, range_rules)

        return valid_df, quarantine_df

    def transform_and_enrich(self, sales_df: DataFrame, products_df: DataFrame) -> DataFrame:
        """
        Transform sales records and enrich with product metadata.

        Returns:
            Transformed and enriched DataFrame.
        """
        logger.info("Transforming and enriching dataset...")
        statuses = self.config.get("pipeline", {}).get("valid_statuses", ["Completed", "Shipped"])
        min_amount = self.config.get("pipeline", {}).get("min_order_amount", 0.0)

        # Filter valid status and min amount
        filtered = filter_sales(sales_df, min_amount=min_amount, statuses=statuses)

        # Add computed metrics
        metrics_df = add_derived_metrics(filtered)

        # Broadcast join with products
        enriched_df = execute_broadcast_join(metrics_df, products_df, join_key="product_id", join_type="left")

        return enriched_df

    def compute_analytics(self, enriched_df: DataFrame) -> Tuple[DataFrame, DataFrame, DataFrame]:
        """
        Compute analytical summaries, window rankings, and running totals.

        Returns:
            Tuple of (category_summary_df, top_products_df, running_totals_df).
        """
        logger.info("Computing analytical summaries and window functions...")
        cat_summary = summarize_sales_by_category(enriched_df)
        top_products = calculate_top_n_per_category(enriched_df, top_n=3)
        running_totals = calculate_running_totals_and_moving_avg(enriched_df, window_size=3)

        return cat_summary, top_products, running_totals

    def load_outputs(
        self,
        enriched_sales: DataFrame,
        category_summary: DataFrame,
        quarantine_df: DataFrame,
    ) -> None:
        """
        Write processed data sinks to Parquet format.
        """
        paths = self.config["paths"]
        logger.info("Writing output datasets...")

        # Write processed sales partitioned by category
        self.io.write_parquet(
            enriched_sales,
            paths["output_processed_sales"],
            mode="overwrite",
            partition_cols=["category"],
        )

        # Write category summary
        self.io.write_parquet(
            category_summary,
            paths["output_category_summary"],
            mode="overwrite",
        )

        # Write quarantine records if present
        if quarantine_df.count() > 0:
            logger.warning("Writing %d quarantined records to %s", quarantine_df.count(), paths["output_quarantine"])
            self.io.write_parquet(quarantine_df, paths["output_quarantine"], mode="overwrite")

    def run(self) -> None:
        """Execute complete ETL workflow."""
        try:
            self.initialize_spark()
            raw_sales, raw_events, raw_products = self.extract_sources()
            valid_sales, quarantine_sales = self.audit_and_quarantine(raw_sales)
            enriched_sales = self.transform_and_enrich(valid_sales, raw_products)
            cat_summary, top_prods, running_totals = self.compute_analytics(enriched_sales)
            self.load_outputs(enriched_sales, cat_summary, quarantine_sales)
            logger.info("Pipeline execution completed successfully!")
        except Exception as e:
            logger.error("Pipeline execution failed: %s", str(e), exc_info=True)
            raise
        finally:
            if self.spark:
                SparkSessionFactory.stop(self.spark)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    pipeline = PySparkETLPipeline(config_path="configs/spark_config.yaml")
    pipeline.run()
