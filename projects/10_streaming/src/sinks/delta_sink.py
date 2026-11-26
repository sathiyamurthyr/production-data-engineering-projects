"""
delta_sink.py — Streaming Delta Lake Output Sink
=================================================

PURPOSE:
    Provides production-grade writing functionality for PySpark Structured Streaming
    into Delta Lake tables. Delta Lake provides ACID transactions, schema enforcement,
    schema evolution, time travel, and unified streaming + batch storage.

BUSINESS USE CASE:
    Modern lakehouse architectures use Medallion architecture (Bronze -> Silver -> Gold):
    1. Bronze Layer: Raw Kafka/File streams ingested continuously in Append mode into raw Delta tables.
    2. Silver Layer: Cleaned, deduplicated, and enriched streaming tables written via Delta Lake Append or MERGE (upserts).
    3. Gold Layer: Aggregated real-time metrics updated continuously using Complete or Update mode.

PRODUCTION SINK CONFIGURATION:
    - Checkpoint Location: CRITICAL for failure recovery and offset persistence.
    - Output Modes:
      * `append` : Append new rows only. Default mode for Bronze & Silver streams.
      * `complete` : Overwrite entire table on every batch. Used for aggregated Gold tables.
      * `update` : Output only changed/updated rows.
    - Triggers:
      * `processingTime="10 seconds"` : Micro-batch trigger every 10s.
      * `availableNow=True` : Process all available backlog then gracefully terminate (cost-effective serverless ETL).

INTERVIEW QUESTIONS:
    Q: Why is Delta Lake the preferred sink for Spark Structured Streaming?
    A: Delta Lake maintains an ACID transaction log (`_delta_log/`). When a streaming micro-batch
       writes files, Delta commits them atomically. If a worker crashes mid-write, Delta's transaction log
       ignores orphan uncommitted Parquet files, providing true end-to-end exactly-once write semantics.

    Q: How do you perform upserts (MERGE) from a streaming DataFrame into a Delta table?
    A: Use `writeStream.foreachBatch(upsert_func)`. Inside `upsert_func`, perform a standard Delta Table `merge()`
       operation using the micro-batch DataFrame as the source.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class DeltaStreamSink:
    """
    Production streaming sink for writing DataFrames to Delta Lake.
    """

    def __init__(self, checkpoint_base_path: str = "/tmp/delta_checkpoints") -> None:
        """
        Initialise Delta streaming sink.

        Args:
            checkpoint_base_path: Base directory for storing stream query checkpoints.
        """
        self.checkpoint_base_path = checkpoint_base_path

    def write_to_delta(
        self,
        df: DataFrame,
        output_path: str,
        query_name: str,
        output_mode: str = "append",
        trigger_interval: str = "10 seconds",
        partition_cols: Optional[List[str]] = None,
        merge_schema: bool = True,
        checkpoint_path: Optional[str] = None,
    ) -> StreamingQuery:
        """
        Write streaming DataFrame to Delta Lake table.

        Args:
            df: Streaming DataFrame.
            output_path: Delta Lake storage path or table location.
            query_name: Unique streaming query identifier.
            output_mode: "append", "complete", or "update".
            trigger_interval: Trigger timing (e.g., "10 seconds", "1 minute", "once", "availableNow").
            partition_cols: Columns for Delta table partitioning (e.g. ["processing_date"]).
            merge_schema: If True, enables schema evolution (`mergeSchema=true`).
            checkpoint_path: Custom checkpoint directory. If None, derived from `checkpoint_base_path/query_name`.

        Returns:
            Active StreamingQuery object.
        """
        cp_path = checkpoint_path or f"{self.checkpoint_base_path}/{query_name}"
        logger.info(
            "Starting Delta stream query '%s': path=%s, mode=%s, checkpoint=%s",
            query_name,
            output_path,
            output_mode,
            cp_path,
        )

        writer = (
            df.writeStream
            .format("delta")
            .outputMode(output_mode)
            .queryName(query_name)
            .option("checkpointLocation", cp_path)
            .option("mergeSchema", str(merge_schema).lower())
        )

        # Apply Partitioning
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)

        # Apply Trigger
        if trigger_interval.lower() == "once":
            writer = writer.trigger(once=True)
        elif trigger_interval.lower() == "availablenow":
            writer = writer.trigger(availableNow=True)
        else:
            writer = writer.trigger(processingTime=trigger_interval)

        return writer.start(output_path)

    def write_upsert_to_delta(
        self,
        df: DataFrame,
        output_path: str,
        query_name: str,
        primary_key: str,
        trigger_interval: str = "10 seconds",
        checkpoint_path: Optional[str] = None,
    ) -> StreamingQuery:
        """
        Write streaming DataFrame using MERGE (upsert) via foreachBatch into a Delta Lake table.

        Args:
            df: Streaming DataFrame.
            output_path: Target Delta Lake table path.
            query_name: Unique stream query identifier.
            primary_key: Matching key for merge condition (e.g., "user_id" or "event_id").
            trigger_interval: Trigger timing interval.
            checkpoint_path: Custom checkpoint directory.

        Returns:
            Active StreamingQuery instance.
        """
        from delta.tables import DeltaTable

        cp_path = checkpoint_path or f"{self.checkpoint_base_path}/{query_name}_upsert"

        def _upsert_batch(batch_df: DataFrame, batch_id: int):
            logger.info("Executing upsert for micro-batch %d (%d records)", batch_id, batch_df.count())
            if batch_df.isEmpty():
                return

            spark = batch_df.sparkSession

            # Initialize Delta table if it doesn't exist
            if not DeltaTable.isDeltaTable(spark, output_path):
                (
                    batch_df.write
                    .format("delta")
                    .mode("overwrite")
                    .save(output_path)
                )
                return

            delta_table = DeltaTable.forPath(spark, output_path)

            (
                delta_table.alias("target")
                .merge(
                    batch_df.alias("source"),
                    f"target.{primary_key} = source.{primary_key}",
                )
                .whenMatchedUpdateAll()
                .whenNotMatchedInsertAll()
                .execute()
            )

        writer = (
            df.writeStream
            .format("delta")
            .outputMode("update")
            .queryName(query_name)
            .option("checkpointLocation", cp_path)
            .foreachBatch(_upsert_batch)
        )

        if trigger_interval.lower() == "availablenow":
            writer = writer.trigger(availableNow=True)
        else:
            writer = writer.trigger(processingTime=trigger_interval)

        return writer.start()


def write_to_delta_table(
    df: DataFrame,
    target_path: str,
    query_name: str,
    checkpoint_dir: str = "/tmp/checkpoints",
    output_mode: str = "append",
) -> StreamingQuery:
    """
    Convenience wrapper function for streaming to Delta Lake.

    Args:
        df: Input streaming DataFrame.
        target_path: Storage destination path.
        query_name: Streaming query name.
        checkpoint_dir: Checkpoint directory.
        output_mode: Stream output mode.

    Returns:
        Active StreamingQuery instance.
    """
    sink = DeltaStreamSink(checkpoint_base_path=checkpoint_dir)
    return sink.write_to_delta(
        df,
        output_path=target_path,
        query_name=query_name,
        output_mode=output_mode,
        checkpoint_path=f"{checkpoint_dir}/{query_name}",
    )
