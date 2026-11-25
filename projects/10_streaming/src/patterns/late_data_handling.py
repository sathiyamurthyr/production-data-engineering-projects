"""
late_data_handling.py — Late-Arriving Data and Watermarking Strategies
========================================================================

PURPOSE:
    Demonstrates patterns for handling late, out-of-order, or severely delayed streaming events.
    In real-world networks (mobile devices losing connectivity, batch uploads from IoT sensors),
    events arrive out of sequence.
    This module provides watermarking strategies, side-outputs for severely delayed data (Dead Letter Queue),
    and output mode selection logic.

CONCEPTUAL UNDERSTANDING:
    - Event Time: Time when the event actually occurred on the client/device (e.g. `event_timestamp`).
    - Processing Time: Time when Spark processes the micro-batch (e.g. `current_timestamp()`).
    - Watermark: A threshold trailing the maximum event time seen so far:
      `Watermark = max(EventTime) - Delay`
      Events with `EventTime < Watermark` are defined as "Late Data".

HANDLING STRATEGIES:
    1. Watermarked State Eviction: In windowed aggregations, late data within watermark window is included; data older than watermark is dropped from state.
    2. Dead Letter Side-Routing: In `foreachBatch`, isolate records where `event_time < current_watermark` and divert them to a `late_events_dlq` Delta table for auditing.

INTERVIEW QUESTIONS:
    Q: What happens if an event arrives after the watermark has passed?
    A: In stateful stream operations (windowed aggregations, stream-stream joins, dropDuplicates),
       Spark automatically drops the record. It is neither included in state nor emitted in the result set.

    Q: How does Spark determine the current watermark value across micro-batches?
    A: At the end of micro-batch N, Spark calculates `max(event_time)` across all rows in batch N.
       The watermark for micro-batch N+1 is set to `max(event_time) - delay_threshold`.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Tuple
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class LateDataHandler:
    """
    Production late-data routing and watermarking strategies.
    """

    @staticmethod
    def apply_watermark(
        df: DataFrame,
        time_col: str = "event_time",
        delay_threshold: str = "15 minutes",
    ) -> DataFrame:
        """
        Apply event-time watermark to streaming DataFrame.

        Args:
            df: Input streaming DataFrame.
            time_col: Column containing TimestampType event times.
            delay_threshold: Late data tolerance duration string (e.g. "15 minutes", "1 hour").

        Returns:
            Watermarked streaming DataFrame.
        """
        logger.info("Applying watermark on column '%s' with threshold '%s'", time_col, delay_threshold)
        return df.withWatermark(time_col, delay_threshold)

    @staticmethod
    def filter_and_route_late_records(
        df: DataFrame,
        time_col: str = "event_time",
        max_allowed_delay_minutes: int = 60,
    ) -> Tuple[DataFrame, DataFrame]:
        """
        Split a batch/micro-batch DataFrame into valid records and severely delayed records (DLQ).

        Note: Designed for execution inside `foreachBatch` micro-batch handler.

        Args:
            df: Micro-batch DataFrame.
            time_col: Event timestamp column.
            max_allowed_delay_minutes: Cutoff threshold in minutes against ingestion time.

        Returns:
            Tuple of (valid_events_df, late_events_dlq_df).
        """
        cutoff_expr = F.current_timestamp() - F.expr(f"INTERVAL {max_allowed_delay_minutes} MINUTES")

        valid_df = df.filter(F.col(time_col) >= cutoff_expr)
        late_dlq_df = df.filter(F.col(time_col) < cutoff_expr).withColumn(
            "dlq_reason", F.lit(f"Event timestamp older than {max_allowed_delay_minutes} minute threshold")
        )

        return valid_df, late_dlq_df


def configure_late_data_pipeline(
    df: DataFrame,
    time_col: str = "event_time",
    delay: str = "30 minutes",
) -> DataFrame:
    """
    Convenience function to apply watermark to a streaming pipeline.

    Args:
        df: Streaming DataFrame.
        time_col: Event timestamp column.
        delay: Watermark delay string.

    Returns:
        Watermarked streaming DataFrame.
    """
    return LateDataHandler.apply_watermark(df, time_col=time_col, delay_threshold=delay)
