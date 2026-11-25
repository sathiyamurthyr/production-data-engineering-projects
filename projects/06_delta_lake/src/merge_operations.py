"""
Module: merge_operations.py
===========================
Delta MERGE INTO statement patterns for Upserts, SCD Type 1, and SCD Type 2 tracking.

Business Use Case:
    Change Data Capture (CDC) feeds from upstream relational databases (PostgreSQL, MySQL, Oracle)
    deliver inserts, updates, and deletes as a continuous stream or incremental batch.
    Traditional data lakes require full table re-writes to apply small row updates.
    Delta Lake's MERGE INTO allows fine-grained, atomic upserts and deletes directly on object storage,
    forming the foundation of Slowly Changing Dimensions (SCD Type 1 and Type 2) in Lakehouses.

Patterns Covered:
    1. SCD Type 1 Upsert: Update existing records in-place, insert new records.
    2. Merge with Deletes: Conditionally delete records based on incoming delete flags.
    3. SCD Type 2 (History Tracking): Expire old versions with end_date/is_current=false and insert new versions with start_date.
    4. Deterministic Merge: Handling duplicate merge keys with pre-deduplication.

Interview Questions:
    Q: What error occurs if a MERGE statement matches multiple target rows for a single source key?
    A: `AnalysisException: Cannot perform MERGE because multiple source rows matched and attempted to modify the same target row.`
       Fix: Always deduplicate the incoming source DataFrame on the join key prior to calling MERGE.

    Q: How does Delta Lake optimize MERGE performance physically?
    A: Delta identifies affected files using file statistics / data skipping, reads candidate Parquet files,
       performs join in Spark memory, writes new Parquet files with updated/inserted rows, and issues a commit log entry.
       Adding partition filters to the ON merge condition significantly improves pruning speed.
"""

import logging
from typing import List, Optional, Dict
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from delta.tables import DeltaTable

logger = logging.getLogger(__name__)


def upsert_scd_type_1(
    spark: SparkSession,
    target_table_path: str,
    updates_df: DataFrame,
    primary_key: str,
    update_cols: Optional[List[str]] = None,
) -> None:
    """
    Perform an SCD Type 1 Upsert (overwrite matching rows, insert new rows).

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    target_table_path : str
        Path to the target Delta table.
    updates_df : DataFrame
        Source DataFrame containing updates/inserts.
    primary_key : str
        Primary key column for joining source and target.
    update_cols : List[str], optional
        List of column names to update. If None, all columns are updated/inserted.
    """
    logger.info("Performing SCD Type 1 Upsert on table at '%s'", target_table_path)
    target_table = DeltaTable.forPath(spark, target_table_path)

    # Ensure source has no duplicate primary keys
    dedup_updates = updates_df.dropDuplicates([primary_key])

    merge_cond = f"target.{primary_key} = source.{primary_key}"

    if update_cols:
        set_dict = {col: f"source.{col}" for col in update_cols}
        (
            target_table.alias("target")
            .merge(dedup_updates.alias("source"), merge_cond)
            .whenMatchedUpdate(set=set_dict)
            .whenNotMatchedInsert(values=set_dict)
            .execute()
        )
    else:
        (
            target_table.alias("target")
            .merge(dedup_updates.alias("source"), merge_cond)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    logger.info("SCD Type 1 Upsert completed successfully")


def merge_with_soft_and_hard_deletes(
    spark: SparkSession,
    target_table_path: str,
    source_df: DataFrame,
    primary_key: str,
    delete_col: str = "is_deleted",
) -> None:
    """
    Merge incoming records, deleting target rows when source delete flag is True.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    target_table_path : str
        Target Delta table path.
    source_df : DataFrame
        Source DataFrame containing updates and delete flags.
    primary_key : str
        Join key column name.
    delete_col : str
        Boolean column indicating deletion status.
    """
    logger.info("Merging source data with deletes into '%s'", target_table_path)
    target_table = DeltaTable.forPath(spark, target_table_path)
    dedup_source = source_df.dropDuplicates([primary_key])

    merge_cond = f"target.{primary_key} = source.{primary_key}"

    (
        target_table.alias("target")
        .merge(dedup_source.alias("source"), merge_cond)
        .whenMatchedDelete(condition=f"source.{delete_col} = true")
        .whenMatchedUpdateAll(condition=f"source.{delete_col} = false")
        .whenNotMatchedInsertAll(condition=f"source.{delete_col} = false")
        .execute()
    )
    logger.info("Merge with deletes completed")


def upsert_scd_type_2(
    spark: SparkSession,
    target_table_path: str,
    updates_df: DataFrame,
    primary_key: str,
    effective_date_col: str = "updated_at"
) -> None:
    """
    Perform an SCD Type 2 merge tracking full history with effective start/end dates
    and an `is_current` boolean flag.

    Target Schema Expectation:
        [primary_key, ..., start_date, end_date, is_current]

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    target_table_path : str
        Target Delta table path.
    updates_df : DataFrame
        Incoming change records.
    primary_key : str
        Primary key column.
    effective_date_col : str
        Timestamp column for change event.
    """
    logger.info("Performing SCD Type 2 merge on '%s'", target_table_path)
    target_table = DeltaTable.forPath(spark, target_table_path)

    # 1. Format incoming updates for SCD2 insertion
    staged_updates = (
        updates_df
        .withColumn("merge_key", F.col(primary_key))
        .withColumn("start_date", F.col(effective_date_col))
        .withColumn("end_date", F.lit(None).cast("timestamp"))
        .withColumn("is_current", F.lit(True))
    )

    # 2. Stage records that will update existing active target rows (null key forces insertion of new current row)
    existing_target = target_table.toDF().filter(F.col("is_current") == True)

    staged_null_keys = (
        staged_updates.join(
            existing_target,
            on=primary_key,
            how="inner"
        )
        .select(staged_updates["*"])
        .withColumn("merge_key", F.lit(None))
    )

    # Union staged new updates with NULL key rows
    final_staged = staged_updates.unionByName(staged_null_keys)

    # 3. Execute MERGE: Expire old active record when matched, insert new active record when not matched
    merge_condition = (
        f"target.{primary_key} = source.merge_key AND target.is_current = true"
    )

    (
        target_table.alias("target")
        .merge(final_staged.alias("source"), merge_condition)
        .whenMatchedUpdate(
            set={
                "end_date": "source.start_date",
                "is_current": "false"
            }
        )
        .whenNotMatchedInsert(
            values={
                primary_key: f"source.{primary_key}",
                "start_date": "source.start_date",
                "end_date": "source.end_date",
                "is_current": "source.is_current"
            }
        )
        .execute()
    )
    logger.info("SCD Type 2 merge completed")
