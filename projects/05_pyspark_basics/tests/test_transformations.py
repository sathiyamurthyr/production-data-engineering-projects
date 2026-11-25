"""
test_transformations.py
=======================
Unit tests for src/transformations.py using pytest.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

from src.dataframe_basics import SALES_SCHEMA, create_sample_sales
from src.transformations import (
    add_derived_metrics,
    combine_sales_datasets,
    filter_sales,
    select_and_rename_columns,
    summarize_sales_by_category,
)


def test_select_and_rename_columns(spark: SparkSession):
    sales = create_sample_sales(spark)
    cols_map = {"sale_id": "id", "customer_id": "cust_id", "total_amount": "revenue"}

    result = select_and_rename_columns(sales, cols_map)

    assert result.columns == ["id", "cust_id", "revenue"]
    assert result.count() == 5


def test_filter_sales(spark: SparkSession):
    sales = create_sample_sales(spark)

    # Filter min_amount = 500 and status = Completed
    result = filter_sales(sales, min_amount=500.0, statuses=["Completed"])
    records = result.collect()

    assert len(records) == 2
    for r in records:
        assert float(r["total_amount"]) >= 500.0
        assert r["status"] == "Completed"


def test_add_derived_metrics(spark: SparkSession):
    sales = create_sample_sales(spark)

    result = add_derived_metrics(sales)
    row = result.filter("sale_id = 'S001'").first()

    assert row is not None
    # S001: qty=1, price=1200.00, discount=5.0% -> gross=1200.00, discount_amount=60.00, calc_total=1140.00
    assert float(row["gross_amount"]) == 1200.00
    assert float(row["discount_amount"]) == 60.00
    assert float(row["calculated_total"]) == 1140.00
    assert row["high_value_flag"] is True
    assert row["order_year"] == 2024
    assert row["order_month"] == 1


def test_summarize_sales_by_category(spark: SparkSession):
    sales = create_sample_sales(spark)

    summary = summarize_sales_by_category(sales)
    summary_dict = {r["category"]: float(r["total_sales"]) for r in summary.collect()}

    assert "Electronics" in summary_dict
    assert "Furniture" in summary_dict
    assert summary_dict["Electronics"] > 0


def test_combine_sales_datasets(spark: SparkSession):
    sales1 = create_sample_sales(spark)
    sales2 = create_sample_sales(spark)

    combined = combine_sales_datasets(sales1, sales2, by_name=True)
    assert combined.count() == 10
