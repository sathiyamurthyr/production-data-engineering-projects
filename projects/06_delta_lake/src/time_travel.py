"""
Module: time_travel.py
======================
Delta Lake Time Travel queries, history tracking, table restore, and version diffing.

Business Use Case:
    In traditional data warehouses or raw object stores, once data is updated or overwritten,
    the previous state is lost forever (unless expensive backups are taken).
    Delta Lake maintains an immutable transaction log (_delta_log) that tracks every
    commit with pointers to Parquet files added and removed.
    This enables reproducible machine learning models, regulatory compliance auditing,
    disaster recovery rollbacks, and debugging accidental data corruption.

Key Capabilities:
    1. Query historical snapshots via `VERSION AS OF` or `TIMESTAMP AS OF`.
    2. Inspect detailed audit logs using `DESCRIBE HISTORY` / `DeltaTable.history()`.
    3. Rollback table state safely with `RESTORE TABLE ...`.
    4. Compute point-in-time diffs between versions for data reconciliation.

Interview Questions:
    Q: How does Delta Lake implement time travel without copying data?
    A: Delta uses write-ahead logging (transaction log). When data is updated or deleted,
       old Parquet files are marked as removed in the log (remove action), but the physical
       files are retained on disk. A time travel query reconstructs the active file list
       at a given version/timestamp by replaying log commits up to that point.

    Q: What happens if you try to time travel past the VACUUM retention period?
    A: It raises an `AnalysisException` (file not found). VACUUM permanently deletes
       Parquet files that were marked as removed longer ago than the retention threshold.

    Q: How does time travel work with timestamp queries when there is no commit at that exact second?
    A: Delta locates the latest commit made BEFORE or AT the specified timestamp.
"""

import logging
from typing import Dict, List, Any, Optional
from pyspark.sql import SparkSession, DataFrame
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


def read_version_as_of(spark: SparkSession, table_path: str, version: int) -> DataFrame:
    """
    Read a Delta table snapshot as of a specific version number.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        File system path or catalog table name.
    version : int
        Zero-based version number.

    Returns
    -------
    DataFrame
        Data snapshot at the specified version.
    """
    logger.info("Reading Delta table at '%s' as of version %d", table_path, version)
    return (
        spark.read
        .format("delta")
        .option("versionAsOf", version)
        .load(table_path)
    )


def read_timestamp_as_of(spark: SparkSession, table_path: str, timestamp_str: str) -> DataFrame:
    """
    Read a Delta table snapshot as of a specific timestamp.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        File system path or catalog table name.
    timestamp_str : str
        Timestamp string (e.g. '2026-03-01 10:00:00' or '2026-03-01T10:00:00Z').

    Returns
    -------
    DataFrame
        Data snapshot at the specified timestamp.
    """
    logger.info("Reading Delta table at '%s' as of timestamp '%s'", table_path, timestamp_str)
    return (
        spark.read
        .format("delta")
        .option("timestampAsOf", timestamp_str)
        .load(table_path)
    )


def get_table_history(spark: SparkSession, table_path: str, limit: Optional[int] = None) -> DataFrame:
    """
    Retrieve transaction history audit records for a Delta table.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        File system path or catalog table name.
    limit : int, optional
        Maximum number of recent history commits to return.

    Returns
    -------
    DataFrame
        DataFrame containing history fields: version, timestamp, userId, userName,
        operation, operationParameters, job, notebook, clusterId, readVersion, etc.
    """
    logger.info("Retrieving transaction history for '%s'", table_path)
    delta_table = DeltaTable.forPath(spark, table_path)
    history_df = delta_table.history()
    if limit:
        history_df = history_df.limit(limit)
    return history_df


def restore_to_version(spark: SparkSession, table_path: str, target_version: int) -> DataFrame:
    """
    Restore a Delta table to a previous version.
    This creates a NEW commit in the transaction log that reverts the table state.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        File system path to the Delta table.
    target_version : int
        Version number to revert to.

    Returns
    -------
    DataFrame
        Metrics and summary of the restore operation.
    """
    logger.info("Restoring Delta table '%s' to version %d", table_path, target_version)
    delta_table = DeltaTable.forPath(spark, table_path)
    return delta_table.restoreToVersion(target_version)


def restore_to_timestamp(spark: SparkSession, table_path: str, timestamp_str: str) -> DataFrame:
    """
    Restore a Delta table to a specific timestamp.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        File system path to the Delta table.
    timestamp_str : str
        Timestamp string to revert to.

    Returns
    -------
    DataFrame
        Metrics and summary of the restore operation.
    """
    logger.info("Restoring Delta table '%s' to timestamp '%s'", table_path, timestamp_str)
    delta_table = DeltaTable.forPath(spark, table_path)
    return delta_table.restoreToTimestamp(timestamp_str)


def compute_version_diff(
    spark: SparkSession,
    table_path: str,
    v_old: int,
    v_new: int,
    key_cols: List[str]
) -> Dict[str, DataFrame]:
    """
    Compute inserted, deleted, and modified rows between two versions.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table path.
    v_old : int
        Older version number.
    v_new : int
        Newer version number.
    key_cols : List[str]
        Primary key columns to join on.

    Returns
    -------
    Dict[str, DataFrame]
        Dictionary with keys 'added', 'deleted', and 'modified' DataFrames.
    """
    df_old = read_version_as_of(spark, table_path, v_old)
    df_new = read_version_as_of(spark, table_path, v_new)

    # Added records (in new, not in old)
    added = df_new.join(df_old, on=key_cols, how="left_anti")

    # Deleted records (in old, not in new)
    deleted = df_old.join(df_new, on=key_cols, how="left_anti")

    # Common keys (in both)
    common_old = df_old.join(df_new.select(key_cols), on=key_cols, how="inner")
    common_new = df_new.join(df_old.select(key_cols), on=key_cols, how="inner")
    modified = common_new.subtract(common_old)

    return {
        "added": added,
        "deleted": deleted,
        "modified": modified,
    }
