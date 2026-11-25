"""
aggregations.py
===============
Advanced PySpark grouping and aggregation techniques: groupBy, pivot, rollup, cube.

Business Use Case:
    Multi-dimensional analytical reporting (OLAP cubes) for e-commerce performance.
    Data analysts need sales summaries aggregated by Category, Region, and Salesperson,
    along with sub-totals and grand totals in a single efficient query.

Production Patterns Covered:
    - Standard groupBy with multiple aggregate functions (sum, avg, countDistinct, collect_list)
    - Pivot tables with pre-filtered distinct values (for performance)
    - Rollup (hierarchical aggregations: total, regional total, category total)
    - Cube (all possible combinations of dimensions)
    - grouping_id() to differentiate aggregation levels in Rollup/Cube output

Interview Questions:
    Q: What is the performance danger of using pivot() in PySpark?
    A: Without explicit pivot values, PySpark performs an extra pass over the dataset
       to discover all unique values of the pivot column. Always pass explicit values
       (e.g. `pivot("region", ["North", "South", "East", "West"])`) in production.

    Q: What is the difference between ROLLUP and CUBE?
    A: ROLLUP generates hierarchical sub-totals along the specified column order:
       (A, B, C), (A, B), (A), (). CUBE generates all N^2 combinations of dimensions:
       (A, B, C), (A, B), (A, C), (B, C), (A), (B), (C), ().

    Q: What is grouping_id()?
    A: A bitmask integer returned by Spark indicating which columns are aggregated (NULLed)
       in a ROLLUP or CUBE output row. Allows downstream filters to pinpoint specific totals.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def group_by_multi_dim(
    df: DataFrame,
    group_cols: List[str],
) -> DataFrame:
    """
    Perform multi-column groupBy with rich aggregate metrics:
    - total_revenue: sum of total_amount
    - total_quantity: sum of quantity
    - avg_order_value: average total_amount
    - unique_customers: distinct count of customer_id
    - customer_list: collect list of distinct customer IDs

    Args:
        df: Input sales DataFrame.
        group_cols: List of column names to group by.

    Returns:
        Aggregated DataFrame.
    """
    logger.info("Executing groupBy on columns: %s", group_cols)
    return (
        df.groupBy(*group_cols)
        .agg(
            F.round(F.sum("total_amount"), 2).alias("total_revenue"),
            F.sum("quantity").alias("total_quantity"),
            F.round(F.avg("total_amount"), 2).alias("avg_order_value"),
            F.countDistinct("customer_id").alias("unique_customers"),
            F.collect_set("customer_id").alias("distinct_customers"),
        )
        .orderBy(F.col("total_revenue").desc())
    )


def pivot_sales_by_region(
    df: DataFrame,
    pivot_col: str = "region",
    pivot_values: Optional[List[str]] = None,
) -> DataFrame:
    """
    Pivot sales data to convert region rows into separate columns showing total revenue.

    Production Tip:
    Pass `pivot_values` explicitly to avoid an extra scan stage to infer unique values.

    Args:
        df: Input sales DataFrame.
        pivot_col: Column to pivot (e.g. 'region').
        pivot_values: Optional list of known values for performance optimization.

    Returns:
        Pivoted DataFrame with categories as rows and regions as columns.
    """
    logger.info("Pivoting column '%s' with explicit values: %s", pivot_col, pivot_values)
    grouped = df.groupBy("category")

    if pivot_values:
        pivoted = grouped.pivot(pivot_col, pivot_values)
    else:
        pivoted = grouped.pivot(pivot_col)

    return pivoted.agg(F.round(F.sum("total_amount"), 2)).na.fill(0.0)


def hierarchical_rollup(
    df: DataFrame,
    hierarchy_cols: List[str] = ["category", "region"],
) -> DataFrame:
    """
    Perform hierarchical aggregation using ROLLUP.

    Generates sub-totals at each hierarchy level and a grand total row.
    Uses grouping_id() to identify the aggregation level.

    Args:
        df: Input sales DataFrame.
        hierarchy_cols: Ordered hierarchy columns [Category -> Region].

    Returns:
        DataFrame containing sub-totals and grand totals.
    """
    logger.info("Performing ROLLUP hierarchy: %s", hierarchy_cols)
    return (
        df.rollup(*hierarchy_cols)
        .agg(
            F.round(F.sum("total_amount"), 2).alias("total_revenue"),
            F.sum("quantity").alias("total_units"),
            F.count("sale_id").alias("order_count"),
            F.grouping_id().alias("grouping_level"),
        )
        .orderBy(*hierarchy_cols)
    )


def multidimensional_cube(
    df: DataFrame,
    cube_cols: List[str] = ["category", "region", "status"],
) -> DataFrame:
    """
    Perform multi-dimensional aggregation across all column combinations using CUBE.

    Args:
        df: Input sales DataFrame.
        cube_cols: List of dimensions for CUBE.

    Returns:
        DataFrame with aggregate rows for all 2^N combination of dimensions.
    """
    logger.info("Performing CUBE aggregation across: %s", cube_cols)
    return (
        df.cube(*cube_cols)
        .agg(
            F.round(F.sum("total_amount"), 2).alias("total_revenue"),
            F.count("sale_id").alias("order_count"),
            F.grouping_id().alias("grouping_level"),
        )
        .orderBy(*cube_cols)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("AggregationsDemo")
    sales = create_sample_sales(spark)

    print("=== Multi-Dimensional GroupBy (Category, Region) ===")
    group_by_multi_dim(sales, ["category", "region"]).show()

    print("=== Pivoted Sales (Category x Region) ===")
    pivot_sales_by_region(sales, "region", ["North", "South", "East", "West"]).show()

    print("=== Hierarchical Rollup ===")
    hierarchical_rollup(sales, ["category", "region"]).show()

    spark.stop()
