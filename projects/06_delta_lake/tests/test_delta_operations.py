"""
Unit tests for core Delta Lake operations (create, read, write, append, overwrite, constraints, schema evolution).
"""

import os
import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from delta.tables import DeltaTable

from src.delta_table_ops import create_delta_table, write_delta_table, read_delta_table
from src.schema_evolution import enable_merge_schema_write
from src.vacuuming import vacuum_delta_table
from src.delta_constraints import add_check_constraint


def test_create_and_read_delta_table(spark: SparkSession, temp_delta_dir: str):
    """Test creating a Delta table and reading back data."""
    table_path = os.path.join(temp_delta_dir, "test_basic_table")
    
    data = [("id-1", "Alice", 100.0), ("id-2", "Bob", 200.0)]
    schema = StructType([
        StructField("id", StringType(), True),
        StructField("name", StringType(), True),
        StructField("balance", DoubleType(), True)
    ])
    df = spark.createDataFrame(data, schema)
    
    write_delta_table(df, table_path, mode="overwrite")
    
    assert DeltaTable.isDeltaTable(spark, table_path)
    
    read_df = read_delta_table(spark, table_path)
    assert read_df.count() == 2
    assert "id" in read_df.columns
    assert "name" in read_df.columns


def test_append_and_overwrite(spark: SparkSession, temp_delta_dir: str):
    """Test append mode vs overwrite mode."""
    table_path = os.path.join(temp_delta_dir, "test_append_overwrite")
    
    data1 = [("usr-1", 10), ("usr-2", 20)]
    df1 = spark.createDataFrame(data1, ["user_id", "score"])
    write_delta_table(df1, table_path, mode="overwrite")
    assert read_delta_table(spark, table_path).count() == 2
    
    data2 = [("usr-3", 30)]
    df2 = spark.createDataFrame(data2, ["user_id", "score"])
    write_delta_table(df2, table_path, mode="append")
    assert read_delta_table(spark, table_path).count() == 3
    
    data3 = [("usr-99", 999)]
    df3 = spark.createDataFrame(data3, ["user_id", "score"])
    write_delta_table(df3, table_path, mode="overwrite")
    assert read_delta_table(spark, table_path).count() == 1


def test_schema_evolution(spark: SparkSession, temp_delta_dir: str):
    """Test merging schema on append when new columns are added."""
    table_path = os.path.join(temp_delta_dir, "test_schema_evo")
    
    df1 = spark.createDataFrame([("a", 1)], ["col1", "col2"])
    write_delta_table(df1, table_path, mode="overwrite")
    
    df2 = spark.createDataFrame([("b", 2, "new_val")], ["col1", "col2", "col3"])
    enable_merge_schema_write(df2, table_path)
    
    res_df = read_delta_table(spark, table_path)
    assert "col3" in res_df.columns
    assert res_df.count() == 2


def test_check_constraints(spark: SparkSession, temp_delta_dir: str):
    """Test CHECK constraint enforcement on write."""
    table_path = os.path.join(temp_delta_dir, "test_constraints")
    
    df_valid = spark.createDataFrame([("p1", 50.0)], ["prod_id", "price"])
    write_delta_table(df_valid, table_path, mode="overwrite")
    
    add_check_constraint(spark, table_path, "price_must_be_positive", "price > 0")
    
    df_invalid = spark.createDataFrame([("p2", -10.0)], ["prod_id", "price"])
    with pytest.raises(Exception):
        write_delta_table(df_invalid, table_path, mode="append")
