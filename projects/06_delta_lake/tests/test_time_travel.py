"""
Unit tests for Delta Time Travel, DESCRIBE HISTORY, restore, and diffing.
"""

import os
import pytest
from pyspark.sql import SparkSession
from delta.tables import DeltaTable

from src.delta_table_ops import write_delta_table, read_delta_table
from src.time_travel import read_version_as_of, get_table_history, restore_to_version, compute_version_diff


def test_time_travel_version_as_of(spark: SparkSession, temp_delta_dir: str):
    """Test querying historical table state using versionAsOf."""
    table_path = os.path.join(temp_delta_dir, "test_time_travel")
    
    # Version 0: 2 rows
    v0_df = spark.createDataFrame([("v0_1", 10), ("v0_2", 20)], ["id", "val"])
    write_delta_table(v0_df, table_path, mode="overwrite")
    
    # Version 1: overwrite with 3 rows
    v1_df = spark.createDataFrame([("v1_1", 100), ("v1_2", 200), ("v1_3", 300)], ["id", "val"])
    write_delta_table(v1_df, table_path, mode="overwrite")
    
    # Current version should have 3 rows
    current_df = read_delta_table(spark, table_path)
    assert current_df.count() == 3
    
    # Version 0 should have 2 rows
    hist_v0 = read_version_as_of(spark, table_path, version=0)
    assert hist_v0.count() == 2


def test_get_table_history(spark: SparkSession, temp_delta_dir: str):
    """Test retrieving transaction audit logs."""
    table_path = os.path.join(temp_delta_dir, "test_table_history")
    
    df1 = spark.createDataFrame([("a", 1)], ["col1", "col2"])
    write_delta_table(df1, table_path, mode="overwrite")
    
    df2 = spark.createDataFrame([("b", 2)], ["col1", "col2"])
    write_delta_table(df2, table_path, mode="append")
    
    history_df = get_table_history(spark, table_path)
    assert history_df.count() == 2
    
    operations = [row["operation"] for row in history_df.collect()]
    assert "WRITE" in operations


def test_restore_to_version(spark: SparkSession, temp_delta_dir: str):
    """Test restoring Delta table to an earlier version."""
    table_path = os.path.join(temp_delta_dir, "test_restore")
    
    df_v0 = spark.createDataFrame([("item-1", 10)], ["item", "qty"])
    write_delta_table(df_v0, table_path, mode="overwrite")
    
    df_v1 = spark.createDataFrame([("item-2", 99)], ["item", "qty"])
    write_delta_table(df_v1, table_path, mode="overwrite")
    
    assert read_delta_table(spark, table_path).collect()[0]["item"] == "item-2"
    
    # Restore to Version 0
    restore_to_version(spark, table_path, target_version=0)
    
    restored_df = read_delta_table(spark, table_path)
    assert restored_df.count() == 1
    assert restored_df.collect()[0]["item"] == "item-1"


def test_compute_version_diff(spark: SparkSession, temp_delta_dir: str):
    """Test computing added/deleted rows between versions."""
    table_path = os.path.join(temp_delta_dir, "test_version_diff")
    
    df_v0 = spark.createDataFrame([("k1", "old_val"), ("k2", "val2")], ["key", "val"])
    write_delta_table(df_v0, table_path, mode="overwrite")
    
    df_v1 = spark.createDataFrame([("k1", "new_val"), ("k3", "val3")], ["key", "val"])
    write_delta_table(df_v1, table_path, mode="overwrite")
    
    diffs = compute_version_diff(spark, table_path, v_old=0, v_new=1, key_cols=["key"])
    assert diffs["added"].count() == 1  # k3 added
    assert diffs["deleted"].count() == 1  # k2 deleted
