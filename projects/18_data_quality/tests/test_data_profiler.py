"""
Unit tests for Data Profiler and Schema Profiler modules.
"""

import pytest
import pandas as pd
from src.profiling.data_profiler import DataProfiler
from src.profiling.schema_profiler import SchemaProfiler


@pytest.fixture
def profile_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "category": ["A", "B", "A", "C", None],
        "score": [10.5, 20.0, 15.2, 85.0, 42.1],
    })


def test_data_profiler(profile_df):
    profiler = DataProfiler(dataset_name="test_profile")
    profile = profiler.profile(profile_df)

    assert profile["total_rows"] == 5
    assert profile["total_columns"] == 3
    assert profile["columns"]["id"]["is_unique"] is True
    assert profile["columns"]["category"]["null_count"] == 1
    assert profile["columns"]["score"]["min"] == 10.5
    assert profile["columns"]["score"]["max"] == 85.0


def test_schema_profiler_no_drift(profile_df):
    profiler = SchemaProfiler(baseline_schema={
        "id": "int64",
        "category": "object",
        "score": "float64",
    })
    result = profiler.detect_drift(profile_df)

    assert result["has_drift"] is False
    assert len(result["added_columns"]) == 0
    assert len(result["missing_columns"]) == 0


def test_schema_profiler_with_drift(profile_df):
    profiler = SchemaProfiler(baseline_schema={
        "id": "int64",
        "category": "object",
        "email": "object",  # missing in profile_df
    })
    result = profiler.detect_drift(profile_df)

    assert result["has_drift"] is True
    assert "score" in result["added_columns"]
    assert "email" in result["missing_columns"]
