"""
test_transformations.py — Unit Tests for Stateless Transformations
===================================================================
"""

import pytest
from pyspark.sql import functions as F
from src.transformations.stream_transformer import StreamTransformer, apply_stateless_transformations


def test_filter_valid_events(sample_click_df):
    """Verify null/empty event IDs are filtered out."""
    transformer = StreamTransformer()
    filtered_df = transformer.filter_valid_events(sample_click_df, id_column="event_id")

    # Sample click df has 4 rows, 1 row has null event_id
    assert filtered_df.count() == 3
    assert filtered_df.filter(F.col("event_id").isNull()).count() == 0


def test_normalize_event_timestamps(sample_click_df):
    """Verify string timestamp conversion to TimestampType."""
    transformer = StreamTransformer()
    ts_df = transformer.normalize_event_timestamps(
        sample_click_df, ts_col="event_timestamp", output_ts_col="event_time"
    )

    assert "event_time" in ts_df.columns
    assert str(ts_df.schema["event_time"].dataType) == "TimestampType"


def test_categorize_event_severity(sample_click_df):
    """Verify tier assignment based on price."""
    transformer = StreamTransformer()
    tiered_df = transformer.categorize_event_severity(sample_click_df, amount_col="price")

    high_val_count = tiered_df.filter(F.col("event_tier") == "HIGH_VALUE").count()
    # evt-3 price is 600.0 >= 500.0
    assert high_val_count == 1


def test_apply_stateless_transformations_pipeline(sample_click_df):
    """Verify full stateless transformation pipeline execution."""
    res_df = apply_stateless_transformations(sample_click_df)

    assert "processed_at" in res_df.columns
    assert "event_tier" in res_df.columns
    assert res_df.count() == 3
