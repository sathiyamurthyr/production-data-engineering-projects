"""
kafka_sink.py — Streaming Kafka Output Sink
=============================================

PURPOSE:
    Provides production-grade functionality for publishing PySpark Structured Streaming
    results back to Apache Kafka topics.
    In event-driven architectures, transformed micro-batches or alerts are published
    back to Kafka downstream topics for push notifications, downstream consumer microservices,
    or cross-region stream replication.

KAFKA SINK REQUIREMENTS:
    Kafka writeStream expects a DataFrame with the following structure:
    ┌──────────┬──────────────────────────────────────────────┐
    │ Column   │ Type / Description                           │
    ├──────────┼──────────────────────────────────────────────┤
    │ topic    │ string (optional if set in option)           │
    │ key      │ string or binary (optional partition key)    │
    │ value    │ string or binary (REQUIRED message payload)   │
    └──────────┴──────────────────────────────────────────────┘

BUSINESS USE CASE:
    - Fraud Alerting: High-risk events flagged by streaming stateful rules are formatted as JSON strings and written to `fraud-alerts-topic`.
    - Event Bus Enrichment: Raw clickstream events are enriched with user demographics and published back to `enriched-clicks-topic`.

INTERVIEW QUESTIONS:
    Q: What columns must a streaming DataFrame contain when writing to Kafka without a fixed topic option?
    A: It must contain at least a `value` column (string or binary). If the `topic` option is not hardcoded, a `topic` column specifying the destination topic per row must also exist.

    Q: Does writing to Kafka guarantee exactly-once processing?
    A: Spark Structured Streaming guarantees at-least-once writes to Kafka sinks. To achieve end-to-end exactly-once, downstream Kafka consumers must perform idempotent reads or deduplicate based on unique event IDs.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class KafkaStreamSink:
    """
    Production streaming sink for writing DataFrames to Apache Kafka.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        """
        Initialise Kafka stream sink.

        Args:
            bootstrap_servers: Comma-separated list of Kafka broker endpoints.
        """
        self.bootstrap_servers = bootstrap_servers

    def write_to_kafka(
        self,
        df: DataFrame,
        topic: str,
        query_name: str,
        key_col: Optional[str] = None,
        checkpoint_path: str = "/tmp/kafka_sink_checkpoints",
        output_mode: str = "append",
        trigger_interval: str = "10 seconds",
    ) -> StreamingQuery:
        """
        Serialize DataFrame payload to JSON and write to specified Kafka topic.

        Args:
            df: Streaming DataFrame containing target payload attributes.
            topic: Target Kafka topic name.
            query_name: Unique streaming query name.
            key_col: Column to map to Kafka message key (for partitioning).
            checkpoint_path: Storage path for streaming query checkpoints.
            output_mode: Streaming output mode ("append", "update").
            trigger_interval: Trigger timing interval.

        Returns:
            Active StreamingQuery object.
        """
        logger.info("Preparing streaming DataFrame write to Kafka topic '%s'", topic)

        # Build payload JSON string from all columns (excluding key column if specified)
        payload_cols = [c for c in df.columns if c != key_col]
        kafka_df = df.select(
            F.col(key_col).cast("string").alias("key") if key_col else F.lit(None).cast("string").alias("key"),
            F.to_json(F.struct(*payload_cols)).alias("value"),
        )

        cp = f"{checkpoint_path}/{query_name}"

        writer = (
            kafka_df.writeStream
            .format("kafka")
            .outputMode(output_mode)
            .queryName(query_name)
            .option("kafka.bootstrap.servers", self.bootstrap_servers)
            .option("topic", topic)
            .option("checkpointLocation", cp)
        )

        if trigger_interval.lower() == "availablenow":
            writer = writer.trigger(availableNow=True)
        else:
            writer = writer.trigger(processingTime=trigger_interval)

        return writer.start()


def write_to_kafka_topic(
    df: DataFrame,
    topic: str,
    query_name: str,
    bootstrap_servers: str = "localhost:9092",
    key_col: Optional[str] = None,
    checkpoint_dir: str = "/tmp/checkpoints",
) -> StreamingQuery:
    """
    Convenience function for streaming to Kafka.

    Args:
        df: Streaming DataFrame.
        topic: Target topic.
        query_name: Query identifier.
        bootstrap_servers: Kafka broker addresses.
        key_col: Partitioning key column.
        checkpoint_dir: Base checkpoint location.

    Returns:
        Active StreamingQuery instance.
    """
    sink = KafkaStreamSink(bootstrap_servers=bootstrap_servers)
    return sink.write_to_kafka(
        df,
        topic=topic,
        query_name=query_name,
        key_col=key_col,
        checkpoint_path=checkpoint_dir,
    )
