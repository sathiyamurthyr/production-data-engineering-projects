"""
test_aggregations.py
====================
Unit tests for src/aggregations.py using pytest.
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession

from src.aggregations import (
    group_by_multi_dim,
    hierarchical_rollup,
    multidimensional_cube,
    pivot_sales_by_region,
)
from src.dataframe_basics import create_sample_sales


def test_group_by_multi_dim(spark: SparkSession):
    sales = create_sample_sales(spark)

    result = group_by_multi_dim(sales, ["category", "region"])
    cols = result.columns

    assert "total_revenue" in cols
    assert "total_quantity" in cols
    assert "avg_order_value" in cols
    assert "unique_customers" in cols
    assert result.count() > 0


def test_pivot_sales_by_region(spark: SparkSession):
    sales = create_sample_sales(spark)

    pivoted = pivot_sales_by_region(sales, pivot_col="region", pivot_values=["North", "South", "East", "West"])
    cols = pivoted.columns

    assert "category" in cols
    assert "North" in cols
    assert "South" in cols
    assert "East" in cols
    assert "West" in cols


def test_hierarchical_rollup(spark: SparkSession):
    sales = create_sample_sales(spark)

    rollup_df = hierarchical_rollup(sales, ["category", "region"])
    assert "grouping_level" in rollup_df.columns

    # Check that grand total row exists (category is null, region is null)
    grand_total_row = rollup_df.filter("category IS NULL AND region IS NULL").first()
    assert grand_total_row is not None
    assert float(grand_total_row["total_revenue"]) > 0


def test_multidimensional_cube(spark: SparkSession):
    sales = create_sample_sales(spark)

    cube_df = multidimensional_cube(sales, ["category", "region"])
    assert cube_df.count() > sales.count()
