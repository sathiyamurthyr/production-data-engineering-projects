"""
streaming_metrics.py — Query Progress & Streaming Listener Metrics
====================================================================

PURPOSE:
    Provides production monitoring, metrics extraction, and StreamingQueryListener utilities
    for PySpark Structured Streaming jobs. Real-time streaming applications must continuously emit
    operational health metrics (throughput, latency, watermark lag, input rate vs processing rate)
    to observability platforms (Prometheus, Datadog, CloudWatch).

METRICS COVERED:
    - Input Rate: Number of events per second arriving from source (Kafka / Cloud Storage).
    - Processing Rate: Number of events per second processed by Spark workers.
    - Batch Duration: Total execution time (in milliseconds) per micro-batch.
    - Watermark Lag: Time difference between current real-time clock and current streaming watermark.
    - Backpressure Status: If Input Rate > Processing Rate consistently, consumer lag is building up.

PRODUCTION MONITORING PATTERNS:
    1. Polling Query Progress: Inspecting `query.lastProgress` programmatically on active queries.
    2. StreamingQueryListener: Event-driven listener attached to `spark.streams.addListener()`.

INTERVIEW QUESTIONS:
    Q: How do you detect if a streaming query is falling behind (consumer lag)?
    A: Compare `inputRowsPerSecond` and `processedRowsPerSecond` from `query.lastProgress`.
       If `inputRowsPerSecond > processedRowsPerSecond` over consecutive batches, the pipeline has consumer lag.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Dict, Any, Optional
from pyspark.sql import SparkSession
from pyspark.sql.streaming import StreamingQuery, StreamingQueryListener

logger = logging.getLogger(__name__)


class ProductionStreamingListener(StreamingQueryListener):
    """
    Event-driven listener logging metrics on query startup, progress, and termination.
    """

    def onQueryStarted(self, event: StreamingQueryListener.QueryStartedEvent) -> None:
        """Called when a streaming query is started."""
        logger.info(
            "STREAM STARTED — Query ID: %s, Name: %s, Run ID: %s",
            event.id,
            event.name,
            event.runId,
        )

    def onQueryProgress(self, event: StreamingQueryListener.QueryProgressEvent) -> None:
        """Called whenever a micro-batch completes and emits progress metrics."""
        progress = event.progress
        batch_id = progress.batchId
        num_input_rows = progress.numInputRows
        input_rate = progress.inputRowsPerSecond
        process_rate = progress.processedRowsPerSecond

        logger.info(
            "STREAM PROGRESS [%s | Batch %d] Input Rows: %d | Input Rate: %.2f rows/s | Process Rate: %.2f rows/s",
            progress.name or progress.id,
            batch_id,
            num_input_rows,
            input_rate,
            process_rate,
        )

        # Check for lag indicator
        if input_rate > process_rate and num_input_rows > 0:
            logger.warning(
                "BACKPRESSURE WARNING [%s]: Input rate (%.2f/s) > Process rate (%.2f/s)",
                progress.name,
                input_rate,
                process_rate,
            )

    def onQueryTerminated(self, event: StreamingQueryListener.QueryTerminatedEvent) -> None:
        """Called when a streaming query terminates due to error or stop command."""
        if event.exception:
            logger.error(
                "STREAM TERMINATED WITH ERROR — Query ID: %s, Exception: %s",
                event.id,
                event.exception,
            )
        else:
            logger.info("STREAM TERMINATED GRACEFULLY — Query ID: %s", event.id)


class StreamingMetricsExtractor:
    """
    Utility to extract snapshot metrics from an active StreamingQuery instance.
    """

    @staticmethod
    def get_query_metrics(query: StreamingQuery) -> Dict[str, Any]:
        """
        Extract clean dictionary of operational metrics from query.lastProgress.

        Args:
            query: Active StreamingQuery object.

        Returns:
            Dictionary containing input_rate, process_rate, batch_id, num_input_rows, etc.
        """
        progress = query.lastProgress
        if not progress:
            return {"status": "NO_PROGRESS_AVAILABLE", "is_active": query.isActive}

        return {
            "query_name": query.name,
            "query_id": str(query.id),
            "is_active": query.isActive,
            "batch_id": progress.get("batchId"),
            "num_input_rows": progress.get("numInputRows"),
            "input_rows_per_sec": round(progress.get("inputRowsPerSecond", 0.0), 2),
            "processed_rows_per_sec": round(progress.get("processedRowsPerSecond", 0.0), 2),
            "batch_duration_ms": progress.get("durationMs", {}).get("triggerExecution", 0),
            "watermark": progress.get("eventTime", {}).get("watermark"),
        }


def attach_metrics_listener(spark: SparkSession) -> ProductionStreamingListener:
    """
    Attach production streaming query listener to SparkSession.

    Args:
        spark: Active SparkSession.

    Returns:
        Instance of ProductionStreamingListener.
    """
    listener = ProductionStreamingListener()
    spark.streams.addListener(listener)
    logger.info("Attached ProductionStreamingListener to SparkSession streams manager")
    return listener
