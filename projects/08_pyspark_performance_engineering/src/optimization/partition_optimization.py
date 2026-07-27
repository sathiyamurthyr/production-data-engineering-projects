"""
Partition Optimization for PySpark Performance

Production tuning for partition sizing and coalescing.
"""

from typing import Any


def optimize_partitions(
    df: Any,
    target_size_mb: int = 128,
) -> Any:
    """
    Optimize partition count based on data size.
    
    Business Use Case: Large fact table partitioning.
    """
    # Estimate partition count based on target size
    df_size_bytes = df.rdd.map(lambda row: len(str(row))).sum()
    target_size_bytes = target_size_mb * 1024 * 1024
    optimal_partitions = max(1, df_size_bytes // target_size_bytes)

    return df.coalesce(optimal_partitions)


def repartition_for_join(
    df: Any,
    join_key: str,
) -> Any:
    """
    Repartition for join optimization.
    
    Business Use Case: Pre-shuffle join optimization.
    """
    return df.repartition(join_key)


def analyze_partition_stats(
    df: Any,
) -> dict[str, Any]:
    """
    Analyze partition statistics.
    
    Business Use Case: Spark UI analysis.
    """
    partition_sizes = df.rdd.glom().map(len).collect()

    return {
        "num_partitions": len(partition_sizes),
        "min_partition_size": min(partition_sizes) if partition_sizes else 0,
        "max_partition_size": max(partition_sizes) if partition_sizes else 0,
        "avg_partition_size": sum(partition_sizes) / len(partition_sizes) if partition_sizes else 0,
    }