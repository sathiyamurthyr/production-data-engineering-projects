"""
Module 07: Auto Loader (cloudFiles) — Scalable Incremental Cloud Storage Ingestion
=================================================================================

Explanation:
    Auto Loader efficiently processes new data files as they arrive in AWS S3, Azure ADLS Gen2,
    or Google Cloud Storage without needing expensive full directory list scans. It supports
    automatic schema inference, schema evolution handling, and rescued data tracking.

Business Use Case:
    - Incremental ingestion of streaming log files, JSON payloads, or CSV reports from cloud storage.
    - Robust handling of schema drift (new columns appended upstream) without breaking pipelines.
    - Zero-loss ingestion with malformed/unparseable data stored in `_rescued_data`.
    - Cost reduction for storage buckets containing millions of historical files.

Architecture:
    Cloud Storage (S3 / ADLS / GCS)
          |
    [SNS/SQS or Event Grid Notifications]  <-- Auto Loader File Notification Mode
          |
    Auto Loader Spark Streaming Engine (`spark.readStream.format("cloudFiles")`)
          |
          +---> Checkpoint Directory (State / Offsets)
          +---> Schema RocksDB / Metastore (Schema Tracking)
          |
    Delta Lake Bronze Table (Append Mode)

Performance Notes:
    - Directory Listing mode works well up to ~1 million files.
    - File Notification mode (SNS/SQS on AWS, Event Grid on Azure) is required for > 1M files.
    - Set `cloudFiles.maxFilesPerTrigger` or `cloudFiles.maxBytesPerTrigger` to cap micro-batch size.

Common Mistakes:
    - Reusing the same `schemaLocation` path for different source directories (corrupts schema).
    - Omitting `checkpointLocation`, causing streaming queries to fail on cluster restart.
    - Forgetting cloud storage IAM permissions for auto-configuring cloud event notifications.

Interview Questions:
    Q: How does Auto Loader handle schema evolution when new fields arrive in JSON source files?
    A: Auto Loader supports `cloudFiles.schemaEvolutionMode` modes:
       - `addNewColumns` (default): automatically appends new columns to the Delta table schema.
       - `failOnNewFields`: throws an exception so developers can review the schema change.
       - `rescue`: leaves schema unchanged and captures new fields inside `_rescued_data`.
       - `none`: ignores new columns completely.

    Q: Why is Auto Loader preferred over standard `spark.readStream` for cloud storage?
    A: Standard file stream lists all files in the directory repeatedly, which degrades exponentially
       in speed and cost as file count grows. Auto Loader uses cloud notification queues or RocksDB listing caches.
"""

import logging
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AutoLoaderIngestion:
    """
    Production Auto Loader configuration builder and PySpark readStream wrapper.
    """

    def __init__(
        self,
        file_format: str = "json",
        schema_location: str = "/tmp/autoloader/schema",
        checkpoint_location: str = "/tmp/autoloader/checkpoint",
        rescued_data_column: str = "_rescued_data",
    ):
        self.file_format = file_format
        self.schema_location = schema_location
        self.checkpoint_location = checkpoint_location
        self.rescued_data_column = rescued_data_column

    def get_autoloader_options(
        self,
        schema_evolution_mode: str = "addNewColumns",
        use_notifications: bool = False,
        max_files_per_trigger: int = 1000,
        extra_options: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Builds standard Spark readStream cloudFiles configuration dictionary.
        """
        options = {
            "cloudFiles.format": self.file_format,
            "cloudFiles.schemaLocation": self.schema_location,
            "cloudFiles.schemaEvolutionMode": schema_evolution_mode,
            "cloudFiles.rescuedDataColumn": self.rescued_data_column,
            "cloudFiles.maxFilesPerTrigger": str(max_files_per_trigger),
            "cloudFiles.inferColumnTypes": "true",
        }

        if use_notifications:
            options["cloudFiles.useNotifications"] = "true"

        if extra_options:
            options.update(extra_options)

        logger.info(f"Generated Auto Loader options for format '{self.file_format}'")
        return options

    def build_pyspark_stream_code(
        self,
        source_path: str,
        target_delta_table: str,
        trigger_mode: str = "availableNow",
        partition_cols: Optional[list] = None,
    ) -> str:
        """
        Generates production-ready PySpark python code string for running Auto Loader stream.
        """
        opts = self.get_autoloader_options()
        opts_str = ",\n        ".join([f'"{k}": "{v}"' for k, v in opts.items()])

        partition_clause = f'.partitionBy({partition_cols})' if partition_cols else ""

        if trigger_mode == "availableNow":
            trigger_clause = ".trigger(availableNow=True)"
        elif trigger_mode.startswith("processingTime"):
            trigger_clause = f'.trigger(processingTime="{trigger_mode.split(":")[1]}")'
        else:
            trigger_clause = ""

        code = f"""
# Auto Loader Stream Ingestion Script
df = (spark.readStream
        .format("cloudFiles")
        .options(**{{
        {opts_str}
        }})
        .load("{source_path}")
     )

query = (df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", "{self.checkpoint_location}")
        {trigger_clause}
        {partition_clause}
        .toTable("{target_delta_table}")
     )

query.awaitTermination()
"""
        return code.strip()


if __name__ == "__main__":
    al = AutoLoaderIngestion(
        file_format="parquet",
        schema_location="s3://my-bucket/checkpoints/orders_schema",
        checkpoint_location="s3://my-bucket/checkpoints/orders_chk",
    )

    options = al.get_autoloader_options(schema_evolution_mode="addNewColumns", use_notifications=True)
    print("=== Auto Loader Options ===")
    for k, v in options.items():
        print(f"  {k}: {v}")

    pyspark_code = al.build_pyspark_stream_code(
        source_path="s3://my-bucket/landing/orders/",
        target_delta_table="prod_raw.bronze_orders",
        trigger_mode="availableNow",
        partition_cols=["order_date"],
    )

    print("\n=== PySpark Execution Code ===")
    print(pyspark_code)
