"""
transformations.py
==================
Core PySpark DataFrame transformations including select, filter, withColumn,
groupBy, agg, join, and union operations.

Business Use Case:
    Transform raw ingested sales data into clean, business-ready data structures
    by filtering invalid records, calculating derived metrics (e.g. net sales,
    discount amounts), and joining reference product data.

Production Best Practices:
    - Prefer withColumn / withColumns for single/multiple column additions.
    - Avoid row-by-row Python iterations; always use vectorised PySpark expressions.
    - Use unionByName(..., allowMissingColumns=True) instead of union() to avoid
      column misalignment issues when schemas differ slightly.
    - Use explicit boolean conditions with col() and ~ for clarity.

Interview Questions:
    Q: What is the difference between map() and select()?
    A: map() is an RDD transformation operating on individual Python objects.
       select() is a DataFrame transformation working with Catalyst expressions,
       enabling query optimization and code generation (Tungsten).

    Q: What is the difference between union() and unionByName()?
    A: union() resolves columns by ordinal position (index), which bugs if schemas
       have columns in different orders. unionByName() resolves by column name.

    Q: How does Spark optimize narrow vs wide transformations?
    A: Narrow (filter, select, withColumn) do not require data shuffling across
       executors and run pipelined in a single stage. Wide (groupBy, join, distinct)
       require a shuffle stage across network nodes.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, DoubleType

logger = logging.getLogger(__name__)


def select_and_rename_columns(
    df: DataFrame,
    columns_map: Dict[str, str],
) -> DataFrame:
    """
    Select specific columns and rename them according to a mapping dict.

    Args:
        df: Input DataFrame.
        columns_map: Dict mapping existing_name -> new_name.

    Returns:
        DataFrame with selected and renamed columns.
    """
    select_exprs = [F.col(old_col).alias(new_col) for old_col, new_col in columns_map.items()]
    logger.info("Selecting and renaming %d columns", len(columns_map))
    return df.select(*select_exprs)


def filter_sales(
    df: DataFrame,
    min_amount: float = 0.0,
    statuses: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> DataFrame:
    """
    Filter sales data based on total amount, transaction status, and region.

    Args:
        df: Input sales DataFrame.
        min_amount: Minimum total_amount threshold.
        statuses: List of allowed statuses (e.g. ['Completed', 'Shipped']).
        regions: List of allowed regions (e.g. ['North', 'East']).

    Returns:
        Filtered DataFrame.
    """
    condition = F.col("total_amount") >= min_amount

    if statuses:
        condition = condition & F.col("status").isin(statuses)
    if regions:
        condition = condition & F.col("region").isin(regions)

    filtered_df = df.filter(condition)
    logger.info("Filter applied: min_amount=%.2f, statuses=%s, regions=%s", min_amount, statuses, regions)
    return filtered_df


def add_derived_metrics(df: DataFrame) -> DataFrame:
    """
    Add calculated columns to the sales DataFrame:
    - gross_amount: quantity * unit_price
    - discount_amount: gross_amount * (discount_pct / 100)
    - calculated_total: gross_amount - discount_amount
    - order_year: Year extracted from order_date
    - order_month: Month extracted from order_date
    - high_value_flag: True if total_amount >= 500

    Args:
        df: Input sales DataFrame.

    Returns:
        DataFrame with added derived columns.
    """
    return (
        df
        .withColumn("gross_amount", (F.col("quantity") * F.col("unit_price")).cast(DecimalType(12, 2)))
        .withColumn(
            "discount_amount",
            (F.col("quantity") * F.col("unit_price") * (F.col("discount_pct") / F.lit(100.0))).cast(DecimalType(12, 2))
        )
        .withColumn("calculated_total", (F.col("gross_amount") - F.col("discount_amount")).cast(DecimalType(12, 2)))
        .withColumn("order_year", F.year(F.col("order_date")))
        .withColumn("order_month", F.month(F.col("order_date")))
        .withColumn("high_value_flag", F.when(F.col("total_amount") >= F.lit(500.0), True).otherwise(False))
    )


def summarize_sales_by_category(df: DataFrame) -> DataFrame:
    """
    Group sales by category and compute summary aggregations.

    Aggregations:
    - total_sales: sum(total_amount)
    - total_items: sum(quantity)
    - avg_unit_price: avg(unit_price)
    - order_count: count(sale_id)

    Args:
        df: Input sales DataFrame.

    Returns:
        Aggregated summary DataFrame.
    """
    return (
        df.groupBy("category")
        .agg(
            F.round(F.sum("total_amount"), 2).alias("total_sales"),
            F.sum("quantity").alias("total_items"),
            F.round(F.avg("unit_price"), 2).alias("avg_unit_price"),
            F.count("sale_id").alias("order_count"),
        )
        .orderBy(F.col("total_sales").desc())
    )


def join_sales_with_products(
    sales_df: DataFrame,
    products_df: DataFrame,
    join_type: str = "inner",
) -> DataFrame:
    """
    Join sales records with product catalog metadata.

    Args:
        sales_df: Sales DataFrame containing 'product_id'.
        products_df: Products DataFrame containing 'product_id'.
        join_type: Spark join type ('inner', 'left', 'right', 'outer').

    Returns:
        Joined DataFrame.
    """
    # Disambiguate duplicate columns by using product_id condition or renaming
    joined = sales_df.join(
        products_df.select("product_id", "brand", "sku", "unit_cost", "stock_qty"),
        on="product_id",
        how=join_type,
    )
    logger.info("Joined sales and products using %s join", join_type)
    return joined


def combine_sales_datasets(
    df1: DataFrame,
    df2: DataFrame,
    by_name: bool = True,
    allow_missing: bool = True,
) -> DataFrame:
    """
    Union two sales DataFrames safely.

    Args:
        df1: First DataFrame.
        df2: Second DataFrame.
        by_name: If True, resolves columns by name instead of position.
        allow_missing: If True, fills missing columns in either DF with Null.

    Returns:
        Combined DataFrame.
    """
    if by_name:
        return df1.unionByName(df2, allowMissingColumns=allow_missing)
    return df1.union(df2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("TransformationsDemo")
    sales = create_sample_sales(spark)

    print("=== Filtered Sales (Completed & total >= 500) ===")
    filter_sales(sales, min_amount=500.0, statuses=["Completed"]).show()

    print("=== Sales with Derived Metrics ===")
    add_derived_metrics(sales).select("sale_id", "quantity", "unit_price", "discount_pct", "gross_amount", "discount_amount", "calculated_total", "high_value_flag").show()

    print("=== Category Summary ===")
    summarize_sales_by_category(sales).show()

    spark.stop()
