"""
Module: partitioning.py
=======================
Delta table partitioning strategies, partition pruning, and dynamic/selective partition overwrites.

Business Use Case:
    Partitioning divides Delta Lake dataset files into distinct physical subdirectories on object storage
    based on partition column values (e.g. `/year=2026/month=03/`).
    Queries with filters matching partition columns can prune 99%+ of files before reading, saving time and cost.

Rules for Partitioning:
    - High Volume Threshold: Only partition tables larger than 1 TB. Small tables (< 100 GB) suffer from over-partitioning.
    - Low Cardinality: Partition columns should have low unique value counts (< 10,000 distinct values).
      Good: date, month, region, country. Bad: timestamp, user_id, uuid.
    - Over-partitioning anti-pattern: Having millions of tiny files in thousands of subdirectories. Use Z-Ordering instead.

Key Capabilities:
    1. Creating partitioned Delta tables (`.partitionBy()`).
    2. Selective partition overwrites using `replaceWhere` option.
    3. Partition pruning analysis.

Interview Questions:
    Q: What is the `replaceWhere` option in Delta Lake?
    A: It allows atomic overwrites of specific partitions matching a predicate (e.g. `replaceWhere => "date = '2026-03-01'"`).
       If any written row violates the `replaceWhere` condition, Delta throws an error, ensuring safe partition replacements.

    Q: When should you use Z-Ordering instead of Partitioning?
    A: Use Partitioning for low-cardinality values used in coarse-grained filters (e.g., date).
       Use Z-Ordering for high-cardinality columns (e.g., customer_id, product_id) where subdirectories would create small file issues.
"""

import logging
from typing import List, Optional
from pyspark.sql import SparkSession, DataFrame

logger = logging.getLogger(__name__)


def write_partitioned_delta_table(
    df: DataFrame,
    table_path: str,
    partition_cols: List[str],
    mode: str = "append"
) -> None:
    """
    Write DataFrame to Delta format partitioned by specified columns.

    Parameters
    ----------
    df : DataFrame
        DataFrame to write.
    table_path : str
        Target table file system path.
    partition_cols : List[str]
        Column names to partition by.
    mode : str
        Write mode ('append', 'overwrite').
    """
    logger.info("Writing partitioned Delta table at '%s' by %s with mode='%s'", table_path, partition_cols, mode)
    (
        df.write
        .format("delta")
        .mode(mode)
        .partitionBy(*partition_cols)
        .save(table_path)
    )
    logger.info("Partitioned write finished")


def selective_partition_overwrite(
    df: DataFrame,
    table_path: str,
    replace_where_expr: str
) -> None:
    """
    Atomically overwrite data in specific partitions matching a condition using replaceWhere.

    Parameters
    ----------
    df : DataFrame
        Source DataFrame containing replacement partition data.
    table_path : str
        Target Delta table path.
    replace_where_expr : str
        SQL filter expression for partition predicate (e.g. "event_date = '2026-03-01'").
    """
    logger.info("Overwriting partition in '%s' matching condition: '%s'", table_path, replace_where_expr)
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", replace_where_expr)
        .save(table_path)
    )
    logger.info("Selective partition overwrite succeeded")


def read_partitioned_delta_table(
    spark: SparkSession,
    table_path: str,
    partition_filter: Optional[str] = None
) -> DataFrame:
    """
    Read Delta table with optional partition filter to leverage partition pruning.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    partition_filter : str, optional
        Filter clause to apply (e.g. "year = 2026 AND month = 3").

    Returns
    -------
    DataFrame
        Filtered DataFrame.
    """
    logger.info("Reading partitioned table from '%s'", table_path)
    df = spark.read.format("delta").load(table_path)
    if partition_filter:
        df = df.filter(partition_filter)
    return df
