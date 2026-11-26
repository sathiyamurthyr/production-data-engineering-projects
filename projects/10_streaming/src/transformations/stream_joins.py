"""
stream_joins.py — Stream-to-Stream and Stream-to-Static Joins
============================================================

PURPOSE:
    Implements real-time join patterns in PySpark Structured Streaming:
    1. Stream-to-Static Join: Enrich real-time streaming events (e.g., clicks/orders)
       with static metadata tables (e.g., product catalog, user profile lookups).
    2. Stream-to-Stream Join: Join two independent unbounded real-time streams
       (e.g., Impressions and Clicks, or Payment Requests and Payment Confirmations)
       using watermark constraints and time range join conditions.

BUSINESS USE CASE:
    - Ad-Tech Attribution: Match impression events with click events arriving within 10 minutes.
    - Payment Fraud Pipeline: Match payment authorization requests with bank approval webhooks,
      flagging orphan authorizations as potential fraud if no response arrives within 5 minutes.
    - Dynamic Customer Enrichment: Join streaming click events with user demographic CSV tables.

PRODUCTION RULES & WATERMARKS:
    - Stream-to-Static:
      * Stateless operation (no watermark required for join logic itself).
      * Supports Outer joins (Left outer: stream is left, static is right).
      * Static DataFrame is automatically broadcasted or cached.
    - Stream-to-Stream:
      * State maintenance required for both sides of the stream until join condition expires.
      * Watermark MUST be defined on BOTH streaming DataFrames.
      * Outer joins (Left/Right/Full Outer) REQUIRE a range condition on event time (e.g., `click_time BETWEEN imp_time AND imp_time + INTERVAL 10 MINUTES`).

INTERVIEW QUESTIONS:
    Q: Why are time range conditions required for Stream-to-Stream outer joins?
    A: Spark must know when it can safely stop buffering unmatched records from memory state.
       The time range condition combined with the watermark allows Spark to evict old state when
       the maximum allowed delay passes.

    Q: Can static DataFrames in a Stream-to-Static join change over time?
    A: Spark reads the static DataFrame once at stream initiation unless `location` re-evaluation
       is triggered, or delta table continuous integration is used.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class StreamJoiner:
    """
    Production implementation of streaming join patterns.
    """

    @staticmethod
    def join_stream_with_static(
        stream_df: DataFrame,
        static_df: DataFrame,
        join_key: str,
        join_type: str = "left",
        select_cols: Optional[list] = None,
    ) -> DataFrame:
        """
        Enrich streaming events with static dimension data (Broadcast Join).

        Args:
            stream_df: Real-time streaming DataFrame.
            static_df: Static batch DataFrame (e.g., catalog, customer profiles).
            join_key: Primary/Foreign key column name present in both tables.
            join_type: "inner" or "left" (stream on left, static on right).
            select_cols: Optional list of explicit columns to select after join.

        Returns:
            Enriched streaming DataFrame.
        """
        logger.info("Executing Stream-to-Static join on key: %s, type: %s", join_key, join_type)

        # Broadcast hint speeds up static lookup join
        joined_df = stream_df.join(
            F.broadcast(static_df),
            on=join_key,
            how=join_type,
        )

        if select_cols:
            return joined_df.select(select_cols)

        return joined_df

    @staticmethod
    def join_stream_with_stream(
        left_stream: DataFrame,
        right_stream: DataFrame,
        join_key: str,
        left_time_col: str = "impression_time",
        right_time_col: str = "click_time",
        lower_bound_minutes: int = 0,
        upper_bound_minutes: int = 10,
        join_type: str = "inner",
    ) -> DataFrame:
        """
        Correlate two streaming DataFrames with time-bounded watermark conditions.

        Args:
            left_stream: Left streaming DataFrame (e.g., Impressions) with watermark.
            right_stream: Right streaming DataFrame (e.g., Clicks) with watermark.
            join_key: Common correlation key (e.g., "ad_id", "transaction_id").
            left_time_col: Event time column in left stream.
            right_time_col: Event time column in right stream.
            lower_bound_minutes: Min interval between events (e.g., click timestamp >= impression timestamp - 0 min).
            upper_bound_minutes: Max allowed window offset (e.g., click timestamp <= impression timestamp + 10 min).
            join_type: "inner", "left_outer", "right_outer", or "full_outer".

        Returns:
            Correlated streaming DataFrame.
        """
        logger.info(
            "Executing Stream-to-Stream join on key: %s, time window [%d m, %d m]",
            join_key,
            lower_bound_minutes,
            upper_bound_minutes,
        )

        # Construct time range join condition
        time_condition = (
            (F.col(f"r.{right_time_col}") >= F.col(f"l.{left_time_col}") - F.expr(f"INTERVAL {lower_bound_minutes} MINUTES")) &
            (F.col(f"r.{right_time_col}") <= F.col(f"l.{left_time_col}") + F.expr(f"INTERVAL {upper_bound_minutes} MINUTES"))
        )

        join_condition = (F.col(f"l.{join_key}") == F.col(f"r.{join_key}")) & time_condition

        l_alias = left_stream.alias("l")
        r_alias = right_stream.alias("r")

        return l_alias.join(
            r_alias,
            on=join_condition,
            how=join_type,
        )


def enrich_events_with_lookup(
    stream_df: DataFrame,
    lookup_df: DataFrame,
    join_key: str = "product_id",
) -> DataFrame:
    """
    Convenience function for static reference table enrichment.

    Args:
        stream_df: Streaming events DataFrame.
        lookup_df: Static reference lookup DataFrame.
        join_key: Common join key.

    Returns:
        Enriched DataFrame with lookup columns added.
    """
    joiner = StreamJoiner()
    return joiner.join_stream_with_static(stream_df, lookup_df, join_key=join_key, join_type="left")
