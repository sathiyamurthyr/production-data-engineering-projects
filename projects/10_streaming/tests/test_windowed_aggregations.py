"""
test_windowed_aggregations.py — Unit Tests for Time Window Aggregations
=========================================================================
"""

import pytest
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType
from src.transformations.windowed_aggregations import WindowedAggregator


def test_tumbling_window_aggregation(spark):
    """Verify tumbling window metric counts."""
    data = [
        ("2026-07-20 10:01:00", "elec", 100.0),
        ("2026-07-20 10:03:00", "elec", 200.0),
        ("2026-07-20 10:07:00", "elec", 150.0),  # Falls into 10:05-10:10 window
    ]

    schema = StructType([
        StructField("event_time_str", StringType(), True),
        StructField("category", StringType(), True),
        StructField("price", DoubleType(), True),
    ])

    df = spark.createDataFrame(data, schema).withColumn(
        "event_time", F.to_timestamp(F.col("event_time_str"))
    )

    aggregator = WindowedAggregator()
    agg_df = aggregator.tumbling_window_aggregation(
        df,
        time_col="event_time",
        window_duration="5 minutes",
        group_cols=["category"],
    )

    # 10:00-10:05 window has 2 events (sum=300.0), 10:05-10:10 has 1 event (sum=150.0)
    assert agg_df.count() == 2
    
    first_window = agg_df.filter(F.col("total_events") == 2).first()
    assert first_window["total_revenue"] == 300.0


def test_sliding_window_aggregation(spark):
    """Verify overlapping sliding window metrics."""
    data = [
        ("2026-07-20 10:02:00", "usr-1", 50.0),
    ]
    schema = StructType([
        StructField("event_time_str", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("price", DoubleType(), True),
    ])
    df = spark.createDataFrame(data, schema).withColumn(
        "event_time", F.to_timestamp(F.col("event_time_str"))
    )

    aggregator = WindowedAggregator()
    slide_df = aggregator.sliding_window_aggregation(
        df,
        time_col="event_time",
        window_duration="10 minutes",
        slide_duration="5 minutes",
    )

    # A single event at 10:02 fall into multiple overlapping sliding windows (e.g. 09:55-10:05, 10:00-10:10)
    assert slide_df.count() == 2
