"""
Module: medallion_pipeline.py
=============================
End-to-end Medallion Architecture Pipeline (Bronze -> Silver -> Gold).

Architecture Overview:
    ┌──────────────────┐
    │ Raw Data Sources │ (JSON events, CSV updates)
    └────────┬─────────┘
             │ Ingest Raw (Append-only + metadata)
             ▼
    ┌──────────────────┐
    │  BRONZE LAYER    │ Raw raw_events table (Schema preservation, input_file_name, ingested_at)
    └────────┬─────────┘
             │ Cleanse, deduplicate, unpack JSON payloads
             ▼
    ┌──────────────────┐
    │  SILVER LAYER    │ Curated silver_cleaned_events table (Deduplicated on event_id, validated types)
    └────────┬─────────┘
             │ Business aggregations & domain metrics
             ▼
    ┌──────────────────┐
    │   GOLD LAYER     │ Business gold_user_daily_metrics table (Aggregated total_amount, counts by user/date)
    └──────────────────┘

Business Use Case:
    The Medallion architecture structures data lakes into incremental refinement layers.
    - Bronze: Preserves raw data fidelity so data can be reprocessed if business logic changes.
    - Silver: Cleansed, normalized, deduplicated single source of truth for analysts and data science.
    - Gold: Aggregated star-schema / domain tables optimized for low-latency BI dashboards and reporting.

Interview Questions:
    Q: Why not jump straight from raw files to Gold aggregations?
    A: Skipping Bronze/Silver loses auditability. If raw data contains errors or business logic changes,
       having a raw Bronze layer allows reprocessing without re-fetching from source systems. Silver provides
       a reusable, clean data layer so multiple Gold pipelines don't re-implement cleansing.

    Q: How do Delta ACID transactions support Medallion pipelines?
    A: They allow concurrent read/write across layers. Silver pipelines can read Bronze while Bronze ingests,
       and Gold can read Silver continuously via Structured Streaming or MERGE without read locks.
"""

import os
import logging
from typing import Dict, Any
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
from delta.tables import DeltaTable

from src.merge_operations import upsert_scd_type_1
from src.optimize_zorder import run_zorder_optimize

logger = logging.getLogger(__name__)


def process_bronze_layer(
    spark: SparkSession,
    raw_json_path: str,
    bronze_table_path: str
) -> DataFrame:
    """
    Ingest raw JSON event files into Bronze Delta table.

    Applies minimal transformation: adds ingestion metadata (`_ingested_at`, `_source_file`).

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    raw_json_path : str
        Path to input raw JSON file or directory.
    bronze_table_path : str
        Path for Bronze Delta table storage.

    Returns
    -------
    DataFrame
        Bronze DataFrame.
    """
    logger.info("--- Processing Bronze Layer ---")
    raw_df = spark.read.json(raw_json_path)

    bronze_df = (
        raw_df
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
    )

    (
        bronze_df.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(bronze_table_path)
    )
    logger.info("Bronze layer written to '%s' (%d records)", bronze_table_path, bronze_df.count())
    return spark.read.format("delta").load(bronze_table_path)


def process_silver_layer(
    spark: SparkSession,
    bronze_table_path: str,
    silver_table_path: str
) -> DataFrame:
    """
    Cleanse, unpack, and deduplicate Bronze events into Silver Delta table.

    Transformations:
    - Cast timestamp string to TimestampType.
    - Parse JSON payload field.
    - Filter invalid or null event_ids.
    - Deduplicate on event_id using windowing or dropDuplicates.
    - Write to Silver table via MERGE upsert.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    bronze_table_path : str
        Bronze Delta table path.
    silver_table_path : str
        Silver Delta table path.

    Returns
    -------
    DataFrame
        Silver DataFrame.
    """
    logger.info("--- Processing Silver Layer ---")
    bronze_df = spark.read.format("delta").load(bronze_table_path)

    # Cleanse and cast
    cleaned_df = (
        bronze_df
        .filter(F.col("event_id").isNotNull())
        .withColumn("timestamp", F.to_timestamp(F.col("timestamp")))
        .withColumn("event_date", F.to_date(F.col("timestamp")))
        .withColumn("amount", F.coalesce(F.col("amount"), F.lit(0.0)))
        .dropDuplicates(["event_id"])
    )

    # Check if target silver table exists for merge upsert
    if not DeltaTable.isDeltaTable(spark, silver_table_path):
        logger.info("Creating initial Silver table at '%s'", silver_table_path)
        (
            cleaned_df.write
            .format("delta")
            .mode("overwrite")
            .partitionBy("event_date")
            .option("delta.enableChangeDataFeed", "true")
            .save(silver_table_path)
        )
    else:
        logger.info("Merging updates into existing Silver table at '%s'", silver_table_path)
        upsert_scd_type_1(
            spark=spark,
            target_table_path=silver_table_path,
            updates_df=cleaned_df,
            primary_key="event_id"
        )

    silver_df = spark.read.format("delta").load(silver_table_path)
    logger.info("Silver layer updated at '%s' (%d total records)", silver_table_path, silver_df.count())
    return silver_df


def process_gold_layer(
    spark: SparkSession,
    silver_table_path: str,
    gold_table_path: str
) -> DataFrame:
    """
    Aggregate Silver events into daily business metrics per user in Gold Delta table.

    Aggregations:
    - Group by `event_date`, `user_id`.
    - Metrics: total_events, purchase_count, total_amount, avg_amount.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    silver_table_path : str
        Silver Delta table path.
    gold_table_path : str
        Gold Delta table path.

    Returns
    -------
    DataFrame
        Gold DataFrame.
    """
    logger.info("--- Processing Gold Layer ---")
    silver_df = spark.read.format("delta").load(silver_table_path)

    gold_df = (
        silver_df
        .groupBy("event_date", "user_id")
        .agg(
            F.count("event_id").alias("total_events"),
            F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchase_count"),
            F.round(F.sum("amount"), 2).alias("total_amount"),
            F.round(F.avg("amount"), 2).alias("avg_amount"),
            F.max("timestamp").alias("last_event_time")
        )
        .withColumn("_updated_at", F.current_timestamp())
    )

    (
        gold_df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(gold_table_path)
    )

    # Run Z-ORDER on Gold table for user_id lookup performance
    try:
        run_zorder_optimize(
            spark=spark,
            table_path=gold_table_path,
            zorder_cols=["user_id"]
        )
    except Exception as e:
        logger.warning("Could not execute OPTIMIZE Z-ORDER on Gold table: %s", e)

    gold_final = spark.read.format("delta").load(gold_table_path)
    logger.info("Gold layer generated at '%s' (%d aggregate records)", gold_table_path, gold_final.count())
    return gold_final


def run_medallion_pipeline(
    spark: SparkSession,
    raw_data_path: str,
    output_base_dir: str
) -> Dict[str, DataFrame]:
    """
    Execute full Medallion pipeline (Bronze -> Silver -> Gold).

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    raw_data_path : str
        Input raw sample JSON path.
    output_base_dir : str
        Root path for storing Lakehouse layer tables.

    Returns
    -------
    Dict[str, DataFrame]
        Dictionary of layer names to DataFrames ('bronze', 'silver', 'gold').
    """
    bronze_path = os.path.join(output_base_dir, "bronze", "events")
    silver_path = os.path.join(output_base_dir, "silver", "events")
    gold_path = os.path.join(output_base_dir, "gold", "user_daily_metrics")

    bronze_df = process_bronze_layer(spark, raw_data_path, bronze_path)
    silver_df = process_silver_layer(spark, bronze_path, silver_path)
    gold_df = process_gold_layer(spark, silver_path, gold_path)

    return {
        "bronze": bronze_df,
        "silver": silver_df,
        "gold": gold_df,
    }
