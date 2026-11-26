"""
Module 13: Performance Tuning — Photon Engine, AQE, Disk Caching, & Shuffle Optimization
========================================================================================

Explanation:
    Databricks provides significant performance enhancements over open-source Apache Spark through
    the Photon execution engine (a native C++ vectorized query engine), Adaptive Query Execution (AQE),
    managed Disk Caching (Delta Cache), and automated shuffle/partition management.

Business Use Case:
    - Accelerating complex SQL queries and BI reporting workloads by up to 3x-5x using Photon.
    - Eliminating manual join tuning and skew mitigation through Adaptive Query Execution (AQE).
    - Reducing cloud compute costs by caching frequently accessed hot Delta tables on NVMe SSD local worker storage.
    - Preventing out-of-memory errors caused by data skew in large joins or aggregations.

Architecture:
    Spark Catalyst Optimizer (Logical & Physical Plan)
                         |
           Adaptive Query Execution (AQE)
            - Dynamic Join Conversion (SortMerge -> Broadcast)
            - Dynamic Partition Coalescing
            - Dynamic Skew Join Handling
                         |
           Photon Execution Engine (C++ Vectorized Native Code)
                         |
           Disk Cache (Local NVMe SSDs on Cloud Workers)

Performance Notes:
    - Photon is optimized for SQL, DataFrames, and Delta Lake reads/writes (does not support Python UDFs directly).
    - Disk Caching accelerates repeated reads without consuming PySpark JVM heap memory.
    - Set `spark.sql.adaptive.skewJoin.enabled = true` to handle data skew automatically during runtime.

Common Mistakes:
    - Using custom Python UDFs inside Photon workloads (forces fallback to PySpark JVM, losing Photon acceleration).
    - Hardcoding `spark.sql.shuffle.partitions` to fixed numbers (e.g., 200) when AQE auto-coalescing is enabled.
    - Conflating Spark `CACHE TABLE` (in JVM RAM) with Databricks Disk Cache (on worker SSDs).

Interview Questions:
    Q: What is Photon and how does it differ from the standard Spark JVM engine?
    A: Photon is a vectorized query engine rewritten in C++ by Databricks. It directly processes columnar data
       in CPU cache/registers, bypassing Java bytecode generation and JVM GC overhead, delivering up to 5x query speedups.

    Q: How does Adaptive Query Execution (AQE) handle data skew during runtime?
    A: When AQE detects that a shuffle partition is significantly larger than others (skewed), it automatically splits
       that partition into smaller sub-partitions and duplicates matching rows from the other side of the join.
"""

import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabricksPerformanceOptimizer:
    """
    Production configuration manager and optimization tool for Databricks Photon,
    AQE, Disk Caching, and Delta table performance tuning.
    """

    def __init__(self, spark_session: Optional[Any] = None):
        self.spark = spark_session

    def get_optimized_spark_configs(
        self,
        enable_photon: bool = True,
        enable_disk_cache: bool = True,
        enable_aqe: bool = True,
        target_post_shuffle_input_size: int = 67108864,  # 64 MB
    ) -> Dict[str, str]:
        """
        Returns complete set of enterprise Spark performance configuration properties.
        """
        configs = {}

        # 1. Adaptive Query Execution (AQE)
        if enable_aqe:
            configs.update({
                "spark.sql.adaptive.enabled": "true",
                "spark.sql.adaptive.coalescePartitions.enabled": "true",
                "spark.sql.adaptive.coalescePartitions.targetPostShuffleInputSize": str(target_post_shuffle_input_size),
                "spark.sql.adaptive.skewJoin.enabled": "true",
                "spark.sql.adaptive.skewJoin.skewedPartitionFactor": "5",
                "spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes": "268435456",  # 256 MB
                "spark.sql.adaptive.localShuffleReader.enabled": "true",
            })

        # 2. Databricks Disk Cache (Delta Cache)
        if enable_disk_cache:
            configs.update({
                "spark.databricks.io.cache.enabled": "true",
                "spark.databricks.io.cache.maxDiskUsage": "80g",
                "spark.databricks.io.cache.compression.enabled": "true",
            })

        # 3. Photon Engine Configs
        if enable_photon:
            configs.update({
                "spark.databricks.photon.enabled": "true",
            })

        # 4. Delta Lake Auto-Optimize & Compact
        configs.update({
            "spark.databricks.delta.optimizeWrite.enabled": "true",
            "spark.databricks.delta.autoCompact.enabled": "true",
            "spark.sql.execution.arrow.pyspark.enabled": "true",  # Fast Pandas conversion
        })

        logger.info(f"Generated {len(configs)} performance configuration parameters.")
        return configs

    def apply_configs_to_session(self, configs: Optional[Dict[str, str]] = None) -> bool:
        """
        Applies configuration settings to live Spark Session if available.
        """
        target_configs = configs or self.get_optimized_spark_configs()
        if self.spark:
            for k, v in target_configs.items():
                self.spark.conf.set(k, v)
            logger.info("Successfully applied performance configs to active Spark session.")
            return True
        else:
            logger.info("Spark Session not active. Prepared configs for submission.")
            return False

    def generate_cache_table_sql(self, table_name: str) -> str:
        """
        Generates SQL command to explicitly load a Delta table into Databricks Disk Cache.
        """
        return f"CACHE SELECT * FROM {table_name};"

    def generate_zorder_optimize_sql(self, table_name: str, zorder_cols: list) -> str:
        """
        Generates Databricks Delta OPTIMIZE Z-ORDER BY statement for multi-dimensional clustering.
        """
        cols_str = ", ".join(zorder_cols)
        return f"OPTIMIZE {table_name} ZORDER BY ({cols_str});"


if __name__ == "__main__":
    optimizer = DatabricksPerformanceOptimizer()

    configs = optimizer.get_optimized_spark_configs(enable_photon=True, enable_aqe=True)
    print("=== Databricks Production Performance Configurations ===")
    for k, v in configs.items():
        print(f"  {k} = {v}")

    print("\n=== Databricks SQL Optimization Statements ===")
    print(optimizer.generate_cache_table_sql("prod_gold.fact_sales"))
    print(optimizer.generate_zorder_optimize_sql("prod_gold.fact_sales", ["customer_id", "transaction_date"]))
