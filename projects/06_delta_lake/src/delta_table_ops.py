"""
Module: delta_table_ops.py
==========================
Create, read, write Delta tables — covering all write modes and APIs.

Business Use Case:
    The foundation of any Delta Lake project is knowing how to correctly
    create and write to Delta tables. Unlike vanilla Parquet where you
    just write files, Delta tables maintain a transaction log alongside
    the data files. Every write is an atomic transaction.

Write Modes Explained:
    - append: Adds new data to the table. The transaction log records
      the new files added. Previous data is untouched.
    - overwrite: Replaces ALL table data atomically. The old files are
      marked as "removed" in the log but retained for time travel
      (until VACUUM runs).
    - error (default): Fails if table already exists. Safe default.
    - ignore: Silently skips the write if table exists. Use carefully.
"""

import logging
from pathlib import Path
from typing import Optional, List

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------

BRONZE_EVENTS_SCHEMA = StructType([
    StructField("event_id", StringType(), nullable=False),
    StructField("event_type", StringType(), nullable=True),
    StructField("user_id", StringType(), nullable=True),
    StructField("session_id", StringType(), nullable=True),
    StructField("page_url", StringType(), nullable=True),
    StructField("device_type", StringType(), nullable=True),
    StructField("country_code", StringType(), nullable=True),
    StructField("event_timestamp", StringType(), nullable=True),
    StructField("revenue", StringType(), nullable=True),
    StructField("properties", StringType(), nullable=True),
    StructField("ingestion_timestamp", StringType(), nullable=True),
])

SILVER_EVENTS_SCHEMA = StructType([
    StructField("event_id", StringType(), nullable=False),
    StructField("event_type", StringType(), nullable=False),
    StructField("user_id", LongType(), nullable=False),
    StructField("session_id", StringType(), nullable=False),
    StructField("page_url", StringType(), nullable=True),
    StructField("device_type", StringType(), nullable=True),
    StructField("country_code", StringType(), nullable=True),
    StructField("event_timestamp", TimestampType(), nullable=False),
    StructField("revenue", DoubleType(), nullable=True),
    StructField("event_date", StringType(), nullable=False),
])

CUSTOMER_SCHEMA = StructType([
    StructField("customer_id", IntegerType(), nullable=False),
    StructField("name", StringType(), nullable=False),
    StructField("email", StringType(), nullable=False),
    StructField("country", StringType(), nullable=True),
    StructField("segment", StringType(), nullable=True),
    StructField("lifetime_value", DoubleType(), nullable=True),
    StructField("is_active", IntegerType(), nullable=True),
    StructField("updated_at", TimestampType(), nullable=True),
])

# ---------------------------------------------------------------------------
# Table Creation & Write Operations
# ---------------------------------------------------------------------------

def create_delta_table_from_df(
    df: DataFrame,
    table_path: str,
    partition_by: Optional[list] = None,
    mode: str = "overwrite",
    comment: str = "",
) -> None:
    """Write DataFrame as Delta table to table_path."""
    logger.info("Writing DataFrame to Delta table | path=%s | mode=%s", table_path, mode)
    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    if comment:
        writer = writer.option("comment", comment)
    writer.save(table_path)
    logger.info("Delta table written successfully to %s", table_path)


# Aliases for convenient importing across tests and pipeline code
create_delta_table = create_delta_table_from_df


def write_delta_table(
    df: DataFrame,
    table_path: str,
    mode: str = "overwrite",
    partition_by: Optional[List[str]] = None,
    options: Optional[dict] = None
) -> None:
    """General function to write a DataFrame to a Delta table."""
    logger.info("Writing Delta table at %s with mode=%s", table_path, mode)
    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    if options:
        for k, v in options.items():
            writer = writer.option(k, str(v))
    writer.save(table_path)


def create_delta_table_sql(
    spark: SparkSession,
    table_name: str,
    schema: StructType,
    table_path: str,
    partition_by: Optional[list] = None,
    properties: Optional[dict] = None,
    comment: str = "",
) -> None:
    """Create an empty Delta table using SQL DDL."""
    col_defs = []
    for field in schema.fields:
        nullable = "" if field.nullable else " NOT NULL"
        col_defs.append(f"    {field.name} {field.dataType.simpleString()}{nullable}")
    cols_sql = ",\n".join(col_defs)
    partition_sql = f"\nPARTITIONED BY ({', '.join(partition_by)})" if partition_by else ""
    
    props_sql = ""
    if properties:
        pairs = [f"'{k}' = '{v}'" for k, v in properties.items()]
        props_sql = f"\nTBLPROPERTIES ({', '.join(pairs)})"

    comment_sql = f"\nCOMMENT '{comment}'" if comment else ""

    ddl = f"CREATE TABLE IF NOT EXISTS {table_name} (\n{cols_sql}\n)\nUSING DELTA\nLOCATION '{table_path}'{comment_sql}{partition_sql}{props_sql}"
    spark.sql(ddl)


def read_delta_table(
    spark: SparkSession,
    table_path: str,
    version: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> DataFrame:
    """Read a Delta table, optionally at a specific version or timestamp."""
    reader = spark.read.format("delta")
    if version is not None:
        reader = reader.option("versionAsOf", version)
    elif timestamp is not None:
        reader = reader.option("timestampAsOf", timestamp)
    return reader.load(table_path)


def read_delta_table_object(spark: SparkSession, table_path: str) -> DeltaTable:
    """Load a Delta table as a DeltaTable object."""
    if not DeltaTable.isDeltaTable(spark, table_path):
        raise ValueError(f"Path is not a Delta table: {table_path}")
    return DeltaTable.forPath(spark, table_path)


def append_to_delta_table(
    df: DataFrame,
    table_path: str,
    merge_schema: bool = False,
) -> None:
    """Append new records to an existing Delta table."""
    (
        df.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", str(merge_schema).lower())
        .save(table_path)
    )


def overwrite_delta_table(
    df: DataFrame,
    table_path: str,
    overwrite_schema: bool = False,
    partition_filter: Optional[str] = None,
) -> None:
    """Overwrite a Delta table — either entirely or a specific partition."""
    writer = (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", str(overwrite_schema).lower())
    )
    if partition_filter:
        writer = writer.option("replaceWhere", partition_filter)
    writer.save(table_path)


def get_table_history(spark: SparkSession, table_path: str, limit: int = 20) -> DataFrame:
    """Retrieve transaction history of a Delta table."""
    dt = DeltaTable.forPath(spark, table_path)
    return dt.history(limit)


def get_table_details(spark: SparkSession, table_path: str) -> DataFrame:
    """Get detailed metadata about a Delta table."""
    return spark.sql(f"DESCRIBE DETAIL delta.`{table_path}`")


def show_table_files(spark: SparkSession, table_path: str) -> DataFrame:
    """List details for Delta table snapshot."""
    dt = DeltaTable.forPath(spark, table_path)
    return dt.detail()
