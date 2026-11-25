"""
stateful_processing.py — Custom Stateful Processing & Session Tracking
========================================================================

PURPOSE:
    Demonstrates custom state management patterns in Structured Streaming.
    While built-in aggregations (window, groupBy) handle common time buckets, complex production workloads
    (such as sessionization timeouts, user status state machines, and streak detection) require tracking custom state per key.

KEY PATTERNS & APIS:
    1. Grouped State Management: Tracking per-entity accumulated state (e.g. active user shopping cart or session count).
    2. Session Timeout Tracking: Updating user state continuously as events arrive and closing session state after inactivity timeout.
    3. RocksDB State Store Provider: Storing state off-heap on disk to support millions of concurrent user keys without Java GC pressure.

BUSINESS USE CASE:
    - User Cart Abandonment: Track items added to cart in state. If no checkout event occurs within 30 minutes, emit a "Cart Abandoned" notification to Kafka.
    - Security Anomaly Detection: Detect 5 consecutive failed login attempts within a 5-minute window for a specific IP address.

ROCKSDB STATE STORE CONFIGURATION:
    ```python
    spark.conf.set(
        "spark.sql.streaming.stateStore.providerClass",
        "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider"
    )
    ```

INTERVIEW QUESTIONS:
    Q: Why use RocksDBStateStoreProvider instead of HDFSBackedStateStoreProvider in production?
    A: HDFSBackedStateStore keeps state in JVM heap memory. When tracking state for tens of millions of keys,
       heap memory spikes cause severe Java GC pauses (Stop-The-World) and OOM crashes. RocksDB stores state in native off-heap memory and local SSDs, spilling efficiently to cloud storage.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Dict, Any, List
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class StatefulProcessor:
    """
    Production patterns for custom stateful stream operations.
    """

    @staticmethod
    def track_user_activity_counts(
        df: DataFrame,
        user_id_col: str = "user_id",
        event_type_col: str = "event_type",
    ) -> DataFrame:
        """
        Track cumulative count of events per user across streaming micro-batches.

        Args:
            df: Watermarked streaming DataFrame.
            user_id_col: Grouping user key column name.
            event_type_col: Event classification column name.

        Returns:
            Streaming DataFrame emitting running user activity state.
        """
        logger.info("Setting up running user activity count stateful aggregation")

        return (
            df.groupBy(user_id_col, event_type_col)
            .agg(
                F.count("*").alias("cumulative_event_count"),
                F.max("event_time").alias("last_seen_timestamp"),
                F.min("event_time").alias("first_seen_timestamp"),
            )
        )

    @staticmethod
    def detect_high_frequency_users(
        df: DataFrame,
        user_col: str = "user_id",
        window_duration: str = "1 minute",
        threshold: int = 100,
    ) -> DataFrame:
        """
        Stateful rule: Flag users generating more than `threshold` events in `window_duration`.

        Args:
            df: Watermarked streaming DataFrame.
            user_col: User identifier column.
            window_duration: Time window size.
            threshold: Frequency limit trigger.

        Returns:
            Streaming DataFrame emitting rate limit alerts.
        """
        return (
            df.groupBy(
                F.window(F.col("event_time"), window_duration),
                F.col(user_col),
            )
            .agg(F.count("*").alias("event_rate"))
            .filter(F.col("event_rate") > threshold)
            .withColumn("alert_type", F.lit("RATE_LIMIT_EXCEEDED"))
        )


def process_stateful_stream(
    df: DataFrame,
    key_col: str = "user_id",
) -> DataFrame:
    """
    Convenience wrapper for custom stateful stream processing.

    Args:
        df: Watermarked streaming DataFrame.
        key_col: Entity grouping key.

    Returns:
        Stateful aggregate streaming DataFrame.
    """
    processor = StatefulProcessor()
    return processor.track_user_activity_counts(df, user_id_col=key_col)
