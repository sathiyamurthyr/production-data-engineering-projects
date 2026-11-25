"""
Module 08: Structured Streaming on Databricks — State, Watermarking, and Sinks
=============================================================================

Explanation:
    Structured Streaming is a scalable stream processing engine built on Spark SQL.
    It handles stream computations as incremental queries on unbounded tables.
    Databricks enhances Structured Streaming with RocksDB state store management,
    optimized Delta Lake sinks, and Trigger.AvailableNow batch execution support.

Business Use Case:
    - Real-time IoT sensor telemetry aggregation with tumbling and sliding time windows.
    - Low-latency fraud detection scoring pipelines processing streaming financial events.
    - Asynchronous event-driven sync from Apache Kafka streams to Delta Lake data lakes.
    - CDC micro-batch streaming using `foreachBatch` to perform UPSERT (MERGE) into Delta Lake.

Architecture:
    Stream Source (Kafka / Event Hubs / Delta Stream)
                           |
            .withWatermark("event_time", "10 minutes")
                           |
             GroupBy Window (Tumbling / Sliding)
                           |
            State Store (RocksDB on Local SSD / DBFS)
                           |
            .writeStream.outputMode("append" / "complete" / "update")
                           |
                 Delta Lake Target Sink

Performance Notes:
    - Set `spark.sql.streaming.stateStore.providerClass` to RocksDB for high-cardinality state stores.
    - Use `Trigger.AvailableNow` (or `once=True` in legacy Spark) to process all available data incrementally in batch jobs, minimizing cluster uptime.
    - Ensure watermark duration balances late-data tolerance with memory reclamation speed.

Common Mistakes:
    - Using `outputMode("append")` on aggregation queries without specifying a watermark.
    - Changing query schema or transformation logic without clearing/versioning the `checkpointLocation`.
    - Excessive partitioning in streaming sinks leading to the small-file problem (mitigated by Delta Auto Compact).

Interview Questions:
    Q: What is the difference between Tumbling and Sliding Windows in Structured Streaming?
    A: Tumbling windows are fixed-size, non-overlapping time intervals (e.g. 5-minute windows: 12:00-12:05, 12:05-12:10).
       Sliding windows overlap based on a slide duration (e.g. 5-minute window every 1 minute: 12:00-12:05, 12:01-12:06).

    Q: How does `foreachBatch` work and when should you use it?
    A: `foreachBatch` exposes the underlying DataFrame for each micro-batch. You use it when standard stream sinks
       do not support your operation, such as performing a Delta `MERGE INTO` statement, writing to multiple sinks, or executing third-party APIs.
"""

import logging
from typing import Dict, Any, Optional, Callable

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class StructuredStreamingPipeline:
    """
    Production Structured Streaming helper for configuring windowing, watermarks,
    RocksDB state storage, micro-batch merges, and checkpoint management.
    """

    def __init__(self, app_name: str, checkpoint_base_dir: str = "/tmp/checkpoints"):
        self.app_name = app_name
        self.checkpoint_base_dir = checkpoint_base_dir

    def get_spark_streaming_configs(self, enable_rocksdb: bool = True) -> Dict[str, str]:
        """
        Returns optimized Spark session configurations for high-performance streaming.
        """
        configs = {
            "spark.sql.shuffle.partitions": "16",  # Optimized for smaller micro-batches
            "spark.sql.streaming.checkpointLocation": f"{self.checkpoint_base_dir}/{self.app_name}",
        }
        if enable_rocksdb:
            configs["spark.sql.streaming.stateStore.providerClass"] = (
                "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider"
            )
            configs["spark.sql.streaming.stateStore.rocksdb.compactOnCommit"] = "true"

        logger.info(f"Generated Spark Streaming configs for RocksDB={enable_rocksdb}")
        return configs

    def build_watermark_window_query_code(
        self,
        time_column: str,
        watermark_delay: str = "10 minutes",
        window_duration: str = "5 minutes",
        slide_duration: Optional[str] = None,
        group_by_cols: Optional[list] = None,
    ) -> str:
        """
        Generates PySpark transformation code for windowed aggregation with watermarking.
        """
        group_cols = group_by_cols or []
        slide_arg = f', "{slide_duration}"' if slide_duration else ""

        code = f"""
# Watermarked Windowed Aggregation Pattern
stream_df = (raw_stream_df
    .withWatermark("{time_column}", "{watermark_delay}")
    .groupBy(
        window("{time_column}", "{window_duration}"{slide_arg}),
        {", ".join([f'"{c}"' for c in group_cols])}
    )
    .agg(
        count("*").alias("event_count"),
        sum("amount").alias("total_amount")
    )
)
"""
        return code.strip()

    def generate_foreach_batch_merge_code(self, target_table: str, merge_keys: list) -> str:
        """
        Generates Python code for Delta MERGE inside `foreachBatch`.
        """
        key_conditions = " AND ".join([f"target.{k} = microBatchDF.{k}" for k in merge_keys])

        code = f"""
def upsert_to_delta(microBatchDF, batchId):
    # Perform Delta MERGE for each micro-batch
    from delta.tables import DeltaTable

    delta_table = DeltaTable.forName(spark, "{target_table}")

    (delta_table.alias("target")
        .merge(
            microBatchDF.alias("microBatchDF"),
            "{key_conditions}"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )

query = (streaming_df.writeStream
    .format("delta")
    .foreachBatch(upsert_to_delta)
    .outputMode("update")
    .option("checkpointLocation", "{self.checkpoint_base_dir}/{self.app_name}_merge")
    .start()
)
"""
        return code.strip()


if __name__ == "__main__":
    ssp = StructuredStreamingPipeline(app_name="iot_telemetry_agg", checkpoint_base_dir="/mnt/telemetry/_checkpoints")

    configs = ssp.get_spark_streaming_configs(enable_rocksdb=True)
    print("=== Streaming Spark Configs ===")
    for k, v in configs.items():
        print(f"  {k}: {v}")

    window_code = ssp.build_watermark_window_query_code(
        time_column="event_timestamp",
        watermark_delay="15 minutes",
        window_duration="1 hour",
        slide_duration="15 minutes",
        group_by_cols=["device_id", "region"],
    )
    print("\n=== PySpark Windowing Code ===")
    print(window_code)

    merge_code = ssp.generate_foreach_batch_merge_code(
        target_table="gold.device_status_dim",
        merge_keys=["device_id"],
    )
    print("\n=== PySpark ForeachBatch MERGE Code ===")
    print(merge_code)
