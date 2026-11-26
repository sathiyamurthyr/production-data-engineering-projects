"""
Unit tests for Delta MERGE INTO operations (SCD Type 1, SCD Type 2, and deletes).
"""

import os
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.delta_table_ops import write_delta_table, read_delta_table
from src.merge_operations import upsert_scd_type_1, merge_with_soft_and_hard_deletes, upsert_scd_type_2


def test_scd_type_1_upsert(spark: SparkSession, temp_delta_dir: str):
    """Test updating existing records and inserting new records in SCD Type 1."""
    table_path = os.path.join(temp_delta_dir, "test_scd1")
    
    # Target initial table
    initial_data = [("c1", "Alice", "Gold"), ("c2", "Bob", "Silver")]
    df_init = spark.createDataFrame(initial_data, ["customer_id", "name", "tier"])
    write_delta_table(df_init, table_path, mode="overwrite")
    
    # Incoming updates (Update Alice to Platinum, Insert Charlie)
    updates_data = [("c1", "Alice", "Platinum"), ("c3", "Charlie", "Bronze")]
    df_updates = spark.createDataFrame(updates_data, ["customer_id", "name", "tier"])
    
    upsert_scd_type_1(spark, table_path, df_updates, primary_key="customer_id")
    
    res_df = read_delta_table(spark, table_path)
    assert res_df.count() == 3
    
    alice_tier = res_df.filter(F.col("customer_id") == "c1").select("tier").collect()[0]["tier"]
    assert alice_tier == "Platinum"


def test_merge_with_deletes(spark: SparkSession, temp_delta_dir: str):
    """Test soft delete processing using MERGE INTO."""
    table_path = os.path.join(temp_delta_dir, "test_merge_deletes")
    
    initial_data = [("u1", "active", False), ("u2", "active", False)]
    df_init = spark.createDataFrame(initial_data, ["user_id", "status", "is_deleted"])
    write_delta_table(df_init, table_path, mode="overwrite")
    
    # Incoming batch marking u2 as deleted
    updates_data = [("u2", "inactive", True), ("u3", "active", False)]
    df_updates = spark.createDataFrame(updates_data, ["user_id", "status", "is_deleted"])
    
    merge_with_soft_and_hard_deletes(spark, table_path, df_updates, primary_key="user_id")
    
    res_df = read_delta_table(spark, table_path)
    user_ids = [row["user_id"] for row in res_df.collect()]
    
    assert "u1" in user_ids
    assert "u3" in user_ids
    assert "u2" not in user_ids  # u2 deleted


def test_scd_type_2_merge(spark: SparkSession, temp_delta_dir: str):
    """Test SCD Type 2 tracking with effective dates and is_current flag."""
    table_path = os.path.join(temp_delta_dir, "test_scd2")
    
    # Initial target schema
    initial_data = [
        ("c1", "Alice", "New York", "2026-01-01 00:00:00", None, True)
    ]
    df_init = (
        spark.createDataFrame(initial_data, ["customer_id", "name", "city", "start_date", "end_date", "is_current"])
        .withColumn("start_date", F.to_timestamp("start_date"))
        .withColumn("end_date", F.to_timestamp("end_date"))
    )
    write_delta_table(df_init, table_path, mode="overwrite")
    
    # Incoming update for Alice (moved to London)
    update_data = [("c1", "Alice", "London", "2026-02-01 00:00:00")]
    df_update = (
        spark.createDataFrame(update_data, ["customer_id", "name", "city", "updated_at"])
        .withColumn("updated_at", F.to_timestamp("updated_at"))
    )
    
    upsert_scd_type_2(spark, table_path, df_update, primary_key="customer_id", effective_date_col="updated_at")
    
    res_df = read_delta_table(spark, table_path)
    assert res_df.count() == 2
    
    # Check current active record
    current_rec = res_df.filter(F.col("is_current") == True).collect()[0]
    assert current_rec["city"] == "London"
    
    # Check expired record
    expired_rec = res_df.filter(F.col("is_current") == False).collect()[0]
    assert expired_rec["city"] == "New York"
    assert expired_rec["end_date"] is not None
