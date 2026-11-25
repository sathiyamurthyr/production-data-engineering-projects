"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/patterns/dead_letter_queue.py

Dead Letter Queue (DLQ) & Poison Message Pattern.

Implements production fault-tolerant message processing:
- Distinction between transient errors (network timeout, DB temporary lock) vs permanent errors (JSON syntax error, schema mismatch)
- Exponential backoff retry loop for transient errors
- Automatic routing of unrecoverable/poison messages to `.DLQ` topic
- Enrichment of DLQ record headers with error diagnostics (exception message, stacktrace, original topic, original partition, original offset, retry attempts)
- Replay utility to re-drive DLQ events back to primary stream after bug resolution

Business Use Case:
  Prevents pipeline blocking. In standard streaming, a single corrupted/poison record
  stops the consumer loop indefinitely (infinite crash loop). DLQ captures poison records
  and allows the consumer to keep processing valid stream records.

Production Example:
  An analytics pipeline consuming `sales-events` encounters an unparseable malformed record.
  Instead of crashing, the handler retries 3 times, then publishes the failed event to
  `sales-events.DLQ` with diagnostic headers, preserving pipeline SLA.

Interview Questions:
  Q: What is a poison message in Kafka?
  A: A record that continuously fails processing (e.g. malformed JSON, divide-by-zero, invalid schema).
     If unhandled, it causes endless retries and blocks consumer offset progression.

  Q: What diagnostic metadata should be attached to DLQ messages?
  A: 1. Exception class and error message
     2. Original topic, partition, and offset
     3. Timestamp of failure
     4. Number of retry attempts made
     5. Processing host/pod identifier
"""

import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.consumer.kafka_consumer import ProcessedMessage

logger = logging.getLogger(__name__)


class ProcessingException(Exception):
    """Base exception for stream processing errors."""
    pass


class NonRetryableException(ProcessingException):
    """Permanent error — route immediately to DLQ (e.g. Malformed JSON, Schema error)."""
    pass


class RetryableException(ProcessingException):
    """Transient error — candidate for exponential retry (e.g. Database connection timeout)."""
    pass


@dataclass
class DLQEnvelope:
    """Enriched payload written to Dead Letter Queue topic."""
    original_topic: str
    original_partition: int
    original_offset: int
    error_type: str
    error_message: str
    stacktrace: str
    failed_at: str
    retry_count: int
    original_payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_topic": self.original_topic,
            "original_partition": self.original_partition,
            "original_offset": self.original_offset,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stacktrace": self.stacktrace,
            "failed_at": self.failed_at,
            "retry_count": self.retry_count,
            "original_payload": self.original_payload,
        }


class DeadLetterQueueHandler:
    """
    DLQ Producer and Retry Manager.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        dlq_suffix: str = ".DLQ",
        max_retries: int = 3,
        initial_backoff_ms: int = 200,
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.dlq_suffix = dlq_suffix
        self.max_retries = max_retries
        self.initial_backoff_ms = initial_backoff_ms
        self.use_mock = use_mock
        self.dlq_records_sent: List[DLQEnvelope] = []

        logger.info(
            "[DeadLetterQueueHandler] Initialized dlq_suffix=%s max_retries=%d",
            dlq_suffix, max_retries
        )

    def process_with_dlq(
        self,
        msg: ProcessedMessage,
        processing_func: Callable[[ProcessedMessage], None],
    ) -> bool:
        """
        Execute processing_func with automatic retry and DLQ routing on failure.

        Returns:
            True if processed successfully or routed to DLQ; False on fatal infrastructure failure.
        """
        attempt = 0
        backoff_ms = self.initial_backoff_ms

        while attempt <= self.max_retries:
            try:
                attempt += 1
                processing_func(msg)
                logger.debug("[DLQHandler] Message processed on attempt %d", attempt)
                return True

            except NonRetryableException as nre:
                logger.error("[DLQHandler] Non-retryable error on msg offset=%d: %s", msg.offset, nre)
                self.send_to_dlq(msg, nre, attempt_count=attempt)
                return True

            except Exception as exc:
                if attempt > self.max_retries:
                    logger.error(
                        "[DLQHandler] Max retries (%d) exhausted for msg offset=%d. Routing to DLQ. Error: %s",
                        self.max_retries, msg.offset, exc
                    )
                    self.send_to_dlq(msg, exc, attempt_count=attempt)
                    return True

                logger.warning(
                    "[DLQHandler] Transient error attempt %d/%d for msg offset=%d. Backing off %d ms. Error: %s",
                    attempt, self.max_retries, msg.offset, backoff_ms, exc
                )
                time.sleep(backoff_ms / 1000.0)
                backoff_ms *= 2  # Exponential backoff

        return False

    def send_to_dlq(
        self,
        msg: ProcessedMessage,
        exception: Exception,
        attempt_count: int,
    ) -> None:
        """
        Package failed message and error metadata into DLQ envelope and publish to DLQ topic.
        """
        dlq_topic = f"{msg.topic}{self.dlq_suffix}"

        envelope = DLQEnvelope(
            original_topic=msg.topic,
            original_partition=msg.partition,
            original_offset=msg.offset,
            error_type=exception.__class__.__name__,
            error_message=str(exception),
            stacktrace=traceback.format_exc(),
            failed_at=datetime.now(timezone.utc).isoformat(),
            retry_count=attempt_count,
            original_payload=msg.value,
        )

        self.dlq_records_sent.append(envelope)

        logger.info(
            "[send_to_dlq] Written to DLQ topic=%s original_offset=%d err_type=%s",
            dlq_topic, msg.offset, envelope.error_type
        )

        if not self.use_mock:
            try:
                from confluent_kafka import Producer
                producer = Producer({"bootstrap.servers": self.bootstrap_servers})
                producer.produce(
                    topic=dlq_topic,
                    key=msg.key.encode("utf-8") if msg.key else None,
                    value=json.dumps(envelope.to_dict()).encode("utf-8"),
                )
                producer.flush(timeout=5.0)
            except Exception as exc:
                logger.error("[send_to_dlq] Failed to produce record to DLQ topic: %s", exc)

    def replay_dlq_messages(
        self,
        dlq_topic: str,
        target_topic: str,
        max_messages: int = 100,
    ) -> int:
        """
        Replay messages from Dead Letter Queue back to target production topic for reprocessing.
        """
        logger.info("[replay_dlq_messages] Replaying from %s -> %s...", dlq_topic, target_topic)
        replayed_count = 0

        if self.use_mock:
            replayed_count = len(self.dlq_records_sent)
            logger.info("[DLQ-Mock-Replay] Replayed %d messages", replayed_count)
            return replayed_count

        try:
            from confluent_kafka import Consumer, Producer
            consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": f"dlq-replay-{int(time.time())}",
                "auto.offset.reset": "earliest",
            })
            producer = Producer({"bootstrap.servers": self.bootstrap_servers})

            consumer.subscribe([dlq_topic])

            for _ in range(max_messages):
                raw = consumer.poll(timeout=1.0)
                if raw is None or raw.error():
                    break

                val_dict = json.loads(raw.value().decode("utf-8"))
                original_payload = val_dict.get("original_payload", val_dict)

                producer.produce(
                    topic=target_topic,
                    value=json.dumps(original_payload).encode("utf-8"),
                )
                replayed_count += 1

            producer.flush(timeout=10.0)
            consumer.close()

            logger.info("[replay_dlq_messages] Replay complete. %d messages re-driven.", replayed_count)
            return replayed_count

        except Exception as exc:
            logger.error("[replay_dlq_messages] Replay error: %s", exc)
            return replayed_count
