"""
kafka_source.py — Production Kafka readStream Source for Structured Streaming
==============================================================================

PURPOSE:
    Encapsulates all patterns for reading from Apache Kafka using PySpark
    Structured Streaming's readStream API. Kafka is the most common source
    for real-time event pipelines at companies like Netflix, Uber, and LinkedIn.

BUSINESS USE CASE:
    An e-commerce platform publishes order events, click events, and inventory
    updates to Kafka topics. This module reads those topics and produces
    typed, schema-enforced DataFrames ready for downstream processing.

    Without schema enforcement: Kafka delivers raw bytes. You'd need manual
    parsing everywhere, with no type safety or null checks.
    
    With this module: Receive a clean StructType DataFrame with proper timestamps,
    watermarks, and nullable annotations — just like a batch DataFrame.

HOW KAFKA SOURCE WORKS IN STRUCTURED STREAMING:
    1. Spark assigns Kafka topic-partitions to tasks (one task per partition)
    2. Each micro-batch reads a range of offsets from each partition
    3. maxOffsetsPerTrigger controls how many records per batch (backpressure)
    4. Checkpointing stores the last committed offset per partition
    5. On restart, Spark reads offsets from checkpoint and continues from there

KAFKA MESSAGE STRUCTURE:
    Every row from Kafka readStream has these columns:
    ┌─────────────────┬──────────────────────────────────────────────┐
    │ Column          │ Type / Description                           │
    ├─────────────────┼──────────────────────────────────────────────┤
    │ key             │ binary — Kafka message key (often entity ID) │
    │ value           │ binary — Kafka message payload (JSON/Avro)   │
    │ topic           │ string — Kafka topic name                    │
    │ partition       │ int    — Kafka partition number              │
    │ offset          │ long   — Offset within partition             │
    │ timestamp       │ timestamp — Kafka broker timestamp           │
    │ timestampType   │ int    — 0=CreateTime, 1=LogAppendTime       │
    └─────────────────┴──────────────────────────────────────────────┘

PERFORMANCE NOTES:
    - Set maxOffsetsPerTrigger to limit batch size and control latency/throughput tradeoff
    - Use startingOffsets="latest" for production (don't reprocess history)
    - Use startingOffsets="earliest" for backfill or first-run scenarios
    - fetchOffset.numRetries and fetchOffset.retryIntervalMs handle transient broker issues
    - minPartitions forces repartition so small Kafka partition counts don't bottleneck parallelism

INTERVIEW QUESTIONS:
    Q: What happens if Spark is restarted and there are no checkpoints?
    A: Without checkpoints, startingOffsets config determines where reading begins.
       "latest" means messages during downtime are lost. "earliest" means full reprocessing.
       In production, always use checkpoints to resume exactly where processing stopped.

    Q: How does Spark handle Kafka partition rebalancing?
    A: Spark treats each partition as an independent stream. When new partitions are
       added to a Kafka topic, Spark automatically picks them up in the next micro-batch.
       Removed partitions are handled via failOnDataLoss option.

    Q: What is failOnDataLoss and when should you set it to false?
    A: failOnDataLoss=true (default) causes the query to fail if Kafka offsets
       are no longer available (e.g., data was deleted due to retention). Set to false
       when your Kafka retention is shorter than your streaming downtime window, accepting
       that some messages may be skipped rather than causing pipeline failure.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import json
import logging
import os
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-built schemas for common event types
# These should live in a schema registry in production (e.g., Confluent Schema Registry)
# ---------------------------------------------------------------------------

# Schema for e-commerce click/page-view events
CLICK_EVENT_SCHEMA = StructType([
    StructField("event_id", StringType(), nullable=False),
    StructField("user_id", StringType(), nullable=False),
    StructField("session_id", StringType(), nullable=True),
    StructField("event_type", StringType(), nullable=False),     # "click", "view", "purchase"
    StructField("page_url", StringType(), nullable=True),
    StructField("product_id", StringType(), nullable=True),
    StructField("category", StringType(), nullable=True),
    StructField("price", DoubleType(), nullable=True),
    StructField("quantity", IntegerType(), nullable=True),
    StructField("device_type", StringType(), nullable=True),     # "mobile", "desktop", "tablet"
    StructField("country_code", StringType(), nullable=True),
    StructField("event_timestamp", StringType(), nullable=False), # ISO string, cast to timestamp
    StructField("properties", StringType(), nullable=True),       # JSON blob for extra attributes
])

# Schema for IoT sensor readings
IOT_SENSOR_SCHEMA = StructType([
    StructField("sensor_id", StringType(), nullable=False),
    StructField("device_type", StringType(), nullable=False),     # "temperature", "pressure", "humidity"
    StructField("location_id", StringType(), nullable=False),
    StructField("latitude", DoubleType(), nullable=True),
    StructField("longitude", DoubleType(), nullable=True),
    StructField("reading_value", DoubleType(), nullable=False),
    StructField("unit", StringType(), nullable=False),            # "celsius", "bar", "percent"
    StructField("is_anomaly", BooleanType(), nullable=True),
    StructField("battery_level", DoubleType(), nullable=True),
    StructField("event_timestamp", StringType(), nullable=False),
])

# Schema for application log events (generic)
LOG_EVENT_SCHEMA = StructType([
    StructField("log_id", StringType(), nullable=False),
    StructField("service_name", StringType(), nullable=False),
    StructField("host", StringType(), nullable=True),
    StructField("level", StringType(), nullable=False),           # "INFO", "WARN", "ERROR"
    StructField("message", StringType(), nullable=False),
    StructField("trace_id", StringType(), nullable=True),
    StructField("span_id", StringType(), nullable=True),
    StructField("duration_ms", LongType(), nullable=True),
    StructField("status_code", IntegerType(), nullable=True),
    StructField("event_timestamp", StringType(), nullable=False),
])


class KafkaSourceReader:
    """
    Production-ready Kafka source for PySpark Structured Streaming.

    Handles:
    - Reading from single or multiple topics
    - JSON payload deserialization with schema enforcement
    - Watermark configuration for late-data handling
    - Offset management (earliest/latest/specific)
    - Connection resilience configuration

    Usage:
        spark = create_kafka_delta_session("my-app")
        reader = KafkaSourceReader(spark, bootstrap_servers="kafka:9092")

        # Read click events from Kafka
        click_df = (
            reader
            .from_topic("click-events", CLICK_EVENT_SCHEMA)
            .with_watermark("10 minutes")
            .build()
        )

        # click_df is a streaming DataFrame ready for transformations
    """

    def __init__(
        self,
        spark: SparkSession,
        bootstrap_servers: Optional[str] = None,
        starting_offsets: str = "latest",
        max_offsets_per_trigger: Optional[int] = None,
        fail_on_data_loss: bool = True,
        min_partitions: Optional[int] = None,
    ) -> None:
        """
        Initialise the Kafka source reader with connection and offset settings.

        Args:
            spark:                   Active SparkSession.
            bootstrap_servers:       Comma-separated Kafka broker list.
                                     Reads KAFKA_BOOTSTRAP_SERVERS env var if not provided.
            starting_offsets:        "latest" (production) or "earliest" (backfill/first-run).
                                     Can also be a JSON string specifying per-partition offsets:
                                     '{"topic":{"0":123,"1":456}}'
            max_offsets_per_trigger: Maximum Kafka messages per micro-batch.
                                     Provides backpressure. None = unlimited.
                                     Example: 10000 ensures each batch ≤ 10K messages.
            fail_on_data_loss:       True = fail if Kafka offsets are missing (safe default).
                                     False = skip missing offsets (use when Kafka retention < downtime).
            min_partitions:          Force Spark to create at least this many tasks per micro-batch.
                                     Useful when Kafka has few partitions but you want parallelism.
        """
        self.spark = spark
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.starting_offsets = starting_offsets
        self.max_offsets_per_trigger = max_offsets_per_trigger
        self.fail_on_data_loss = fail_on_data_loss
        self.min_partitions = min_partitions

        # State set by builder methods
        self._topic: Optional[str] = None
        self._topic_pattern: Optional[str] = None
        self._schema: Optional[StructType] = None
        self._watermark_delay: Optional[str] = None
        self._timestamp_col: str = "event_timestamp"
        self._kafka_options: dict[str, str] = {}

        logger.info(
            "KafkaSourceReader initialised: brokers=%s, starting=%s",
            self.bootstrap_servers,
            self.starting_offsets,
        )

    def from_topic(
        self,
        topic: str,
        schema: Optional[StructType] = None,
    ) -> "KafkaSourceReader":
        """
        Configure reader to consume from a single Kafka topic.

        Args:
            topic:  Kafka topic name.
            schema: StructType for JSON payload deserialization.
                    If None, the raw binary `value` column is returned.

        Returns:
            Self for method chaining.
        """
        self._topic = topic
        self._schema = schema
        logger.debug("Configured to read from topic: %s", topic)
        return self

    def from_topics(
        self,
        topics: list[str],
        schema: Optional[StructType] = None,
    ) -> "KafkaSourceReader":
        """
        Configure reader to consume from multiple Kafka topics.

        All topics must have the same JSON schema when schema is provided.
        The `topic` column in the resulting DataFrame identifies the source topic.

        Args:
            topics: List of Kafka topic names.
            schema: Shared StructType for all topics' JSON payload.

        Returns:
            Self for method chaining.
        """
        # Spark's subscribe option accepts comma-separated topic list
        self._topic = ",".join(topics)
        self._schema = schema
        logger.debug("Configured to read from topics: %s", self._topic)
        return self

    def from_topic_pattern(
        self,
        pattern: str,
        schema: Optional[StructType] = None,
    ) -> "KafkaSourceReader":
        """
        Configure reader to consume from all topics matching a regex pattern.

        Useful when new topics are created dynamically and you want to consume
        all of them without restarting the stream.

        Example:
            reader.from_topic_pattern("events-.*")
            # Reads from: events-clicks, events-orders, events-views, etc.

        Args:
            pattern: Java regex pattern for topic names.
            schema:  Shared StructType for payload deserialization.

        Returns:
            Self for method chaining.
        """
        self._topic_pattern = pattern
        self._schema = schema
        logger.debug("Configured to read from topic pattern: %s", pattern)
        return self

    def with_watermark(
        self,
        delay: str,
        timestamp_col: str = "event_timestamp",
    ) -> "KafkaSourceReader":
        """
        Configure watermark for late data handling.

        The watermark tells Spark: "events arriving more than `delay` after
        the maximum event time seen so far should be dropped." This is required
        for:
        - Output mode `append` with aggregations
        - Stream-to-stream joins
        - dropDuplicates with event time

        Args:
            delay:         Late data tolerance as duration string: "10 minutes", "1 hour", "30 seconds".
            timestamp_col: Column name containing the event timestamp.
                           Must be of TimestampType after deserialization.

        Returns:
            Self for method chaining.

        Interview note:
            Watermark = max(event_time_seen) - delay
            Events with timestamp < watermark are dropped from state.
            This allows Spark to clean up state memory for old windows.
        """
        self._watermark_delay = delay
        self._timestamp_col = timestamp_col
        return self

    def with_kafka_option(self, key: str, value: str) -> "KafkaSourceReader":
        """
        Add a custom Kafka consumer option.

        Common options:
            "kafka.security.protocol"          → "SASL_SSL" for secured clusters
            "kafka.sasl.mechanism"             → "PLAIN" or "GSSAPI"
            "kafka.sasl.jaas.config"           → JAAS credentials for SASL auth
            "kafka.group.id"                   → Consumer group ID
            "kafka.fetch.min.bytes"            → Min data before broker responds
            "kafka.fetch.max.wait.ms"          → Max wait time when insufficient data

        Args:
            key:   Option key (use "kafka." prefix for Kafka consumer properties).
            value: Option value.

        Returns:
            Self for method chaining.
        """
        self._kafka_options[key] = value
        return self

    def build(self) -> DataFrame:
        """
        Build and return the streaming DataFrame.

        Steps:
        1. Configure readStream with Kafka options
        2. Apply topic subscription (subscribe/subscribePattern)
        3. Deserialize JSON payload using schema if provided
        4. Cast timestamp string column to TimestampType
        5. Apply watermark if configured

        Returns:
            Streaming DataFrame. If schema provided: typed columns from JSON.
            If no schema: raw Kafka columns (key, value, topic, partition, offset, timestamp).

        Raises:
            ValueError: If neither topic nor topic_pattern is configured.
        """
        if not self._topic and not self._topic_pattern:
            raise ValueError(
                "Must call from_topic(), from_topics(), or from_topic_pattern() before build()"
            )

        # Step 1: Base read options
        reader = (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", self.bootstrap_servers)
            .option("startingOffsets", self.starting_offsets)
            .option("failOnDataLoss", str(self.fail_on_data_loss).lower())
        )

        # Step 2: Topic subscription
        if self._topic_pattern:
            reader = reader.option("subscribePattern", self._topic_pattern)
        else:
            reader = reader.option("subscribe", self._topic)

        # Step 3: Optional backpressure control
        if self.max_offsets_per_trigger:
            reader = reader.option("maxOffsetsPerTrigger", self.max_offsets_per_trigger)

        # Step 4: Optional minimum parallelism
        if self.min_partitions:
            reader = reader.option("minPartitions", self.min_partitions)

        # Step 5: Apply any custom Kafka options
        for key, value in self._kafka_options.items():
            reader = reader.option(key, value)

        # Step 6: Load raw Kafka DataFrame
        raw_df = reader.load()

        logger.info(
            "Kafka readStream created: topic=%s, pattern=%s",
            self._topic,
            self._topic_pattern,
        )

        # Step 7: Deserialize JSON if schema provided
        if self._schema is not None:
            df = self._deserialize_json(raw_df, self._schema)
        else:
            # Return raw Kafka DataFrame — caller handles deserialization
            df = raw_df
            logger.info("No schema provided — returning raw Kafka DataFrame")
            return df

        # Step 8: Apply watermark if configured
        if self._watermark_delay:
            df = df.withWatermark(self._timestamp_col, self._watermark_delay)
            logger.info(
                "Watermark applied: col=%s, delay=%s",
                self._timestamp_col,
                self._watermark_delay,
            )

        return df

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _deserialize_json(
        self,
        raw_df: DataFrame,
        schema: StructType,
    ) -> DataFrame:
        """
        Parse the binary `value` column as JSON and extract typed fields.

        The Kafka `value` column is binary (bytes). We cast it to string,
        then use from_json() to parse the JSON string into a struct column,
        then flatten the struct into top-level columns.

        We also keep Kafka metadata columns (topic, partition, offset, timestamp)
        for debugging and lineage tracking.

        Args:
            raw_df: Raw Kafka DataFrame with binary value column.
            schema: Expected JSON payload schema.

        Returns:
            DataFrame with typed columns from JSON + Kafka metadata columns.
        """
        parsed_df = (
            raw_df
            # Cast binary key and value to string
            .withColumn("key_str", F.col("key").cast(StringType()))
            .withColumn("value_str", F.col("value").cast(StringType()))
            # Parse JSON value using schema — malformed JSON becomes null struct
            .withColumn("payload", F.from_json(F.col("value_str"), schema))
            # Flatten struct fields to top-level columns using payload.*
            .select(
                "payload.*",
                # Keep Kafka metadata for debugging and lineage
                F.col("key_str").alias("kafka_key"),
                F.col("topic").alias("kafka_topic"),
                F.col("partition").alias("kafka_partition"),
                F.col("offset").alias("kafka_offset"),
                F.col("timestamp").alias("kafka_timestamp"),  # broker timestamp
            )
        )

        # Cast the event_timestamp string field to proper TimestampType
        # so window functions and watermarks work correctly
        if "event_timestamp" in [f.name for f in schema.fields]:
            parsed_df = parsed_df.withColumn(
                "event_timestamp",
                F.to_timestamp(F.col("event_timestamp"), "yyyy-MM-dd'T'HH:mm:ss"),
            )

        logger.debug(
            "JSON deserialized: %d schema fields -> %d DataFrame columns",
            len(schema.fields),
            len(parsed_df.columns),
        )
        return parsed_df


# ---------------------------------------------------------------------------
# Standalone utility functions for simpler use cases
# ---------------------------------------------------------------------------

def read_kafka_json(
    spark: SparkSession,
    topic: str,
    schema: StructType,
    bootstrap_servers: Optional[str] = None,
    watermark_delay: Optional[str] = None,
    starting_offsets: str = "latest",
    max_offsets_per_trigger: Optional[int] = None,
) -> DataFrame:
    """
    Convenience function for the most common pattern: read JSON events from Kafka.

    This is a thin wrapper around KafkaSourceReader for callers that don't need
    the full builder API.

    Args:
        spark:                   SparkSession instance.
        topic:                   Kafka topic name.
        schema:                  StructType for JSON payload.
        bootstrap_servers:       Kafka broker list (uses env var if None).
        watermark_delay:         Late data tolerance (e.g., "10 minutes"). Optional.
        starting_offsets:        "latest" or "earliest".
        max_offsets_per_trigger: Backpressure control. None = unlimited.

    Returns:
        Streaming DataFrame with typed columns.

    Example:
        df = read_kafka_json(
            spark,
            topic="click-events",
            schema=CLICK_EVENT_SCHEMA,
            watermark_delay="15 minutes",
            max_offsets_per_trigger=50000,
        )
    """
    reader = KafkaSourceReader(
        spark=spark,
        bootstrap_servers=bootstrap_servers,
        starting_offsets=starting_offsets,
        max_offsets_per_trigger=max_offsets_per_trigger,
    ).from_topic(topic, schema)

    if watermark_delay:
        reader = reader.with_watermark(watermark_delay)

    return reader.build()


def read_kafka_raw(
    spark: SparkSession,
    topic: str,
    bootstrap_servers: Optional[str] = None,
    starting_offsets: str = "latest",
) -> DataFrame:
    """
    Read raw bytes from Kafka without schema enforcement.

    Use this when the payload format is unknown, variable (Avro/Protobuf/JSON mix),
    or when you need to inspect the raw bytes for schema inference.

    Returns:
        Raw Kafka DataFrame with columns: key (binary), value (binary), topic, partition,
        offset, timestamp, timestampType.
    """
    return (
        KafkaSourceReader(spark=spark, bootstrap_servers=bootstrap_servers, starting_offsets=starting_offsets)
        .from_topic(topic, schema=None)
        .build()
    )


# ---------------------------------------------------------------------------
# Entry point for smoke testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.streaming_session import create_kafka_delta_session

    spark = create_kafka_delta_session("kafka-source-demo")

    # Demonstrate schema definition
    print("=== Available Schemas ===")
    print(f"CLICK_EVENT_SCHEMA fields: {[f.name for f in CLICK_EVENT_SCHEMA.fields]}")
    print(f"IOT_SENSOR_SCHEMA fields : {[f.name for f in IOT_SENSOR_SCHEMA.fields]}")
    print(f"LOG_EVENT_SCHEMA fields  : {[f.name for f in LOG_EVENT_SCHEMA.fields]}")

    print("\n=== KafkaSourceReader API ===")
    print("reader = KafkaSourceReader(spark, 'kafka:9092')")
    print("df     = reader.from_topic('click-events', CLICK_EVENT_SCHEMA)")
    print("             .with_watermark('10 minutes')")
    print("             .build()")
    print("\nNote: Actual readStream requires a running Kafka broker.")

    spark.stop()
