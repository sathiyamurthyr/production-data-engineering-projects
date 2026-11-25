"""
dataframe_basics.py
===================
DataFrame creation, schema definition, and multi-format read/write patterns.

Business Use Case:
    A data engineer must be able to ingest data from heterogeneous sources
    (CSV, JSON, Parquet, in-memory collections) and write results to various
    sinks.  This module shows every common pattern with explicit schemas to
    avoid the "double-scan schema inference" tax.

Key Concepts Covered:
    - SparkSession.createDataFrame()  (from Python lists + Row objects)
    - StructType / StructField schema definition
    - Read CSV / JSON / Parquet with options
    - Write with saveMode, partitionBy, compression

Interview Questions:
    Q: Why should you always define schemas explicitly instead of using inferSchema?
    A: Schema inference reads the entire file (or a sample) to determine types.
       For large datasets this doubles I/O.  Explicit schemas are also safer –
       inferSchema can silently cast long integers to doubles.

    Q: What is the difference between df.show() and df.collect()?
    A: show() prints N rows to the driver stdout.  collect() brings ALL rows to
       driver memory as a Python list – dangerous on large DataFrames.

    Q: What does printSchema() output?
    A: A tree view of the StructType showing field names, data types, and
       nullable flags.  Essential for verifying complex nested schemas.

    Q: How do you convert a Pandas DataFrame to a Spark DataFrame?
    A: spark.createDataFrame(pandas_df).  Requires Arrow if > 10K rows for speed.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DecimalType,
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

SALES_SCHEMA = StructType([
    StructField("sale_id",       StringType(),          nullable=False),
    StructField("order_date",    DateType(),            nullable=False),
    StructField("customer_id",   StringType(),          nullable=False),
    StructField("product_id",    StringType(),          nullable=False),
    StructField("product_name",  StringType(),          nullable=True),
    StructField("category",      StringType(),          nullable=True),
    StructField("region",        StringType(),          nullable=True),
    StructField("salesperson",   StringType(),          nullable=True),
    StructField("quantity",      IntegerType(),         nullable=True),
    StructField("unit_price",    DecimalType(12, 2),    nullable=True),
    StructField("discount_pct",  DoubleType(),          nullable=True),
    StructField("total_amount",  DecimalType(12, 2),    nullable=True),
    StructField("status",        StringType(),          nullable=True),
])

CUSTOMER_EVENT_SCHEMA = StructType([
    StructField("event_id",      StringType(),          nullable=False),
    StructField("customer_id",   StringType(),          nullable=False),
    StructField("event_type",    StringType(),          nullable=True),
    StructField("page",          StringType(),          nullable=True),
    StructField("timestamp",     TimestampType(),       nullable=True),
    StructField("session_id",    StringType(),          nullable=True),
    StructField("device",        StringType(),          nullable=True),
    StructField("browser",       StringType(),          nullable=True),
    StructField("country",       StringType(),          nullable=True),
    StructField("duration_sec",  IntegerType(),         nullable=True),
    StructField("is_converted",  BooleanType(),         nullable=True),
])

PRODUCT_SCHEMA = StructType([
    StructField("product_id",       StringType(),       nullable=False),
    StructField("product_name",     StringType(),       nullable=True),
    StructField("category",         StringType(),       nullable=True),
    StructField("subcategory",      StringType(),       nullable=True),
    StructField("brand",            StringType(),       nullable=True),
    StructField("sku",              StringType(),       nullable=True),
    StructField("unit_cost",        DecimalType(10, 2), nullable=True),
    StructField("unit_price",       DecimalType(10, 2), nullable=True),
    StructField("stock_qty",        IntegerType(),      nullable=True),
    StructField("reorder_point",    IntegerType(),      nullable=True),
    StructField("is_active",        BooleanType(),      nullable=True),
    StructField("supplier_id",      StringType(),       nullable=True),
    StructField("weight_kg",        DoubleType(),       nullable=True),
    StructField("warranty_months",  IntegerType(),      nullable=True),
])


# ---------------------------------------------------------------------------
# DataFrame creation helpers
# ---------------------------------------------------------------------------

def create_from_list(
    spark: SparkSession,
    data: List,
    schema: StructType,
) -> DataFrame:
    """
    Create a Spark DataFrame from a Python list of tuples or Row objects.

    Args:
        spark  : Active SparkSession.
        data   : List of tuples matching the schema column order.
        schema : StructType schema for the DataFrame.

    Returns:
        Spark DataFrame.

    Example::

        rows = [("S001", "2024-01-01", "C101", 100.0)]
        df = create_from_list(spark, rows, my_schema)
    """
    df = spark.createDataFrame(data, schema=schema)
    logger.info("Created DataFrame with %d rows from list", df.count())
    return df


def create_sample_sales(spark: SparkSession) -> DataFrame:
    """
    Create a small in-memory sales DataFrame for demos and tests.

    Returns:
        Spark DataFrame with 5 sales records.
    """
    from pyspark.sql import Row
    from datetime import date
    from decimal import Decimal

    rows = [
        Row(sale_id="S001", order_date=date(2024, 1, 3), customer_id="C101",
            product_id="P201", product_name="Laptop Pro 15", category="Electronics",
            region="North", salesperson="Alice Johnson", quantity=1,
            unit_price=Decimal("1200.00"), discount_pct=5.0,
            total_amount=Decimal("1140.00"), status="Completed"),
        Row(sale_id="S002", order_date=date(2024, 1, 5), customer_id="C102",
            product_id="P202", product_name="Wireless Mouse", category="Electronics",
            region="South", salesperson="Bob Smith", quantity=3,
            unit_price=Decimal("25.00"), discount_pct=0.0,
            total_amount=Decimal("75.00"), status="Completed"),
        Row(sale_id="S003", order_date=date(2024, 1, 7), customer_id="C103",
            product_id="P203", product_name="Office Chair", category="Furniture",
            region="East", salesperson="Carol White", quantity=2,
            unit_price=Decimal("350.00"), discount_pct=10.0,
            total_amount=Decimal("630.00"), status="Completed"),
        Row(sale_id="S004", order_date=date(2024, 1, 9), customer_id="C104",
            product_id="P204", product_name="Standing Desk", category="Furniture",
            region="West", salesperson="David Brown", quantity=1,
            unit_price=Decimal("600.00"), discount_pct=0.0,
            total_amount=Decimal("600.00"), status="Shipped"),
        Row(sale_id="S005", order_date=date(2024, 1, 11), customer_id="C105",
            product_id="P205", product_name="USB Hub 7-Port", category="Electronics",
            region="North", salesperson="Alice Johnson", quantity=5,
            unit_price=Decimal("30.00"), discount_pct=0.0,
            total_amount=Decimal("150.00"), status="Completed"),
    ]
    return spark.createDataFrame(rows, schema=SALES_SCHEMA)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def read_csv(
    spark: SparkSession,
    path: str,
    schema: Optional[StructType] = None,
    header: bool = True,
    infer_schema: bool = False,
    date_format: str = "yyyy-MM-dd",
    timestamp_format: str = "yyyy-MM-dd'T'HH:mm:ss",
    null_value: str = "",
) -> DataFrame:
    """
    Read a CSV file into a Spark DataFrame with production-safe options.

    Args:
        spark            : Active SparkSession.
        path             : File or directory path (supports glob patterns).
        schema           : Explicit StructType; if None, uses inferSchema.
        header           : Whether the first row is a header.
        infer_schema     : Infer column types (slow for large files).
        date_format      : Date format string for DateType columns.
        timestamp_format : Timestamp format string.
        null_value       : String that represents NULL.

    Returns:
        Spark DataFrame.

    Performance Note:
        Always supply an explicit schema for production CSV reads to avoid
        the two-pass scan that inferSchema triggers.
    """
    reader = (
        spark.read
        .option("header", str(header).lower())
        .option("dateFormat", date_format)
        .option("timestampFormat", timestamp_format)
        .option("nullValue", null_value)
        .option("mode", "PERMISSIVE")          # rows with bad fields → nulls
        .option("columnNameOfCorruptRecord", "_corrupt_record")
    )
    if schema:
        reader = reader.schema(schema)
    elif infer_schema:
        reader = reader.option("inferSchema", "true")

    df = reader.csv(path)
    logger.info("Read CSV from '%s': %d columns", path, len(df.columns))
    return df


def read_json(
    spark: SparkSession,
    path: str,
    schema: Optional[StructType] = None,
    multiline: bool = True,
) -> DataFrame:
    """
    Read a JSON file (array or JSONL) into a Spark DataFrame.

    Args:
        spark     : Active SparkSession.
        path      : File path or directory.
        schema    : Explicit schema; if None, schema is inferred.
        multiline : True for JSON arrays (standard); False for JSONL.

    Returns:
        Spark DataFrame.
    """
    reader = spark.read.option("multiline", str(multiline).lower())
    if schema:
        reader = reader.schema(schema)
    df = reader.json(path)
    logger.info("Read JSON from '%s': %d columns", path, len(df.columns))
    return df


def read_parquet(
    spark: SparkSession,
    path: str,
    schema: Optional[StructType] = None,
) -> DataFrame:
    """
    Read Parquet file(s) into a Spark DataFrame.

    Args:
        spark  : Active SparkSession.
        path   : Path or glob pattern.
        schema : Optional schema override (rarely needed – Parquet is self-describing).

    Returns:
        Spark DataFrame.
    """
    reader = spark.read
    if schema:
        reader = reader.schema(schema)
    df = reader.parquet(path)
    logger.info("Read Parquet from '%s': %d columns", path, len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def write_parquet(
    df: DataFrame,
    path: str,
    mode: str = "overwrite",
    partition_by: Optional[List[str]] = None,
    compression: str = "snappy",
) -> None:
    """
    Write a DataFrame to Parquet format.

    Args:
        df           : Source DataFrame.
        path         : Output path (S3, ADLS, local).
        mode         : overwrite | append | ignore | errorIfExists.
        partition_by : List of column names to partition the output by.
        compression  : snappy | gzip | lz4 | zstd | none.

    Production Note:
        Partitioning by (year, month) or (category, region) dramatically
        speeds up downstream queries by enabling partition pruning.
    """
    writer = df.write.mode(mode).option("compression", compression)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(path)
    logger.info("Written Parquet to '%s' (mode=%s)", path, mode)


def write_csv(
    df: DataFrame,
    path: str,
    mode: str = "overwrite",
    header: bool = True,
    coalesce: int = 1,
) -> None:
    """
    Write a DataFrame to CSV.

    Args:
        df       : Source DataFrame.
        path     : Output path.
        mode     : Write mode.
        header   : Include column names as header row.
        coalesce : Number of output files (1 = single file for small datasets).

    Warning:
        coalesce(1) shuffles ALL data to a single executor – suitable only
        for small exports.  Use for reporting outputs only.
    """
    df.coalesce(coalesce).write.mode(mode).option("header", str(header).lower()).csv(path)
    logger.info("Written CSV to '%s' (mode=%s, files=%d)", path, mode, coalesce)


def write_delta(
    df: DataFrame,
    path: str,
    mode: str = "overwrite",
    partition_by: Optional[List[str]] = None,
) -> None:
    """
    Write a DataFrame to Delta Lake format (requires Delta Lake on classpath).

    Args:
        df           : Source DataFrame.
        path         : Delta table path.
        mode         : overwrite | append | ignore | errorIfExists.
        partition_by : Partition columns for the Delta table.

    Note:
        Delta Lake provides ACID transactions, schema enforcement, and
        time-travel – the gold standard for lakehouse storage.
    """
    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.save(path)
    logger.info("Written Delta Lake to '%s' (mode=%s)", path, mode)


# ---------------------------------------------------------------------------
# Schema utilities
# ---------------------------------------------------------------------------

def print_schema_summary(df: DataFrame) -> None:
    """Print schema, column count, and row count for debugging."""
    print(f"\n{'='*60}")
    print(f"Columns : {len(df.columns)}")
    print(f"Rows    : {df.count()}")
    print("Schema  :")
    df.printSchema()
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark

    spark = get_spark("DataFrameBasicsDemo")

    # 1. Create from in-memory data
    df_sales = create_sample_sales(spark)
    print("=== In-Memory Sales DataFrame ===")
    df_sales.show(truncate=False)
    print_schema_summary(df_sales)

    # 2. Read CSV with explicit schema
    csv_path = "sample-data/sales_data.csv"
    df_csv = read_csv(spark, csv_path, schema=SALES_SCHEMA)
    print("=== CSV Sales Data ===")
    df_csv.show(5)

    # 3. Read JSON
    json_path = "sample-data/customer_events.json"
    df_json = read_json(spark, json_path, schema=CUSTOMER_EVENT_SCHEMA)
    print("=== Customer Events JSON ===")
    df_json.show(5)

    spark.stop()
