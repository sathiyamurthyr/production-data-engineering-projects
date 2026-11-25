"""
Module: change_data_feed.py
===========================
Delta Change Data Feed (CDF) enablement, batch reading, stream reading, and change auditing.

Business Use Case:
    When updating target tables (e.g. Silver or Gold tables via MERGE operations), downstream consumers
    (e.g., real-time search indexes, compliance reporting, external message queues, feature stores)
    need to know EXACTLY what rows were inserted, updated, or deleted in each transaction.
    Delta Change Data Feed automatically generates change events with metadata:
    - `_change_type`: 'insert', 'update_preimage' (value before update), 'update_postimage' (value after update), 'delete'.
    - `_commit_version`: Version number of the transaction.
    - `_commit_timestamp`: Commit timestamp.

Interview Questions:
    Q: What are the metadata columns added by Delta Change Data Feed?
    A: `_change_type`, `_commit_version`, and `_commit_timestamp`.

    Q: How does CDF handle UPDATE operations?
    A: For each updated row, CDF produces TWO records:
       1. `update_preimage`: The row's column values BEFORE the update.
       2. `update_postimage`: The row's column values AFTER the update.

    Q: Is CDF enabled by default on Delta tables?
    A: No. You must enable it per-table: `ALTER TABLE ... SET TBLPROPERTIES (delta.enableChangeDataFeed = true)`
       or globally via `spark.databricks.delta.properties.defaults.enableChangeDataFeed = true`.
"""

import logging
from typing import Optional
from pyspark.sql import SparkSession, DataFrame
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


def enable_cdf_on_table(spark: SparkSession, table_path: str) -> None:
    """
    Enable Change Data Feed property on an existing Delta table.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table file system path.
    """
    logger.info("Enabling delta.enableChangeDataFeed on table '%s'", table_path)
    spark.sql(f"ALTER TABLE delta.`{table_path}` SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")


def read_cdf_batch_by_version(
    spark: SparkSession,
    table_path: str,
    starting_version: int,
    ending_version: Optional[int] = None
) -> DataFrame:
    """
    Read Change Data Feed as a static DataFrame between versions.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    starting_version : int
        Start version for CDF log query (inclusive).
    ending_version : int, optional
        End version for CDF log query (inclusive). Defaults to latest version if omitted.

    Returns
    -------
    DataFrame
        DataFrame including table data plus _change_type, _commit_version, _commit_timestamp.
    """
    logger.info("Reading CDF batch for '%s' starting at version %d", table_path, starting_version)
    reader = (
        spark.read
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingVersion", starting_version)
    )
    if ending_version is not None:
        reader = reader.option("endingVersion", ending_version)

    return reader.load(table_path)


def read_cdf_batch_by_timestamp(
    spark: SparkSession,
    table_path: str,
    starting_timestamp: str,
    ending_timestamp: Optional[str] = None
) -> DataFrame:
    """
    Read Change Data Feed as a static DataFrame between timestamps.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    starting_timestamp : str
        Start timestamp (e.g. '2026-03-01 00:00:00').
    ending_timestamp : str, optional
        End timestamp.

    Returns
    -------
    DataFrame
        DataFrame with change feed events.
    """
    logger.info("Reading CDF batch for '%s' starting at timestamp '%s'", table_path, starting_timestamp)
    reader = (
        spark.read
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingTimestamp", starting_timestamp)
    )
    if ending_timestamp is not None:
        reader = reader.option("endingTimestamp", ending_timestamp)

    return reader.load(table_path)


def read_cdf_stream(
    spark: SparkSession,
    table_path: str,
    starting_version: int = 0
) -> DataFrame:
    """
    Read Change Data Feed as a streaming DataFrame for Structured Streaming consumers.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    starting_version : int
        Starting version stream point.

    Returns
    -------
    DataFrame
        Streaming DataFrame emitting change events.
    """
    logger.info("Creating CDF streaming reader for '%s' starting at version %d", table_path, starting_version)
    return (
        spark.readStream
        .format("delta")
        .option("readChangeFeed", "true")
        .option("startingVersion", starting_version)
        .load(table_path)
    )
