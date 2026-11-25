"""
Module: vacuuming.py
===================
Delta Lake VACUUM command management, retention policies, dry-runs, and cleanup.

Business Use Case:
    Over time, UPDATE, DELETE, MERGE, and OPTIMIZE operations write new Parquet files
    and mark old files as tombstoned (removed) in the Delta transaction log.
    If left uncleaned, old Parquet files accumulate on S3/ADLS/GCS, generating massive storage costs.
    VACUUM permanently purges physical data files that have been tombstoned longer than the retention threshold.

Safety & Retention Policies:
    - Default Retention: 7 days (168 hours). Ensures long-running reader transactions don't crash with FileNotFoundError.
    - Zero Retention Override: Setting retention to 0 hours requires disabling safety check:
      `spark.databricks.delta.vacuum.parallelDelete.enabled` / `spark.sql("SET spark.databricks.delta.vacuum.parallelDelete.enabled = true")`
      (or setting `spark.databricks.delta.vacuum.logging.enabled`).

Interview Questions:
    Q: What happens to Time Travel after running VACUUM RETAIN 0 HOURS?
    A: You can no longer query history past the vacuum threshold! Any time travel query attempting to read
       purged Parquet files will fail with a FileNotFoundError / AnalysisException.

    Q: Why does Delta Lake enforce a 7-day retention safety check by default?
    A: To protect concurrent readers. If a streaming query or batch query opened a Parquet file 1 hour ago
       and VACUUM deleted it while the query was scanning, the query would fail.

    Q: How do you preview files that VACUUM will delete without actually deleting them?
    A: Use the DRY RUN clause: `VACUUM table_name RETAIN 168 HOURS DRY RUN` or `delta_table.vacuum(168)` with dry-run mode.
"""

import logging
from typing import List, Optional
from pyspark.sql import SparkSession, DataFrame
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


def vacuum_delta_table(
    spark: SparkSession,
    table_path: str,
    retention_hours: float = 168.0,
    dry_run: bool = False,
) -> Optional[DataFrame]:
    """
    Run VACUUM on a Delta table to clean up tombstoned files.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    retention_hours : float
        Hours threshold for file retention (default 168.0 hours = 7 days).
    dry_run : bool
        If True, previews files to be deleted without deleting them.

    Returns
    -------
    Optional[DataFrame]
        DataFrame listing deleted/preview files if dry_run=True, else None.
    """
    logger.info(
        "Running VACUUM on '%s' with retention=%f hours (dry_run=%s)",
        table_path, retention_hours, dry_run
    )
    dt = DeltaTable.forPath(spark, table_path)

    if dry_run:
        # Perform dry run using SQL to get DataFrame of candidates
        sql_stmt = f"VACUUM delta.`{table_path}` RETAIN {retention_hours} HOURS DRY RUN"
        return spark.sql(sql_stmt)
    else:
        dt.vacuum(retention_hours)
        logger.info("VACUUM completed successfully for '%s'", table_path)
        return None


def enable_unsafe_vacuum(spark: SparkSession) -> None:
    """
    Disable safety check enforcing retention period >= 168 hours.
    WARNING: Use only in testing or strict maintenance windows!

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    """
    logger.warning("Disabling retention duration check for VACUUM (UNSAFE IN PRODUCTION)")
    spark.conf.set("spark.databricks.delta.vacuum.parallelDelete.enabled", "true")
    spark.conf.set("spark.databricks.delta.vacuum.logging.enabled", "true")


def vacuum_with_zero_retention(spark: SparkSession, table_path: str) -> None:
    """
    Execute VACUUM RETAIN 0 HOURS to clear all unreferenced tombstoned files immediately.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    """
    enable_unsafe_vacuum(spark)
    logger.info("Executing zero-retention VACUUM on '%s'", table_path)
    dt = DeltaTable.forPath(spark, table_path)
    dt.vacuum(0.0)
    logger.info("Zero-retention VACUUM completed")
