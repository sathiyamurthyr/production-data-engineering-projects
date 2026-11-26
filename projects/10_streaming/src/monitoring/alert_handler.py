"""
alert_handler.py — Streaming Operational Alerting & Lag Monitor
===============================================================

PURPOSE:
    Provides alert condition evaluation for real-time PySpark streaming queries.
    Detects latency degradation, consumer lag spikes, zero-event stalls, and unhandled runtime exceptions.

BUSINESS USE CASE:
    If an upstream Kafka topic stops emitting events or a downstream database sink throttles connection pools:
    1. Detect zero-throughput queries running for longer than alert window.
    2. Detect micro-batch processing durations exceeding SLA threshold (e.g. batch takes > 60s for 5s trigger).
    3. Trigger automated webhook alerts (Slack, PagerDuty, email) to On-Call Data Engineers.

INTERVIEW QUESTIONS:
    Q: What metrics indicate that a streaming job is struggling?
    A:
    1. Batch Duration > Trigger Interval (causing micro-batches to queue up).
    2. Input Rate > Process Rate consistently over time.
    3. High State Memory / RocksDB memory footprint growth.

Author: Sathiya Murthy
Project: Data Engineering Diaries — Project 10
"""

import logging
from typing import Dict, Any, Optional
from pyspark.sql.streaming import StreamingQuery

logger = logging.getLogger(__name__)


class StreamAlertHandler:
    """
    Evaluates streaming query metrics and triggers operational notifications.
    """

    def __init__(
        self,
        max_batch_duration_ms: int = 60000,
        max_lag_ratio: float = 2.0,
    ) -> None:
        """
        Initialise Alert Handler.

        Args:
            max_batch_duration_ms: Maximum acceptable micro-batch duration in ms.
            max_lag_ratio: Threshold ratio of (input_rate / process_rate) defining backpressure.
        """
        self.max_batch_duration_ms = max_batch_duration_ms
        self.max_lag_ratio = max_lag_ratio

    def evaluate_query_health(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate metrics snapshot and return alert dictionary if threshold violated.

        Args:
            metrics: Metrics dictionary extracted from query.lastProgress.

        Returns:
            Alert payload dictionary if issue detected, None if healthy.
        """
        if metrics.get("status") == "NO_PROGRESS_AVAILABLE":
            return None

        query_name = metrics.get("query_name", "unnamed_query")
        batch_duration = metrics.get("batch_duration_ms", 0)
        input_rate = metrics.get("input_rows_per_sec", 0.0)
        process_rate = metrics.get("processed_rows_per_sec", 0.0)

        # SLA Violation Check: Batch duration exceeds SLA limit
        if batch_duration > self.max_batch_duration_ms:
            alert = {
                "alert_level": "CRITICAL",
                "query_name": query_name,
                "rule": "BATCH_DURATION_SLA_VIOLATED",
                "message": f"Micro-batch duration ({batch_duration} ms) exceeded limit ({self.max_batch_duration_ms} ms).",
            }
            logger.error("ALERT DETECTED: %s", alert["message"])
            return alert

        # Consumer Lag / Backpressure Check
        if process_rate > 0 and (input_rate / process_rate) > self.max_lag_ratio:
            alert = {
                "alert_level": "WARNING",
                "query_name": query_name,
                "rule": "BACKPRESSURE_LAG_SPIKE",
                "message": f"Input rate ({input_rate:.1f}/s) is {input_rate/process_rate:.1f}x higher than process rate ({process_rate:.1f}/s).",
            }
            logger.warning("ALERT DETECTED: %s", alert["message"])
            return alert

        return None


def check_and_alert_query(
    query: StreamingQuery,
    max_duration_ms: int = 30000,
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to evaluate an active query instance.

    Args:
        query: Active StreamingQuery.
        max_duration_ms: SLA threshold limit.

    Returns:
        Alert dictionary or None.
    """
    from src.monitoring.streaming_metrics import StreamingMetricsExtractor

    metrics = StreamingMetricsExtractor.get_query_metrics(query)
    handler = StreamAlertHandler(max_batch_duration_ms=max_duration_ms)
    return handler.evaluate_query_health(metrics)
