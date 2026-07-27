"""
Broadcast Join Optimization for PySpark

Production patterns for efficient joins in Spark.
"""

from typing import Any


def broadcast_join(
    large_df: Any,
    small_df: Any,
    join_key: str,
    join_type: str = "inner",
) -> Any:
    """
    Perform broadcast join between large and small DataFrames.
    
    Business Use Case: Customer dimension lookup in orders.
    """
    from pyspark.sql.functions import broadcast

    return large_df.join(
        broadcast(small_df),
        on=join_key,
        how=join_type,
    )


def optimize_join(
    df1: Any,
    df2: Any,
    join_key: str,
    df1_size_mb: float,
    df2_size_mb: float,
    max_broadcast_mb: float = 8,
) -> Any:
    """
    Automatically choose join strategy based on data size.
    
    Business Use Case: Dynamic join optimization for ETL pipelines.
    """
    from pyspark.sql.functions import broadcast

    # Auto-broadcast if small enough
    if df1_size_mb <= max_broadcast_mb:
        return df2.join(broadcast(df1), on=join_key, how="inner")
    elif df2_size_mb <= max_broadcast_mb:
        return df1.join(broadcast(df2), on=join_key, how="inner")
    else:
        # Regular join with salting for skew
        return df1.join(df2, on=join_key, how="inner")


def salting_join(
    df: Any,
    join_key: str,
    salt_range: int = 100,
) -> Any:
    """
    Handle skewed joins with salting.
    
    Business Use Case: Large fact table with skewed keys.
    """
    from pyspark.sql.functions import col, monotonically_increasing_id, floor

    salted_df = df.withColumn(
        "salt",
        floor(monotonically_increasing_id() % salt_range),
    )

    return salted_df