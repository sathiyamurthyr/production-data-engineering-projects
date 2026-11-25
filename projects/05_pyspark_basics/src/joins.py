"""
joins.py
========
PySpark join strategies, broadcast hints, left anti/semi joins, and skew optimization.

Business Use Case:
    Enriching transactional sales streams with dimensions (Customer, Product) across
    large data lakes, eliminating duplicate columns, and handling skewed keys efficiently.

Supported Join Types in PySpark:
    - inner: Returns matching keys in both DataFrames.
    - left / left_outer: All left rows, matching right rows (NULL if no match).
    - right / right_outer: All right rows, matching left rows (NULL if no match).
    - full / outer: All rows from both sides with NULLs filled where un-matched.
    - left_semi: Returns left rows that HAVE a match in right (NO right columns returned).
    - left_anti: Returns left rows that DO NOT have a match in right.
    - cross: Cartesian product (N x M rows) - extreme memory warning!

Interview Questions:
    Q: How does Broadcast Hash Join (BHJ) work and when should you use it?
    A: BHJ copies the smaller DataFrame (<10 MB by default, configured via
       `spark.sql.autoBroadcastJoinThreshold`) to all worker executors.
       It avoids the costly network shuffle of the large DataFrame.

    Q: What is the difference between left_semi and inner join?
    A: left_semi join only returns columns from the left DataFrame and deduplicates
       multiple matches on the right, equivalent to `WHERE EXISTS (SELECT 1 ...)`.

    Q: How do you resolve key skew during large table joins in Spark?
    A: 1) Enable AQE skew join (`spark.sql.adaptive.skewJoin.enabled=true`).
       2) Salting: Append random numbers (0..N) to skewed join keys in the left table
          and explode the right lookup table with 0..N values to distribute load.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def execute_standard_join(
    df_left: DataFrame,
    df_right: DataFrame,
    join_key: str,
    join_type: str = "inner",
) -> DataFrame:
    """
    Perform a standard join between two DataFrames using a single join key.

    Using `on="key_name"` automatically coalesces the join column so duplicate key
    columns do not appear in the resulting DataFrame.

    Args:
        df_left: Left DataFrame.
        df_right: Right DataFrame.
        join_key: Column name present in both DataFrames.
        join_type: One of ('inner', 'left', 'right', 'full', 'left_semi', 'left_anti').

    Returns:
        Joined DataFrame.
    """
    logger.info("Performing standard %s join on key '%s'", join_type, join_key)
    return df_left.join(df_right, on=join_key, how=join_type)


def execute_broadcast_join(
    large_df: DataFrame,
    small_df: DataFrame,
    join_key: str,
    join_type: str = "inner",
) -> DataFrame:
    """
    Perform a Broadcast Hash Join (BHJ) by broadcasting the small DataFrame to all executors.

    Args:
        large_df: Large target DataFrame.
        small_df: Dimension or lookup DataFrame (small enough to fit in executor memory).
        join_key: Column name for matching.
        join_type: Join strategy.

    Returns:
        Joined DataFrame without shuffle stage.
    """
    logger.info("Executing Broadcast Join on key '%s'", join_key)
    return large_df.join(F.broadcast(small_df), on=join_key, how=join_type)


def filter_unmatched_records_anti_join(
    events_df: DataFrame,
    customers_df: DataFrame,
    join_key: str = "customer_id",
) -> DataFrame:
    """
    Use Left Anti Join to find events belonging to unknown / unregistered customers.

    Args:
        events_df: Left DataFrame (Customer Events).
        customers_df: Right DataFrame (Valid Customers List).
        join_key: Shared identifier.

    Returns:
        DataFrame containing events whose customer_id is missing from customers_df.
    """
    logger.info("Filtering unmatched records using left_anti join")
    return events_df.join(customers_df, on=join_key, how="left_anti")


def filter_active_customers_semi_join(
    customers_df: DataFrame,
    sales_df: DataFrame,
    join_key: str = "customer_id",
) -> DataFrame:
    """
    Use Left Semi Join to retrieve customer records who have made at least one purchase.

    Unlike inner join, left_semi join guarantees no row duplication if a customer
    has multiple sales transactions.

    Args:
        customers_df: Customer master DataFrame.
        sales_df: Transactional sales DataFrame.
        join_key: Shared customer ID column.

    Returns:
        Deduplicated customers DataFrame with existing sales.
    """
    logger.info("Retrieving purchasing customers using left_semi join")
    return customers_df.join(sales_df, on=join_key, how="left_semi")


def apply_salted_join(
    large_skewed_df: DataFrame,
    lookup_df: DataFrame,
    join_key: str,
    salt_factor: int = 4,
) -> DataFrame:
    """
    Perform a salted join to mitigate severe key skew on `join_key`.

    Technique:
    1. Add a random salt integer (0 to salt_factor-1) to the skewed DataFrame.
    2. Explode the lookup table key with an array of all possible salt values (0 to salt_factor-1).
    3. Join on (join_key, salt_col) to distribute skewed keys across multiple executors.

    Args:
        large_skewed_df: Data frame with skewed key distribution.
        lookup_df: Lookup DataFrame.
        join_key: Target column for join.
        salt_factor: Number of salt buckets.

    Returns:
        Joined DataFrame free of single-executor bottleneck.
    """
    logger.info("Applying salted join with salt_factor=%d on key '%s'", salt_factor, join_key)

    # 1. Salt left side with random int [0, salt_factor)
    salted_left = large_skewed_df.withColumn(
        "_salt_key", (F.rand() * salt_factor).cast("int")
    )

    # 2. Replicate lookup side with array of [0, 1, ..., salt_factor-1] and explode
    salt_array = F.array([F.lit(i) for i in range(salt_factor)])
    exploded_right = lookup_df.withColumn("_salt_array", salt_array).withColumn(
        "_salt_key", F.explode(F.col("_salt_array"))
    ).drop("_salt_array")

    # 3. Join on both original key AND salt key
    joined = salted_left.join(
        exploded_right,
        on=[join_key, "_salt_key"],
        how="inner",
    ).drop("_salt_key")

    return joined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales, PRODUCT_SCHEMA

    spark = get_spark("JoinsDemo")
    sales = create_sample_sales(spark)

    # Create dummy products
    prod_data = [
        ("P201", "Laptop Pro 15", "Electronics", "TechBrand"),
        ("P202", "Wireless Mouse", "Electronics", "ClickMaster"),
    ]
    prod_cols = ["product_id", "product_name", "category", "brand"]
    products = spark.createDataFrame(prod_data, prod_cols)

    print("=== Broadcast Join ===")
    execute_broadcast_join(sales, products, join_key="product_id", join_type="left").show()

    print("=== Left Semi Join (Customers who made purchases) ===")
    cust_data = [("C101", "Alice"), ("C102", "Bob"), ("C999", "NoPurchaseUser")]
    customers = spark.createDataFrame(cust_data, ["customer_id", "name"])
    filter_active_customers_semi_join(customers, sales).show()

    spark.stop()
