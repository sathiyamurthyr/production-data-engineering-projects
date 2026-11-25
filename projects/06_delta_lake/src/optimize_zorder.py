"""
Module: optimize_zorder.py
==========================
Compacting small files and multi-dimensional clustering via OPTIMIZE and Z-ORDER BY.

Business Use Case:
    Streaming data ingestion (Kafka, Kinesis, Auto Loader) writes small Parquet files continuously
    (the "Small File Problem"). Tens of thousands of 1MB files create severe metadata overhead,
    slow directory listings, and degrade Spark read query performance by up to 10x–100x.
    OPTIMIZE merges small files into target 128MB–1GB files.
    Z-ORDER BY spatially clusters records along multi-dimensional space curves, allowing Spark's
    data skipping mechanism (file-level min/max stats) to prune irrelevant Parquet files when filtering
    by high-cardinality columns (e.g., user_id, device_id).

Partitioning vs. Z-Ordering:
    - Partitioning: Best for low-cardinality columns (e.g. year, month, region). Creates separate subdirectories.
    - Z-Ordering: Best for high-cardinality columns (e.g. user_id, event_id, customer_id). Co-locates data within files.

Interview Questions:
    Q: What is Z-Ordering and how does it enable data skipping in Delta Lake?
    A: Z-Ordering maps multi-dimensional data into 1D space using Morton space-filling curves.
       It organizes data within files such that similar values across Z-Ordered columns are stored in the same file.
       Delta records min/max stats for each column per file; queries filtering on Z-Ordered columns skip reading files
       whose [min, max] range does not intersect the filter predicate.

    Q: Can you Z-Order by 20 columns?
    A: No. Z-Ordering effectiveness decreases exponentially with each added column (curse of dimensionality).
       Best practice: Limit Z-Order to 1 to 4 columns maximum that are frequently used in WHERE filters or JOIN keys.

    Q: Does OPTIMIZE rewrite existing data files?
    A: Yes, OPTIMIZE reads selected small Parquet files, rewrites them into larger target files, and atomically updates log commits.
       Old files are marked as removed (retained for time travel) and physically deleted when VACUUM is run.
"""

import logging
from typing import List, Optional, Dict, Any
from pyspark.sql import SparkSession
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


def run_bin_packing_optimize(
    spark: SparkSession,
    table_path: str,
    where_clause: Optional[str] = None
) -> None:
    """
    Run OPTIMIZE without Z-Ordering (pure file compaction / bin-packing).

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path or catalog table name.
    where_clause : str, optional
        Partition filter expression (e.g. "date >= '2026-03-01'").
        Compacts only files within specified partitions to save compute.
    """
    logger.info("Executing bin-packing OPTIMIZE on table '%s'", table_path)
    dt = DeltaTable.forPath(spark, table_path)
    opt_builder = dt.optimize()

    if where_clause:
        opt_builder = opt_builder.where(where_clause)

    metrics_df = opt_builder.executeCompaction()
    metrics = metrics_df.collect()[0].asDict()
    logger.info(
        "Compaction metrics for '%s': added %d files, removed %d files, bytes added: %d",
        table_path,
        metrics.get("numFilesAdded", 0),
        metrics.get("numFilesRemoved", 0),
        metrics.get("numBytesAdded", 0),
    )


def run_zorder_optimize(
    spark: SparkSession,
    table_path: str,
    zorder_cols: List[str],
    where_clause: Optional[str] = None
) -> None:
    """
    Run OPTIMIZE Z-ORDER BY to cluster data along specified dimensions.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    zorder_cols : List[str]
        High-cardinality columns to Z-Order by (1–4 recommended).
    where_clause : str, optional
        Partition filter to optimize specific partitions.
    """
    if not zorder_cols:
        raise ValueError("zorder_cols must contain at least one column name.")

    logger.info("Executing OPTIMIZE Z-ORDER BY %s on '%s'", zorder_cols, table_path)
    dt = DeltaTable.forPath(spark, table_path)
    opt_builder = dt.optimize()

    if where_clause:
        opt_builder = opt_builder.where(where_clause)

    metrics_df = opt_builder.executeZOrderBy(*zorder_cols)
    metrics = metrics_df.collect()[0].asDict()
    logger.info(
        "Z-Order metrics for '%s': added %d files, removed %d files",
        table_path,
        metrics.get("numFilesAdded", 0),
        metrics.get("numFilesRemoved", 0)
    )


def execute_sql_optimize(
    spark: SparkSession,
    table_identifier: str,
    zorder_cols: Optional[List[str]] = None,
    partition_filter: Optional[str] = None
) -> None:
    """
    Execute OPTIMIZE using raw SQL syntax.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_identifier : str
        Table name or delta path.
    zorder_cols : List[str], optional
        Columns to Z-Order by.
    partition_filter : str, optional
        Partition predicate (e.g. "date = '2026-03-01'").
    """
    sql_stmt = f"OPTIMIZE {table_identifier}"
    if partition_filter:
        sql_stmt += f" WHERE {partition_filter}"

    if zorder_cols:
        cols_str = ", ".join(zorder_cols)
        sql_stmt += f" ZORDER BY ({cols_str})"

    logger.info("Executing SQL: %s", sql_stmt)
    spark.sql(sql_stmt)
