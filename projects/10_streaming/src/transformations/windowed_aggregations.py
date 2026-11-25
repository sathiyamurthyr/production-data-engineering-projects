"""
windowed_aggregations.py — Windowed Aggregations in Structured Streaming
========================================================================

PURPOSE:
    Provides time-based aggregation patterns over unbounded streams.
    Structured Streaming supports three window types:
    1. Tumbling Windows: Fixed-size, non-overlapping time intervals (e.g., 5-minute buckets).
    2. Sliding Windows: Fixed-size, overlapping intervals (e.g., 10-minute window sliding every 1 minute).
    3. Session Windows: Dynamic windows defined by periods of user activity separated by a gap of inactivity.

BUSINESS USE CASE:
    - Real-time Fraud Detection: Count transaction volume per user over a 5-minute sliding window every 30 seconds.
    - Application SLA Monitoring: Calculate 99th percentile response time per microservice in 1-minute tumbling windows.
    - User Engagement: Track continuous user click streams with session windows bounded by 15-minute inactivity timeouts.

PRODUCTION EXAMPLE:
    from src.transformations.windowed_aggregations import WindowedAggregator

    aggregator = WindowedAggregator()
    
    # 5-minute tumbling aggregations
    tumbling_df = aggregator.tumbling_window_aggregation(
        df,
        time_col="event_time",
        window_duration="5 minutes",
        group_cols=["category"],
    )

PERFORMANCE & WATERMARKING RULES:
    - A watermark (df.withWatermark(time_col, delay)) MUST be set BEFORE calling windowed aggregations
      if you intend to run in `Append` output mode or wish to bound memory state size.
    - State Store Cleanup: Without a watermark, Spark keeps state in memory indefinitely.
    - Slide Duration vs Window Duration: A 1-hour window sliding every 1 second creates 3600 concurrent windows,
      causing memory bloat. Choose realistic slide intervals.

INTERVIEW QUESTIONS:
    Q: What happens to state when a watermark condition is met?
    A: When event time passes (watermark_time > window_end_time), Spark drops the window from
       the StateStore and outputs the finalized result (in Append mode).

    Q: Can you perform session windowing in Structured Streaming?
    A: Yes, Spark 3.2+ introduced session window support via `session_window(time_col, "gap_duration")`.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


class WindowedAggregator:
    """
    Production utility for windowed real-time stream aggregations.
    """

    @staticmethod
    def tumbling_window_aggregation(
        df: DataFrame,
        time_col: str = "event_time",
        window_duration: str = "5 minutes",
        group_cols: Optional[List[str]] = None,
        agg_exprs: Optional[dict] = None,
    ) -> DataFrame:
        """
        Compute tumbling (non-overlapping) window aggregations.

        Args:
            df: Watermarked streaming DataFrame.
            time_col: Column name containing TimestampType event times.
            window_duration: Duration of each window (e.g., "5 minutes", "1 hour").
            group_cols: Optional dimensional grouping columns (e.g., ["country_code", "category"]).
            agg_exprs: Dictionary mapping column names to aggregate functions or default standard metrics.

        Returns:
            Streaming DataFrame with window aggregate columns.
        """
        grouping = [F.window(F.col(time_col), window_duration)]
        if group_cols:
            grouping.extend([F.col(c) for c in group_cols])

        aggregated = df.groupBy(grouping)

        if agg_exprs:
            result_df = aggregated.agg(agg_exprs)
        else:
            # Default standard operational metrics
            result_df = aggregated.agg(
                F.count("*").alias("total_events"),
                F.sum("price").alias("total_revenue"),
                F.avg("price").alias("avg_price"),
                F.min(time_col).alias("window_start_event"),
                F.max(time_col).alias("window_end_event"),
            )

        logger.info("Created tumbling window aggregation: duration=%s", window_duration)
        return result_df

    @staticmethod
    def sliding_window_aggregation(
        df: DataFrame,
        time_col: str = "event_time",
        window_duration: str = "10 minutes",
        slide_duration: str = "1 minute",
        group_cols: Optional[List[str]] = None,
    ) -> DataFrame:
        """
        Compute sliding (overlapping) window aggregations.

        Args:
            df: Watermarked streaming DataFrame.
            time_col: Event timestamp column.
            window_duration: Size of each window (e.g., "10 minutes").
            slide_duration: Frequency of window creation (e.g., "1 minute").
            group_cols: Additional grouping columns.

        Returns:
            Sliding window aggregated DataFrame.
        """
        grouping = [F.window(F.col(time_col), window_duration, slide_duration)]
        if group_cols:
            grouping.extend([F.col(c) for c in group_cols])

        logger.info(
            "Created sliding window aggregation: window=%s, slide=%s",
            window_duration,
            slide_duration,
        )

        return (
            df.groupBy(grouping)
            .agg(
                F.count("*").alias("event_count"),
                F.countDistinct("user_id").alias("unique_users"),
                F.avg("price").alias("avg_transaction_val"),
                F.max("price").alias("max_transaction_val"),
            )
        )

    @staticmethod
    def session_window_aggregation(
        df: DataFrame,
        time_col: str = "event_time",
        session_gap: str = "15 minutes",
        user_col: str = "user_id",
    ) -> DataFrame:
        """
        Compute dynamic session window aggregations based on user activity gap timeouts.

        Args:
            df: Watermarked streaming DataFrame.
            time_col: Event timestamp column.
            session_gap: Inactivity duration threshold to close a session (e.g., "15 minutes").
            user_col: Key identifying entity session boundary (e.g., user_id or device_id).

        Returns:
            Session window aggregated DataFrame.
        """
        logger.info("Created session window aggregation: gap=%s, key=%s", session_gap, user_col)

        return (
            df.groupBy(
                F.session_window(F.col(time_col), session_gap),
                F.col(user_col),
            )
            .agg(
                F.count("*").alias("session_event_count"),
                F.min(time_col).alias("session_start"),
                F.max(time_col).alias("session_end"),
                F.sum("price").alias("session_total_spend"),
            )
        )


def aggregate_stream_metrics(
    df: DataFrame,
    window_type: str = "tumbling",
    time_col: str = "event_time",
    window_duration: str = "5 minutes",
    slide_duration: Optional[str] = None,
    group_cols: Optional[List[str]] = None,
) -> DataFrame:
    """
    Factory function for routing to specific window aggregation logic.

    Args:
        df: Watermarked streaming DataFrame.
        window_type: "tumbling", "sliding", or "session".
        time_col: Event timestamp column.
        window_duration: Window duration string.
        slide_duration: Slide duration string (for sliding windows).
        group_cols: Grouping dimension columns.

    Returns:
        Aggregated streaming DataFrame.
    """
    aggregator = WindowedAggregator()

    if window_type == "tumbling":
        return aggregator.tumbling_window_aggregation(
            df, time_col=time_col, window_duration=window_duration, group_cols=group_cols
        )
    elif window_type == "sliding":
        slide = slide_duration or "1 minute"
        return aggregator.sliding_window_aggregation(
            df, time_col=time_col, window_duration=window_duration, slide_duration=slide, group_cols=group_cols
        )
    elif window_type == "session":
        return aggregator.session_window_aggregation(
            df, time_col=time_col, session_gap=window_duration, user_col=(group_cols[0] if group_cols else "user_id")
        )
    else:
        raise ValueError(f"Unsupported window_type: {window_type}. Must be tumbling, sliding, or session.")
