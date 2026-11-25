"""
deduplication.py — Stream Deduplication for Exactly-Once Processing
====================================================================

PURPOSE:
    Provides real-time event deduplication functionality for streaming DataFrames.
    In distributed real-time systems (Kafka, IoT brokers), network retries and producer
    failures cause duplicate events to arrive at the streaming ingestion layer.
    This module uses `dropDuplicates()` combined with event-time watermarking to drop duplicate
    records dynamically across micro-batches while keeping StateStore size strictly bounded.

BUSINESS USE CASE:
    - Financial Payment Processing: Duplicate transaction IDs must never be processed twice.
    - Clickstream Analytics: Producer network timeouts retry sending event payload; duplicate click IDs distort conversion metrics.

PRODUCTION RULES & WATERMARKS:
    - Deduplication across micro-batches REQUIRES event-time watermarking.
    - If no watermark is supplied, Spark must keep EVERY unique ID in state indefinitely, causing eventual OutOfMemory (OOM) failures.
    - With watermark: `df.withWatermark("event_time", "10 minutes").dropDuplicates(["event_id", "event_time"])`
      Spark automatically drops state entries older than `max(event_time) - 10 minutes`.

INTERVIEW QUESTIONS:
    Q: Why must event_time be included in dropDuplicates columns when watermarks are used?
    A: Spark needs the event timestamp associated with the state entry to determine when
       that entry falls behind the current watermark line and can be safely evicted from state.

    Q: Does dropDuplicates guarantee exactly-once processing when writing to Delta Lake?
    A: dropDuplicates ensures exactly-once within the stream state window. Delta Lake's ACID transaction log
       and idempotency keys complete the end-to-end exactly-once write guarantee across restarts.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame

logger = logging.getLogger(__name__)


class StreamDeduplicator:
    """
    Production stream deduplication utility.
    """

    @staticmethod
    def deduplicate_events(
        df: DataFrame,
        dedup_cols: List[str],
        watermark_col: Optional[str] = "event_time",
        watermark_delay: Optional[str] = "10 minutes",
    ) -> DataFrame:
        """
        Deduplicate streaming DataFrame records using key columns and optional watermark.

        Args:
            df: Input streaming DataFrame.
            dedup_cols: List of column names forming the unique composite natural key (e.g. ["event_id"]).
            watermark_col: Event timestamp column name for state eviction.
            watermark_delay: Watermark delay string (e.g. "10 minutes").

        Returns:
            Deduplicated streaming DataFrame.
        """
        logger.info("Applying stream deduplication on columns: %s", dedup_cols)

        working_df = df

        # Apply watermark if specified and not already applied
        if watermark_col and watermark_delay and watermark_col in working_df.columns:
            # Check if deduplication columns include watermark column
            cols_for_dedup = list(dedup_cols)
            if watermark_col not in cols_for_dedup:
                cols_for_dedup.append(watermark_col)

            working_df = working_df.withWatermark(watermark_col, watermark_delay)
            return working_df.dropDuplicates(cols_for_dedup)
        else:
            # Stateless / single micro-batch deduplication or unbounded state
            return working_df.dropDuplicates(dedup_cols)

    @staticmethod
    def deduplicate_within_batch(
        df: DataFrame,
        primary_key: str = "event_id",
        ordering_col: str = "event_timestamp",
    ) -> DataFrame:
        """
        Deduplicate within micro-batch using window functions (keep newest record).

        Note: Useful inside `foreachBatch` handlers where standard batch Window functions work.

        Args:
            df: Micro-batch DataFrame.
            primary_key: Unique record identifier.
            ordering_col: Column to determine record recency (e.g. timestamp or sequence number).

        Returns:
            Deduplicated batch DataFrame.
        """
        from pyspark.sql.window import Window
        from pyspark.sql import functions as F

        window_spec = Window.partitionBy(primary_key).orderBy(F.col(ordering_col).desc())

        return (
            df.withColumn("_row_num", F.row_number().over(window_spec))
            .filter(F.col("_row_num") == 1)
            .drop("_row_num")
        )


def deduplicate_stream(
    df: DataFrame,
    unique_key: str = "event_id",
    time_col: str = "event_time",
    delay: str = "10 minutes",
) -> DataFrame:
    """
    Convenience wrapper for stream deduplication.

    Args:
        df: Input streaming DataFrame.
        unique_key: Unique identifier.
        time_col: Timestamp column for watermark.
        delay: Watermark delay threshold.

    Returns:
        Deduplicated streaming DataFrame.
    """
    deduplicator = StreamDeduplicator()
    return deduplicator.deduplicate_events(
        df,
        dedup_cols=[unique_key],
        watermark_col=time_col,
        watermark_delay=delay,
    )
