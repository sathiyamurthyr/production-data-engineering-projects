"""
schema_handling.py
===================
StructType & StructField management, schema enforcement, DDL conversions, and schema evolution.

Business Use Case:
    Prevent data corruption in production pipelines when incoming raw files (CSV/JSON)
    have missing, reordered, or extra fields. Enforce strict contracts and handle schema drift safely.

Production Patterns:
    - StructType definition vs DDL string format.
    - Schema validation function: verify columns and data types before pipeline execution.
    - Safe schema evolution: align DataFrame schema to target table schema by adding missing columns as NULL.

Interview Questions:
    Q: What happens if an incoming CSV file has extra columns not present in your explicit StructType schema?
    A: Spark drops the extra columns silently during read (when permissive mode is default).

    Q: How do you parse DDL schema strings into PySpark StructType?
    A: `StructType.fromDDL("sale_id STRING, total_amount DECIMAL(12,2), order_date DATE")`.

    Q: Why prefer StructType programmatic schema over DDL strings in library code?
    A: Programmatic StructType schemas allow programmatic introspection, validation, unit testing,
       and type-safe metadata attachments (e.g. `metadata={"comment": "primary key"}`).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DataType, StringType, StructField, StructType

logger = logging.getLogger(__name__)


def ddl_to_schema(ddl_str: str) -> StructType:
    """
    Convert a DDL schema string to PySpark StructType.

    Example DDL string:
        "id STRING, name STRING, age INT, price DOUBLE"

    Args:
        ddl_str: SQL DDL formatted schema string.

    Returns:
        StructType representation.
    """
    logger.info("Parsing DDL string to StructType")
    return StructType.fromDDL(ddl_str)


def schema_to_ddl(schema: StructType) -> str:
    """
    Convert a StructType schema to a DDL string representation.

    Args:
        schema: StructType instance.

    Returns:
        DDL string representation.
    """
    return schema.toDDL()


def validate_schema(
    df: DataFrame,
    expected_schema: StructType,
    allow_missing: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Validate a DataFrame's actual schema against an expected target schema.

    Checks:
    - Missing required columns
    - Unexpected data types

    Args:
        df: Input DataFrame.
        expected_schema: Target StructType contract.
        allow_missing: If True, missing optional columns are flagged but don't cause validation failure.

    Returns:
        Tuple (is_valid: bool, list_of_errors: List[str])
    """
    actual_fields: Dict[str, DataType] = {f.name: f.dataType for f in df.schema.fields}
    expected_fields: Dict[str, DataType] = {f.name: f.dataType for f in expected_schema.fields}

    errors: List[str] = []

    # Check for missing columns
    for col_name, exp_type in expected_fields.items():
        if col_name not in actual_fields:
            errors.append(f"Missing column: '{col_name}' (expected type {exp_type.simpleString()})")
        else:
            actual_type = actual_fields[col_name]
            if actual_type.simpleString() != exp_type.simpleString():
                errors.append(
                    f"Type mismatch on '{col_name}': expected {exp_type.simpleString()}, got {actual_type.simpleString()}"
                )

    is_valid = len(errors) == 0
    if not is_valid:
        logger.warning("Schema validation failed with %d errors: %s", len(errors), errors)
    else:
        logger.info("Schema validation passed successfully.")

    return is_valid, errors


def enforce_schema_evolution(
    df: DataFrame,
    target_schema: StructType,
) -> DataFrame:
    """
    Align an incoming DataFrame schema to match a target table schema.

    - Adds missing target columns with NULL values.
    - Casts existing columns to match target data types.
    - Selects columns in the exact order specified by `target_schema`.

    Args:
        df: Source DataFrame with drift.
        target_schema: Desired destination StructType schema.

    Returns:
        Schema-aligned DataFrame.
    """
    logger.info("Aligning DataFrame schema to target schema (%d fields)", len(target_schema.fields))
    aligned_df = df

    # Add missing columns as NULL
    actual_cols = set(df.columns)
    for field in target_schema.fields:
        if field.name not in actual_cols:
            logger.info("Adding missing column '%name' as NULL (%s)", field.name, field.dataType)
            aligned_df = aligned_df.withColumn(field.name, F.lit(None).cast(field.dataType))
        else:
            # Cast column to expected type
            aligned_df = aligned_df.withColumn(field.name, F.col(field.name).cast(field.dataType))

    # Reorder columns to match target schema exactly
    target_col_names = [f.name for f in target_schema.fields]
    return aligned_df.select(*target_col_names)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales, SALES_SCHEMA

    spark = get_spark("SchemaHandlingDemo")
    sales = create_sample_sales(spark)

    ddl = "sale_id STRING, order_date DATE, total_amount DECIMAL(12,2)"
    st = ddl_to_schema(ddl)
    print("Parsed StructType:", st)
    print("DDL String:", schema_to_ddl(SALES_SCHEMA))

    is_valid, errs = validate_schema(sales, SALES_SCHEMA)
    print(f"Validation result: {is_valid}, Errors: {errs}")

    spark.stop()
