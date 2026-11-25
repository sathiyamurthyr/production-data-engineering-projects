"""
test_joins.py
=============
Unit tests for src/joins.py using pytest.
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession

from src.dataframe_basics import create_sample_sales
from src.joins import (
    apply_salted_join,
    execute_broadcast_join,
    execute_standard_join,
    filter_active_customers_semi_join,
    filter_unmatched_records_anti_join,
)


def test_execute_standard_join(spark: SparkSession):
    sales = create_sample_sales(spark)
    customers_data = [("C101", "Alice"), ("C102", "Bob")]
    cust_df = spark.createDataFrame(customers_data, ["customer_id", "customer_name"])

    joined = execute_standard_join(sales, cust_df, join_key="customer_id", join_type="inner")
    assert joined.count() == 2
    assert "customer_name" in joined.columns


def test_execute_broadcast_join(spark: SparkSession):
    sales = create_sample_sales(spark)
    prod_data = [("P201", "TechBrand"), ("P202", "ClickMaster")]
    prod_df = spark.createDataFrame(prod_data, ["product_id", "brand"])

    joined = execute_broadcast_join(sales, prod_df, join_key="product_id", join_type="left")
    assert joined.count() == sales.count()
    assert "brand" in joined.columns


def test_left_anti_join(spark: SparkSession):
    events_data = [
        ("E1", "C101"),
        ("E2", "C999"),  # Unknown customer
    ]
    events_df = spark.createDataFrame(events_data, ["event_id", "customer_id"])

    cust_data = [("C101", "Alice")]
    cust_df = spark.createDataFrame(cust_data, ["customer_id", "name"])

    unmatched = filter_unmatched_records_anti_join(events_df, cust_df, join_key="customer_id")
    assert unmatched.count() == 1
    assert unmatched.first()["customer_id"] == "C999"


def test_left_semi_join(spark: SparkSession):
    cust_data = [("C101", "Alice"), ("C102", "Bob"), ("C999", "NoSalesUser")]
    cust_df = spark.createDataFrame(cust_data, ["customer_id", "name"])
    sales = create_sample_sales(spark)

    purchasers = filter_active_customers_semi_join(cust_df, sales, join_key="customer_id")
    cust_ids = [r["customer_id"] for r in purchasers.collect()]

    assert "C101" in cust_ids
    assert "C102" in cust_ids
    assert "C999" not in cust_ids


def test_salted_join(spark: SparkSession):
    sales = create_sample_sales(spark)
    prod_data = [("P201", "Laptop Pro 15"), ("P202", "Wireless Mouse")]
    prod_df = spark.createDataFrame(prod_data, ["product_id", "product_name_ref"])

    salted = apply_salted_join(sales, prod_df, join_key="product_id", salt_factor=2)
    assert salted.count() == 2
