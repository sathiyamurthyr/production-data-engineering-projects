"""
window_functions.py
===================
Advanced PySpark window functions for ranking, time-series calculations, and moving aggregates.

Business Use Case:
    Customer analytics, sales ranking, period-over-period revenue growth analysis,
    and rolling average calculations for sales performance dashboards.

Key Window Concepts:
    - Partitioning (partitionBy) -> Defines data groups (like SQL PARTITION BY).
    - Ordering (orderBy) -> Specifies row sequencing within partition.
    - Frame Specification (rowsBetween / rangeBetween) -> Defines physical or logical boundary.

Interview Questions:
    Q: Difference between row_number(), rank(), and dense_rank()?
    A: For duplicate ordering values:
       - row_number(): Unique sequence numbers (1, 2, 3, 4, 5).
       - rank(): Identical ranks for ties, skips subsequent rank numbers (1, 2, 2, 4, 5).
       - dense_rank(): Identical ranks for ties, DOES NOT skip rank numbers (1, 2, 2, 3, 4).

    Q: Why is an unbound window without partitionBy dangerous in PySpark?
    A: Calling `Window.orderBy("date")` without `partitionBy` forces ALL dataset rows
       into a SINGLE partition on one executor node, causing OOM (Out Of Memory) errors.

    Q: What is the difference between rowsBetween() and rangeBetween()?
    A: rowsBetween uses physical row offsets (e.g. -2 to CURRENT ROW).
       rangeBetween uses logical value differences on the sorting column (e.g. 7 days prior).
"""

from __future__ import annotations

import logging
from typing import Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window, WindowSpec

logger = logging.getLogger(__name__)


def calculate_sales_ranks(df: DataFrame) -> DataFrame:
    """
    Calculate rank, dense_rank, and row_number for sales transactions within each region
    ordered by total_amount descending.

    Args:
        df: Input sales DataFrame.

    Returns:
        DataFrame with row_num, rank, and dense_rank columns.
    """
    window_spec: WindowSpec = Window.partitionBy("region").orderBy(F.col("total_amount").desc())

    logger.info("Computing sales ranks partitioned by region")
    return (
        df
        .withColumn("row_num", F.row_number().over(window_spec))
        .withColumn("rank", F.rank().over(window_spec))
        .withColumn("dense_rank", F.dense_rank().over(window_spec))
    )


def calculate_top_n_per_category(df: DataFrame, top_n: int = 3) -> DataFrame:
    """
    Extract top N sales records for each category based on total_amount.

    Args:
        df: Input sales DataFrame.
        top_n: Number of top records to select per group.

    Returns:
        Filtered DataFrame containing top N records per category.
    """
    window_spec = Window.partitionBy("category").orderBy(F.col("total_amount").desc())

    ranked_df = df.withColumn("rank_in_cat", F.dense_rank().over(window_spec))
    result = ranked_df.filter(F.col("rank_in_cat") <= top_n).drop("rank_in_cat")

    logger.info("Retrieved top %d sales per category", top_n)
    return result


def calculate_lead_lag_sales(df: DataFrame) -> DataFrame:
    """
    Compute previous order amount (lag) and next order amount (lead) per customer
    ordered by order_date, along with period-over-period change amount.

    Args:
        df: Input sales DataFrame.

    Returns:
        DataFrame with prev_amount, next_amount, and amount_change columns.
    """
    customer_window = Window.partitionBy("customer_id").orderBy("order_date")

    logger.info("Calculating lead/lag metrics per customer")
    return (
        df
        .withColumn("prev_order_amount", F.lag("total_amount", 1, 0.0).over(customer_window))
        .withColumn("next_order_amount", F.lead("total_amount", 1, 0.0).over(customer_window))
        .withColumn(
            "amount_change",
            F.round(F.col("total_amount") - F.col("prev_order_amount"), 2)
        )
    )


def calculate_running_totals_and_moving_avg(
    df: DataFrame,
    window_size: int = 3,
) -> DataFrame:
    """
    Compute cumulative total revenue and moving average over a rolling window.

    - Running Total: Unbounded preceding to current row.
    - Moving Average: Rolling window of size `window_size` (current row and preceding N-1 rows).

    Args:
        df: Input sales DataFrame.
        window_size: Number of rows to include in moving average frame.

    Returns:
        DataFrame with cumulative_revenue and moving_avg_revenue columns.
    """
    # Cumulative window (from start of time to current row)
    cumulative_window = (
        Window.partitionBy("region")
        .orderBy("order_date")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )

    # Rolling window (current row and preceding N-1 rows)
    rolling_window = (
        Window.partitionBy("region")
        .orderBy("order_date")
        .rowsBetween(-(window_size - 1), Window.currentRow)
    )

    logger.info("Computing cumulative total and %d-period moving average", window_size)
    return (
        df
        .withColumn("cumulative_revenue", F.round(F.sum("total_amount").over(cumulative_window), 2))
        .withColumn("moving_avg_revenue", F.round(F.avg("total_amount").over(rolling_window), 2))
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("WindowFunctionsDemo")
    sales = create_sample_sales(spark)

    print("=== Regional Sales Ranks ===")
    calculate_sales_ranks(sales).select("sale_id", "region", "total_amount", "row_num", "rank", "dense_rank").show()

    print("=== Top 2 Sales per Category ===")
    calculate_top_n_per_category(sales, top_n=2).select("sale_id", "category", "total_amount").show()

    print("=== Running Totals and Moving Averages ===")
    calculate_running_totals_and_moving_avg(sales).select("sale_id", "region", "order_date", "total_amount", "cumulative_revenue", "moving_avg_revenue").show()

    spark.stop()
