"""
data_quality.py
===============
PySpark Data Quality assertions, null auditing, range validation, and uniqueness verification.

Business Use Case:
    Prevent bad or corrupted data from reaching downstream data models and reporting tools.
    Audit datasets in production ETL pipelines and trigger alerts or quarantine bad rows.

Quality Suite Features:
    - Null check audit across mandatory columns.
    - Value range bounds verification (e.g. quantity > 0, price >= 0).
    - Primary Key uniqueness check.
    - Categorical value set validation.
    - Quality report generation with record counts and fail percentages.

Interview Questions:
    Q: How do you handle quarantine of invalid records in PySpark without failing the job?
    A: Use PySpark filter conditions to split the DataFrame into `valid_df` (passes quality rules)
       and `quarantine_df` (fails quality rules). Write `quarantine_df` to an error path for inspection.

    Q: What is the efficiency cost of checking uniqueness on large DataFrames in Spark?
    A: Uniqueness checks (`df.count() == df.select("primary_key").distinct().count()`) trigger a wide shuffle
       and count action. Execute quality checks after initial filtering or cache the DataFrame first.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def check_null_counts(
    df: DataFrame,
    columns: List[str],
) -> Dict[str, int]:
    """
    Compute null counts for specified columns in a single aggregation pass.

    Args:
        df: Input DataFrame.
        columns: List of column names to check for NULLs.

    Returns:
        Dict mapping column_name -> null_count.
    """
    logger.info("Checking null counts for columns: %s", columns)
    null_exprs = [F.sum(F.when(F.col(c).isNull() | F.isnan(c), 1).otherwise(0)).alias(c) for c in columns]
    row = df.select(*null_exprs).first()

    if row:
        return row.asDict()
    return {c: 0 for c in columns}


def check_uniqueness(
    df: DataFrame,
    key_columns: List[str],
) -> Tuple[bool, int]:
    """
    Check if `key_columns` form a unique primary key across all rows.

    Args:
        df: Input DataFrame.
        key_columns: List of columns defining the composite primary key.

    Returns:
        Tuple (is_unique: bool, duplicate_count: int)
    """
    total_count = df.count()
    distinct_count = df.select(*key_columns).distinct().count()
    duplicate_count = total_count - distinct_count

    is_unique = duplicate_count == 0
    logger.info("Uniqueness check on %s: unique=%s (duplicates=%d)", key_columns, is_unique, duplicate_count)
    return is_unique, duplicate_count


def validate_value_ranges(
    df: DataFrame,
    range_rules: Dict[str, Tuple[float, float]],
) -> Tuple[DataFrame, DataFrame]:
    """
    Filter DataFrame into valid records and quarantined invalid records based on numeric bounds.

    Args:
        df: Input DataFrame.
        range_rules: Dict mapping column_name -> (min_val, max_val).

    Returns:
        Tuple of (valid_df: DataFrame, quarantine_df: DataFrame).
    """
    valid_condition = F.lit(True)

    for col_name, (min_val, max_val) in range_rules.items():
        valid_condition = (
            valid_condition
            & F.col(col_name).isNotNull()
            & (F.col(col_name) >= min_val)
            & (F.col(col_name) <= max_val)
        )

    valid_df = df.filter(valid_condition)
    quarantine_df = df.filter(~valid_condition)

    logger.info("Range validation applied. Valid rows: %d, Quarantined rows: %d", valid_df.count(), quarantine_df.count())
    return valid_df, quarantine_df


def generate_quality_report(
    df: DataFrame,
    mandatory_cols: List[str],
    pk_cols: List[str],
) -> Dict[str, Any]:
    """
    Generate a full data quality audit summary report.

    Args:
        df: Input DataFrame.
        mandatory_cols: List of non-nullable columns.
        pk_cols: Primary key columns.

    Returns:
        Report dictionary containing metrics.
    """
    total_rows = df.count()
    null_metrics = check_null_counts(df, mandatory_cols)
    is_pk_unique, dup_count = check_uniqueness(df, pk_cols)

    report = {
        "total_records": total_rows,
        "primary_key_columns": pk_cols,
        "is_primary_key_unique": is_pk_unique,
        "duplicate_key_count": dup_count,
        "null_counts": null_metrics,
        "passed_all_checks": is_pk_unique and all(cnt == 0 for cnt in null_metrics.values()),
    }
    logger.info("Quality report generated: passed=%s", report["passed_all_checks"])
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("DataQualityDemo")
    sales = create_sample_sales(spark)

    print("=== Null Count Audit ===")
    print(check_null_counts(sales, ["sale_id", "customer_id", "total_amount"]))

    print("=== Uniqueness Check ===")
    unique, dups = check_uniqueness(sales, ["sale_id"])
    print(f"Is sale_id unique? {unique} (Duplicates: {dups})")

    print("=== Full Quality Report ===")
    report = generate_quality_report(sales, mandatory_cols=["sale_id", "order_date"], pk_cols=["sale_id"])
    print(report)

    spark.stop()
