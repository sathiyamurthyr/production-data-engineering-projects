"""
file_source.py — File-Based Streaming Sources for Structured Streaming
=======================================================================

PURPOSE:
    Implements streaming reads from file-based sources: cloud object stores
    (S3, ADLS, GCS), local directories, and Databricks Auto Loader (cloudFiles).
    File streaming is an essential pattern when Kafka is not available or when
    data arrives as batch files dropped into cloud storage by upstream systems.

BUSINESS USE CASE:
    A retail chain's point-of-sale systems upload transaction CSV files to S3
    every minute. Instead of a nightly batch job, this module processes each
    file the moment it lands — enabling near-real-time inventory and sales reporting.

    Another use case: Partner data integrations where external partners drop JSON
    files into an SFTP/S3 bucket. Auto Loader detects new files immediately and
    streams them into the Delta Lake pipeline.

HOW FILE STREAMING WORKS:
    1. Spark monitors a directory for new files
    2. When new files appear, they are read in the next micro-batch
    3. The checkpoint stores which files have been processed (prevents reprocessing)
    4. Files are processed in file-modification-time order (approximately)

DATABRICKS AUTO LOADER (cloudFiles):
    Auto Loader is Databricks' enhanced file streaming source that:
    - Uses cloud-native file notification services (S3 EventBridge, Azure Event Grid)
      instead of listing the directory on every trigger (massive cost/latency savings)
    - Handles schema inference and schema evolution automatically
    - Supports billions of files without performance degradation
    - Provides exactly-once guarantees per file

    vs. Standard file streaming:
    - Standard: Lists entire directory every trigger → slow at scale, misses files in race conditions
    - Auto Loader: Event-driven → detects files instantly, scales to millions of files per hour

SUPPORTED FORMATS:
    - CSV  : Structured tabular data from ETL exports, POS systems
    - JSON : Semi-structured data from APIs, application events
    - Parquet: Columnar data from batch processes upstream
    - Avro : Schema-evolving events from Confluent/Kafka batch dumps

INTERVIEW QUESTIONS:
    Q: How does Spark track which files have already been processed in file streaming?
    A: Spark uses a checkpoint directory that stores a log of all processed files.
       On restart, it reads this log and only processes files not in the log.
       This ensures exactly-once processing (each file processed once and only once).

    Q: What is the difference between cloudFiles and the standard file source?
    A: Standard file source lists the directory on every trigger (expensive at scale).
       cloudFiles uses cloud notification APIs to detect new files event-driven —
       no directory listing needed. It's 10-100x more efficient for high-volume file arrivals
       and can handle millions of files without performance issues.

    Q: What happens if a file is modified after it's been processed?
    A: Spark tracks files by name + modification time. A modified file would appear
       as a new entry. However, in practice, immutable file naming (e.g., UUID prefixes)
       prevents this issue. Never modify files after they land in a streaming directory.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
import os
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-defined schemas for common file formats
# ---------------------------------------------------------------------------

# Schema for CSV transaction files from POS systems
TRANSACTION_CSV_SCHEMA = StructType([
    StructField("transaction_id", StringType(), nullable=False),
    StructField("store_id", StringType(), nullable=False),
    StructField("terminal_id", StringType(), nullable=True),
    StructField("customer_id", StringType(), nullable=True),
    StructField("product_id", StringType(), nullable=False),
    StructField("product_name", StringType(), nullable=True),
    StructField("category", StringType(), nullable=True),
    StructField("quantity", IntegerType(), nullable=False),
    StructField("unit_price", DoubleType(), nullable=False),
    StructField("total_amount", DoubleType(), nullable=False),
    StructField("payment_method", StringType(), nullable=True),
    StructField("transaction_timestamp", StringType(), nullable=False),
])

# Schema for JSON event files from application logs
APP_EVENT_JSON_SCHEMA = StructType([
    StructField("event_id", StringType(), nullable=False),
    StructField("app_name", StringType(), nullable=False),
    StructField("version", StringType(), nullable=True),
    StructField("environment", StringType(), nullable=True),   # "prod", "staging"
    StructField("user_id", StringType(), nullable=True),
    StructField("event_type", StringType(), nullable=False),
    StructField("payload", StringType(), nullable=True),       # nested JSON as string
    StructField("latency_ms", IntegerType(), nullable=True),
    StructField("error_code", StringType(), nullable=True),
    StructField("event_timestamp", StringType(), nullable=False),
])


class FileSourceReader:
    """
    Production file streaming source reader for Structured Streaming.

    Supports standard file streaming and Databricks Auto Loader (cloudFiles).

    Usage (standard):
        reader = FileSourceReader(spark)
        df = (
            reader
            .from_csv_directory(
                path="s3://my-bucket/transactions/",
                schema=TRANSACTION_CSV_SCHEMA,
            )
            .with_watermark("30 minutes")
            .build()
        )

    Usage (Auto Loader):
        df = (
            reader
            .from_auto_loader(
                path="s3://my-bucket/events/",
                format="json",
                schema=APP_EVENT_JSON_SCHEMA,
            )
            .with_watermark("10 minutes")
            .build()
        )
    """

    def __init__(self, spark: SparkSession) -> None:
        """
        Initialise file source reader.

        Args:
            spark: Active SparkSession.
        """
        self.spark = spark
        self._path: Optional[str] = None
        self._format: Optional[str] = None
        self._schema: Optional[StructType] = None
        self._options: dict[str, str] = {}
        self._watermark_delay: Optional[str] = None
        self._timestamp_col: str = "event_timestamp"
        self._use_auto_loader: bool = False
        self._max_files_per_trigger: Optional[int] = None
        self._latest_first: bool = False

    def from_csv_directory(
        self,
        path: str,
        schema: Optional[StructType] = None,
        header: bool = True,
        delimiter: str = ",",
        date_format: str = "yyyy-MM-dd'T'HH:mm:ss",
        infer_schema: bool = False,
    ) -> "FileSourceReader":
        """
        Stream CSV files from a directory.

        Files must follow a consistent schema. New files added to the directory
        are processed in subsequent micro-batches.

        Args:
            path:        Directory path (local, HDFS, S3, ADLS, GCS).
            schema:      Explicit StructType. Always provide this in production —
                         schema inference reads sample files on each restart (slow
                         and error-prone when file formats change).
            header:      True if CSV files have a header row.
            delimiter:   Column separator character. Default comma.
            date_format: Format string for parsing date/timestamp strings.
            infer_schema: If True, Spark infers schema from data (slow, avoid in prod).

        Returns:
            Self for chaining.

        Production tip:
            Always use explicit schema in production. Schema inference requires
            reading a sample of each file, which adds latency and can fail if
            the sample file has missing data or inconsistent types.
        """
        self._path = path
        self._format = "csv"
        self._schema = schema
        self._options.update({
            "header": str(header).lower(),
            "sep": delimiter,
            "dateFormat": date_format,
            "inferSchema": str(infer_schema).lower(),
            # Corrupted rows go to _corrupt_record column instead of failing the batch
            "mode": "PERMISSIVE",
            "columnNameOfCorruptRecord": "_corrupt_record",
        })
        logger.debug("CSV directory source configured: %s", path)
        return self

    def from_json_directory(
        self,
        path: str,
        schema: Optional[StructType] = None,
        multiline: bool = False,
    ) -> "FileSourceReader":
        """
        Stream JSON files from a directory.

        By default, Spark expects one JSON object per line (JSON Lines / NDJSON format).
        Set multiline=True for pretty-printed JSON files where one JSON object spans
        multiple lines (but this disables parallelism within a file).

        Args:
            path:       Directory path.
            schema:     Expected JSON schema. Strongly recommended for production.
            multiline:  True if each file contains a single pretty-printed JSON object.
                        False (default) for JSON Lines format (one JSON per line).

        Returns:
            Self for chaining.
        """
        self._path = path
        self._format = "json"
        self._schema = schema
        self._options.update({
            "multiline": str(multiline).lower(),
            # Timestamp format for automatic cast of timestamp strings
            "timestampFormat": "yyyy-MM-dd'T'HH:mm:ss",
            "mode": "PERMISSIVE",
            "columnNameOfCorruptRecord": "_corrupt_record",
        })
        logger.debug("JSON directory source configured: %s", path)
        return self

    def from_parquet_directory(self, path: str) -> "FileSourceReader":
        """
        Stream Parquet files from a directory.

        Parquet includes schema in its file footer, so no explicit schema is needed.
        However, all Parquet files in the directory must have compatible schemas.

        Schema evolution (adding nullable columns) is supported by Spark's Parquet
        reader, but column renames or type changes require a new checkpoint and
        directory.

        Args:
            path: Directory path containing Parquet files.

        Returns:
            Self for chaining.
        """
        self._path = path
        self._format = "parquet"
        # Parquet is self-describing — no schema options needed
        logger.debug("Parquet directory source configured: %s", path)
        return self

    def from_auto_loader(
        self,
        path: str,
        file_format: str = "json",
        schema: Optional[StructType] = None,
        schema_location: Optional[str] = None,
        infer_column_types: bool = True,
    ) -> "FileSourceReader":
        """
        Stream files using Databricks Auto Loader (cloudFiles format).

        Auto Loader is the recommended approach for streaming from cloud storage
        in Databricks environments. It uses cloud notification services instead
        of directory listing, making it dramatically faster and cheaper at scale.

        Auto Loader features:
        - Schema inference: Automatically infers schema from initial files
        - Schema evolution: Detects new columns and handles type changes gracefully
        - Exactly-once: Tracks file processing in checkpoint; no duplicates
        - File notification: S3 EventBridge / Azure Event Grid for instant detection

        Args:
            path:               Cloud storage path (s3://, abfss://, gs://).
            file_format:        Format of input files: "json", "csv", "parquet", "avro".
            schema:             Explicit schema. If None, Auto Loader infers schema.
            schema_location:    Path where Auto Loader stores its inferred schema.
                                Required when using schema inference (schema_hints not provided).
                                Allows schema evolution tracking across restarts.
            infer_column_types: If True, Auto Loader infers column types during inference.
                                If False, all columns are treated as StringType initially.

        Returns:
            Self for chaining.

        Note:
            cloudFiles format requires Databricks Runtime 7.0+. It is NOT available
            in open-source PySpark. For non-Databricks environments, use the standard
            directory streaming methods above.
        """
        self._use_auto_loader = True
        self._path = path
        self._format = file_format
        self._schema = schema
        self._options.update({
            "cloudFiles.format": file_format,
            "cloudFiles.inferColumnTypes": str(infer_column_types).lower(),
        })
        if schema_location:
            self._options["cloudFiles.schemaLocation"] = schema_location
        logger.debug("Auto Loader source configured: path=%s, format=%s", path, file_format)
        return self

    def with_max_files_per_trigger(self, n: int) -> "FileSourceReader":
        """
        Limit the number of files processed per micro-batch.

        Provides backpressure for file streaming — prevents a large backlog of
        files from creating an enormous first batch that overwhelms downstream sinks.

        Args:
            n: Maximum number of files to process per trigger.

        Returns:
            Self for chaining.
        """
        self._max_files_per_trigger = n
        return self

    def process_latest_first(self, enabled: bool = True) -> "FileSourceReader":
        """
        Process newest files first when there is a backlog.

        Default (False): Process files in FIFO order (oldest first).
        This option (True): Process newest files first — useful when you care
        about recent data more than historical catch-up.

        Args:
            enabled: True to process newest files first.

        Returns:
            Self for chaining.
        """
        self._latest_first = enabled
        return self

    def with_watermark(
        self,
        delay: str,
        timestamp_col: str = "event_timestamp",
    ) -> "FileSourceReader":
        """
        Apply watermark for late-data tolerance and state management.

        Args:
            delay:         Duration string: "10 minutes", "1 hour", etc.
            timestamp_col: Event timestamp column name. Must be TimestampType.

        Returns:
            Self for chaining.
        """
        self._watermark_delay = delay
        self._timestamp_col = timestamp_col
        return self

    def build(self) -> DataFrame:
        """
        Build and return the streaming DataFrame.

        Returns:
            Streaming DataFrame with file data. Includes `_corrupt_record` column
            for CSV/JSON to capture malformed rows.

        Raises:
            ValueError: If no source path has been configured.
        """
        if not self._path:
            raise ValueError(
                "Must call from_csv_directory(), from_json_directory(), "
                "from_parquet_directory(), or from_auto_loader() before build()"
            )

        # Choose source format
        source_format = "cloudFiles" if self._use_auto_loader else self._format

        # Build reader
        reader = self.spark.readStream.format(source_format)

        # Apply schema if provided
        if self._schema is not None:
            reader = reader.schema(self._schema)

        # Apply all options
        for key, value in self._options.items():
            reader = reader.option(key, value)

        # Backpressure: limit files per trigger
        if self._max_files_per_trigger:
            reader = reader.option("maxFilesPerTrigger", self._max_files_per_trigger)

        # Process newest files first in backlog scenario
        if self._latest_first:
            reader = reader.option("latestFirst", "true")

        # Load the streaming DataFrame
        df = reader.load(self._path)

        # Add source file path for lineage tracking (which file produced each row)
        df = df.withColumn("_source_file", F.input_file_name())

        logger.info(
            "File readStream created: path=%s, format=%s, autoloader=%s",
            self._path,
            self._format,
            self._use_auto_loader,
        )

        # Cast timestamp string column if present and not already TimestampType
        if self._schema and "event_timestamp" in [f.name for f in self._schema.fields]:
            event_ts_field = next(
                f for f in self._schema.fields if f.name == "event_timestamp"
            )
            if event_ts_field.dataType == StringType():
                df = df.withColumn(
                    "event_timestamp",
                    F.to_timestamp(F.col("event_timestamp"), "yyyy-MM-dd'T'HH:mm:ss"),
                )

        # Apply watermark
        if self._watermark_delay:
            df = df.withWatermark(self._timestamp_col, self._watermark_delay)
            logger.info(
                "Watermark applied: col=%s, delay=%s",
                self._timestamp_col,
                self._watermark_delay,
            )

        return df


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def stream_csv_files(
    spark: SparkSession,
    path: str,
    schema: StructType,
    watermark_delay: Optional[str] = None,
    max_files_per_trigger: int = 10,
) -> DataFrame:
    """
    Quick helper to stream CSV files from a directory with sensible defaults.

    Args:
        spark:                   SparkSession.
        path:                    Directory path containing CSV files.
        schema:                  Expected CSV schema.
        watermark_delay:         Optional late data tolerance.
        max_files_per_trigger:   Files per micro-batch (default 10 for backpressure).

    Returns:
        Streaming DataFrame.
    """
    reader = (
        FileSourceReader(spark)
        .from_csv_directory(path, schema=schema)
        .with_max_files_per_trigger(max_files_per_trigger)
    )
    if watermark_delay:
        reader = reader.with_watermark(watermark_delay)
    return reader.build()


def stream_json_files(
    spark: SparkSession,
    path: str,
    schema: StructType,
    watermark_delay: Optional[str] = None,
    max_files_per_trigger: int = 10,
) -> DataFrame:
    """
    Quick helper to stream JSON (NDJSON) files from a directory.

    Args:
        spark:                   SparkSession.
        path:                    Directory path containing JSON files.
        schema:                  Expected JSON schema.
        watermark_delay:         Optional late data tolerance.
        max_files_per_trigger:   Files per micro-batch.

    Returns:
        Streaming DataFrame.
    """
    reader = (
        FileSourceReader(spark)
        .from_json_directory(path, schema=schema)
        .with_max_files_per_trigger(max_files_per_trigger)
    )
    if watermark_delay:
        reader = reader.with_watermark(watermark_delay)
    return reader.build()


# ---------------------------------------------------------------------------
# Entry point demonstration
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.streaming_session import create_test_session

    spark = create_test_session("file-source-demo")

    print("=== File Source Reader Demo ===")
    print("Available schemas:")
    print(f"  TRANSACTION_CSV_SCHEMA: {[f.name for f in TRANSACTION_CSV_SCHEMA.fields]}")
    print(f"  APP_EVENT_JSON_SCHEMA : {[f.name for f in APP_EVENT_JSON_SCHEMA.fields]}")

    print("\nExample usage:")
    print("  reader = FileSourceReader(spark)")
    print("  df = reader.from_csv_directory('/data/transactions/', TRANSACTION_CSV_SCHEMA)")
    print("              .with_watermark('30 minutes')")
    print("              .with_max_files_per_trigger(5)")
    print("              .build()")

    spark.stop()
