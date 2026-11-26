"""
optimizations.py
================
PySpark performance optimization patterns: Caching, Partitioning, Broadcast variables,
Accumulators, and Adaptive Query Execution (AQE).

Business Use Case:
    Speeding up high-throughput pipelines, eliminating out-of-memory (OOM) errors,
    preventing small-file problems, and reducing cloud execution costs.

Key Optimization Techniques:
    - Broadcast Variables: Send read-only lookup table to all executors once (avoids task shipping overhead).
    - Accumulators: Write-only distributed counters for tracking record metrics / corrupt records.
    - cache() / persist(): Save intermediate DataFrame results in memory/disk to avoid re-computation.
    - repartition() vs coalesce():
        * repartition(N): Full shuffle across cluster to balance partitions (increase or decrease count).
        * coalesce(N): Decreases partition count by merging adjacent partitions on existing nodes (NO SHUFFLE).

Interview Questions:
    Q: Difference between cache() and persist()?
    A: cache() is a shorthand for `persist(StorageLevel.MEMORY_AND_DISK_DESER)` (or MEMORY_ONLY in PySpark).
       persist() allows specifying storage levels like `MEMORY_ONLY`, `MEMORY_AND_DISK`, `MEMORY_ONLY_SER`, or `DISK_ONLY`.

    Q: When should you use repartition() vs coalesce()?
    A: Use `repartition()` when increasing partition count or re-balancing skewed data across executors.
       Use `coalesce()` when reducing partition count before writing to disk to avoid small files, saving network shuffle cost.

    Q: What are the three main features of Adaptive Query Execution (AQE) in Spark 3.x?
    A: 1) Dynamically coalescing shuffle partitions.
       2) Dynamically converting sort-merge join to broadcast hash join.
       3) Dynamically optimizing skew joins.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark import StorageLevel

logger = logging.getLogger(__name__)


def create_broadcast_dictionary(spark: SparkSession, lookup_dict: Dict[Any, Any]):
    """
    Create a Spark Broadcast Variable for a small lookup dictionary.

    Args:
        spark: Active SparkSession.
        lookup_dict: Python dictionary to broadcast across workers.

    Returns:
        Broadcast variable wrapper.
    """
    logger.info("Broadcasting lookup dictionary with %d items", len(lookup_dict))
    return spark.sparkContext.broadcast(lookup_dict)


def optimize_dataframe_partitions(
    df: DataFrame,
    target_partitions: int,
    use_shuffle: bool = False,
) -> DataFrame:
    """
    Adjust the partition count of a DataFrame efficiently.

    Args:
        df: Input DataFrame.
        target_partitions: Target partition count.
        use_shuffle: If True, uses repartition() (full shuffle).
                     If False, uses coalesce() (no shuffle, decrease only).

    Returns:
        Re-partitioned DataFrame.
    """
    current_partitions = df.rdd.getNumPartitions()
    logger.info(
        "Adjusting partitions from %d to %d (shuffle=%s)",
        current_partitions, target_partitions, use_shuffle
    )

    if use_shuffle or target_partitions > current_partitions:
        return df.repartition(target_partitions)
    else:
        return df.coalesce(target_partitions)


def cache_intermediate_result(
    df: DataFrame,
    storage_level: StorageLevel = StorageLevel.MEMORY_AND_DISK,
) -> DataFrame:
    """
    Persist DataFrame in memory/disk storage to prevent re-computation in multiple downstream DAG paths.

    Args:
        df: DataFrame to cache.
        storage_level: PySpark StorageLevel configuration.

    Returns:
        Persisted DataFrame.
    """
    logger.info("Caching DataFrame with storage level: %s", storage_level)
    return df.persist(storage_level)


def uncache_dataframe(df: DataFrame) -> None:
    """
    Release memory resources occupied by a cached DataFrame.
    """
    logger.info("Uncaching DataFrame")
    df.unpersist()


def configure_aqe_defaults(spark: SparkSession) -> None:
    """
    Enable Adaptive Query Execution (AQE) settings on an existing SparkSession.
    """
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
    logger.info("Configured production AQE settings on SparkSession")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("OptimizationDemo")
    configure_aqe_defaults(spark)

    sales = create_sample_sales(spark)
    print(f"Initial partition count: {sales.rdd.getNumPartitions()}")

    repartitioned = optimize_dataframe_partitions(sales, target_partitions=4, use_shuffle=True)
    print(f"After repartition(4): {repartitioned.rdd.getNumPartitions()}")

    coalesced = optimize_dataframe_partitions(repartitioned, target_partitions=1, use_shuffle=False)
    print(f"After coalesce(1): {coalesced.rdd.getNumPartitions()}")

    cached = cache_intermediate_result(coalesced)
    print(f"Cached row count: {cached.count()}")
    uncache_dataframe(cached)

    spark.stop()
