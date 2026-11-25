"""
Module: delta_constraints.py
============================
Delta Lake data quality enforcement using CHECK constraints, NOT NULL constraints, and Generated Columns.

Business Use Case:
    Data quality errors (e.g. negative prices, null user IDs, invalid status codes) corrupt downstream reports
    and break ML pipelines if unmanaged.
    Traditional object store formats (Parquet, ORC, CSV) have zero schema/quality checks on write.
    Delta Lake enforces constraints at the engine level during write transactions. If incoming data violates
    a `NOT NULL` or `CHECK` constraint, Delta aborts the transaction, preventing bad data from entering the Lakehouse.

Types of Constraints:
    1. NOT NULL: Enforces that specific columns cannot contain null values.
    2. CHECK constraints: Custom boolean SQL expressions (e.g., `amount >= 0.0 AND age >= 18`).
    3. Generated Columns: Automatically computed columns derived from other columns (e.g., date derived from timestamp).

Interview Questions:
    Q: What happens when a batch write contains 1 million rows, and 1 row violates a CHECK constraint?
    A: Delta Lake throws an InvariantViolationException and ABORTS the entire transaction.
       Zero rows are written to the table (Atomicity).

    Q: How do Generated Columns optimize partition pruning in Delta Lake?
    A: If a table is partitioned by a generated date column `date GENERATED ALWAYS AS (CAST(ts AS DATE))`,
       Delta automatically rewrites queries filtering on `ts` (e.g. `WHERE ts >= '2026-03-01 10:00:00'`) to include
       filters on the partition column `date`, enabling transparent partition pruning without requiring explicit date filters in SQL.
"""

import logging
from typing import Dict, Any, List
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

logger = logging.getLogger(__name__)


def create_table_with_constraints(
    spark: SparkSession,
    table_path: str,
    schema: StructType
) -> None:
    """
    Create a Delta table at table_path with specified schema.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Target table file system path.
    schema : StructType
        PySpark schema definition.
    """
    logger.info("Creating initial empty Delta table at '%s'", table_path)
    empty_df = spark.createDataFrame([], schema)
    empty_df.write.format("delta").mode("overwrite").save(table_path)


def add_check_constraint(
    spark: SparkSession,
    table_path: str,
    constraint_name: str,
    expression: str
) -> None:
    """
    Add a SQL CHECK constraint to a Delta table.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    constraint_name : str
        Unique constraint name identifier (e.g., 'valid_amount').
    expression : str
        SQL boolean expression (e.g., 'amount >= 0.0').
    """
    logger.info("Adding constraint '%s' (%s) to '%s'", constraint_name, expression, table_path)
    sql = f"ALTER TABLE delta.`{table_path}` ADD CONSTRAINT {constraint_name} CHECK ({expression})"
    spark.sql(sql)
    logger.info("Constraint '%s' added successfully", constraint_name)


def drop_check_constraint(
    spark: SparkSession,
    table_path: str,
    constraint_name: str
) -> None:
    """
    Drop an existing CHECK constraint from a Delta table.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_path : str
        Delta table directory path.
    constraint_name : str
        Name of constraint to drop.
    """
    logger.info("Dropping constraint '%s' from '%s'", constraint_name, table_path)
    sql = f"ALTER TABLE delta.`{table_path}` DROP CONSTRAINT {constraint_name}"
    spark.sql(sql)
    logger.info("Constraint '%s' dropped successfully", constraint_name)


def create_table_with_generated_columns(
    spark: SparkSession,
    table_name_or_path: str,
    is_path: bool = True
) -> None:
    """
    Create a Delta table using SQL WITH GENERATED COLUMNS.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    table_name_or_path : str
        Catalog table name or path.
    is_path : bool
        True if target is a file path, False if catalog table.
    """
    target = f"delta.`{table_name_or_path}`" if is_path else table_name_or_path
    sql = f"""
    CREATE TABLE IF NOT EXISTS {target} (
        event_id STRING NOT NULL,
        user_id STRING NOT NULL,
        event_timestamp TIMESTAMP,
        event_date DATE GENERATED ALWAYS AS (CAST(event_timestamp AS DATE)),
        amount DOUBLE
    )
    USING DELTA
    PARTITIONED BY (event_date)
    """
    logger.info("Creating table with generated columns: %s", sql)
    spark.sql(sql)
