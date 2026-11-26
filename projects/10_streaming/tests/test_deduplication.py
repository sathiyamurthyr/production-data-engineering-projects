"""
test_deduplication.py — Unit Tests for Event Deduplication
===========================================================
"""

import pytest
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType
from src.transformations.deduplication import StreamDeduplicator, deduplicate_stream


def test_deduplicate_within_batch(spark):
    """Verify in-batch deduplication keeping newest record."""
    data = [
        ("evt-100", "2026-07-20 10:00:00", 10.0),
        ("evt-100", "2026-07-20 10:01:00", 15.0),  # Newer timestamp for same event_id
        ("evt-101", "2026-07-20 10:00:30", 25.0),
    ]

    schema = StructType([
        StructField("event_id", StringType(), True),
        StructField("event_timestamp", StringType(), True),
        StructField("price", DoubleType(), True),
    ])

    df = spark.createDataFrame(data, schema)
    dedup_df = StreamDeduplicator.deduplicate_within_batch(
        df, primary_key="event_id", ordering_col="event_timestamp"
    )

    assert dedup_df.count() == 2
    evt_100 = dedup_df.filter(F.col("event_id") == "evt-100").first()
    assert evt_100["price"] == 15.0


def test_deduplicate_stream_batch_helper(spark):
    """Verify dropDuplicates helper on DataFrame."""
    data = [
        ("evt-1", "2026-07-20 10:00:00"),
        ("evt-1", "2026-07-20 10:00:00"),
        ("evt-2", "2026-07-20 10:01:00"),
    ]
    schema = StructType([
        StructField("event_id", StringType(), True),
        StructField("event_time", StringType(), True),
    ])
    df = spark.createDataFrame(data, schema)

    dedup = StreamDeduplicator.deduplicate_events(
        df, dedup_cols=["event_id"], watermark_col=None
    )
    assert dedup.count() == 2
