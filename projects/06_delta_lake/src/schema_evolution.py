"""
Module: schema_evolution.py
============================
Delta Lake schema evolution: mergeSchema, overwriteSchema, column add/drop.
"""

import logging
from typing import Optional

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)


def enable_merge_schema_write(df: DataFrame, table_path: str) -> None:
    """
    Append DataFrame to a Delta table with mergeSchema=true to evolve table schema.
    """
    logger.info("Appending data with mergeSchema=true to '%s'", table_path)
    (
        df.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(table_path)
    )


def overwrite_table_schema(df: DataFrame, table_path: str) -> None:
    """
    Overwrite a Delta table schema and data with overwriteSchema=true.
    """
    logger.info("Overwriting table schema and data with overwriteSchema=true at '%s'", table_path)
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(table_path)
    )


def demonstrate_schema_enforcement(spark: SparkSession, table_path: str) -> None:
    """Show how Delta rejects writes that violate the current schema."""
    df_v1 = spark.createDataFrame(
        [(1, "Alice", 100.0), (2, "Bob", 200.0)],
        ["id", "name", "value"]
    )
    df_v1.write.format("delta").mode("overwrite").save(table_path)


def demonstrate_merge_schema(spark: SparkSession, table_path: str) -> None:
    """Demonstrate mergeSchema — adding new columns on append/update."""
    df_v1 = spark.createDataFrame(
        [(1, "Alice Smith", "alice@example.com")],
        ["user_id", "name", "email"]
    )
    df_v1.write.format("delta").mode("overwrite").save(table_path)

    df_v2 = spark.createDataFrame(
        [(2, "Bob Jones", "bob@example.com", "+1-555-0100", "US")],
        ["user_id", "name", "email", "phone", "country"]
    )
    enable_merge_schema_write(df_v2, table_path)


def demonstrate_overwrite_schema(spark: SparkSession, table_path: str) -> None:
    """Demonstrate overwriteSchema — replacing entire schema during overwrite."""
    df_v1 = spark.createDataFrame(
        [(1, "Invoice A", 100)],
        ["invoice_id", "description", "amount"]
    )
    df_v1.write.format("delta").mode("overwrite").save(table_path)

    df_v2 = spark.createDataFrame(
        [(2, "Invoice B", 200.50)],
        ["invoice_id", "description", "amount"]
    )
    overwrite_table_schema(df_v2, table_path)
