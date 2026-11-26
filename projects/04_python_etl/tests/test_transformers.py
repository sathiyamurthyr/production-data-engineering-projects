"""
Unit tests for data transformers (Cleaner, Enricher, Validator, Aggregator).
"""

from pathlib import Path
import pytest
import pandas as pd

from src.transformers.data_cleaner import DataCleaner
from src.transformers.data_enricher import DataEnricher
from src.transformers.data_validator import DataValidator
from src.transformers.aggregator import DataAggregator


def test_data_cleaner_snake_case_and_trim():
    """Test header snake_casing, trimming strings, and missing value fill."""
    raw_df = pd.DataFrame({
        " Customer ID ": [" CUST-01 ", " CUST-02 ", " CUST-01 "],
        " Total Spent ": [100.0, None, 100.0],
        " Status ": [" active ", " pending ", " active "]
    })

    cleaner = DataCleaner({
        "lowercase_headers": True,
        "trim_strings": True,
        "default_fill_values": {"total_spent": 0.0},
        "deduplicate_subset": ["customer_id", "status"]
    })

    cleaned_df = cleaner.transform(raw_df)

    assert "customer_id" in cleaned_df.columns
    assert "total_spent" in cleaned_df.columns
    assert cleaned_df.iloc[0]["customer_id"] == "CUST-01"
    assert cleaned_df.iloc[1]["total_spent"] == 0.0
    assert len(cleaned_df) == 2  # 1 duplicate dropped


def test_data_enricher_customer_tier():
    """Test customer tier classification and timestamp enrichment."""
    df = pd.DataFrame({
        "customer_id": ["C1", "C2", "C3"],
        "total_spent": [6000.0, 1500.0, 50.0]
    })

    enricher = DataEnricher({
        "customer_tier_thresholds": {"vip": 5000.0, "gold": 1000.0, "silver": 200.0}
    })

    enriched_df = enricher.transform(df)

    assert "customer_tier" in enriched_df.columns
    assert enriched_df.iloc[0]["customer_tier"] == "vip"
    assert enriched_df.iloc[1]["customer_tier"] == "gold"
    assert enriched_df.iloc[2]["customer_tier"] == "bronze"
    assert "processed_at" in enriched_df.columns


def test_data_validator_email_and_dlq(tmp_path: Path):
    """Test data validation rules and DLQ quarantining."""
    dlq_file = tmp_path / "dlq.json"
    df = pd.DataFrame([
        {"id": 1, "email": "valid@example.com", "status": "COMPLETED", "grand_total": 150.0},
        {"id": 2, "email": "invalid-email-format", "status": "COMPLETED", "grand_total": 50.0},
        {"id": 3, "email": "good@domain.org", "status": "INVALID_STATUS", "grand_total": -10.0},
    ])

    validator = DataValidator({
        "email_regex": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        "allowed_order_statuses": ["COMPLETED", "PENDING"],
        "min_price": 0.0,
        "dlq_path": str(dlq_file)
    })

    valid_df = validator.transform(df)

    assert len(valid_df) == 1
    assert valid_df.iloc[0]["id"] == 1
    assert dlq_file.exists()


def test_data_aggregator():
    """Test aggregation rollups by grouping key."""
    df = pd.DataFrame({
        "country": ["USA", "USA", "UK", "Canada"],
        "total_spent": [100.0, 300.0, 200.0, 400.0]
    })

    aggregator = DataAggregator({
        "group_by_columns": ["country"],
        "aggregations": {"total_spent": ["sum", "count"]}
    })

    agg_df = aggregator.transform(df)

    assert len(agg_df) == 3
    usa_row = agg_df[agg_df["country"] == "USA"].iloc[0]
    assert usa_row["total_spent_sum"] == 400.0
    assert usa_row["total_spent_count"] == 2
