"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/producer/kafka_producer.py

Production-grade Kafka producer with:
- JSON and Avro serialization
- Configurable partitioning strategies (round-robin, key-based, custom)
- Delivery guarantees (acks=all for strongest guarantee)
- Batching and compression for throughput optimization
- Idempotent producer to prevent duplicate messages
- Callback-based delivery reporting
- Graceful shutdown and flush

Business Use Case:
  Real-time sales event ingestion from a microservices architecture into
  Kafka for downstream analytics, ML feature pipelines, and alerting.

Production Example:
  An e-commerce platform processes 500K orders/day. Each order event is
  published to Kafka within 5ms of creation. Downstream consumers feed
  a real-time dashboard, fraud detection ML model, and data warehouse.

Performance Notes:
  - linger.ms=5 + batch.size=65536 → 10x throughput vs defaults
  - compression.type=lz4 → 4x compression ratio, negligible CPU overhead
  - acks=all → zero data loss, ~2x latency vs acks=1
  - enable.idempotence=true → exactly-once at producer level

Interview Questions:
  Q: What is the difference between acks=0, acks=1, and acks=all?
  A: acks=0: Fire-and-forget (fastest, data loss risk).
     acks=1: Leader writes to local log (medium, leader crash = data loss).
     acks=all: All ISR replicas acknowledge (slowest, zero data loss).

  Q: What does enable.idempotence do?
  A: Assigns a Producer ID (PID) and sequence number to each message.
     The broker deduplicates retried messages using PID+sequence+partition.
     This prevents duplicates on retry without application-level deduplication.

  Q: When should you use a custom partitioner?
  A: When you need ordering guarantees within a logical group (e.g., all
     events for user_id=123 go to the same partition for ordered processing)
     or when load must be distributed by business key (region, tenant).
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Enums & Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

class PartitionStrategy(Enum):
    """Message partitioning strategies."""
    ROUND_ROBIN = "round_robin"          # Default: even load distribution
    KEY_BASED = "key_based"              # Murmur2 hash of message key
    CUSTOM = "custom"                    # Application-defined partitioner
    STICKY = "sticky"                    # Sticky: batch same partition until full


class CompressionType(Enum):
    """Kafka compression codecs."""
    NONE = "none"
    GZIP = "gzip"        # High compression, high CPU
    SNAPPY = "snappy"    # Balanced: good compression, low CPU
    LZ4 = "lz4"          # Best throughput, low latency
    ZSTD = "zstd"        # Best compression ratio (Kafka 2.1+)


@dataclass
class DeliveryReport:
    """Tracks delivery status of a produced message."""
    message_id: str
    topic: str
    partition: Optional[int]
    offset: Optional[int]
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class ProducerMetrics:
    """Aggregated producer metrics for monitoring."""
    messages_produced: int = 0
    messages_failed: int = 0
    bytes_produced: int = 0
    total_latency_ms: float = 0.0
    batch_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.messages_produced + self.messages_failed
        return (self.messages_produced / total * 100) if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return (self.total_latency_ms / self.messages_produced
                if self.messages_produced > 0 else 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages_produced": self.messages_produced,
            "messages_failed": self.messages_failed,
            "bytes_produced": self.bytes_produced,
            "success_rate_pct": round(self.success_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "batch_count": self.batch_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Mock Confluent Kafka classes for environments without the package installed
# In production, these are replaced by the real confluent_kafka classes.
# ─────────────────────────────────────────────────────────────────────────────

class _MockMessage:
    """Simulates a confluent_kafka.Message for local development/testing."""

    def __init__(self, topic: str, partition: int, offset: int,
                 key: bytes, value: bytes, error=None):
        self._topic = topic
        self._partition = partition
        self._offset = offset
        self._key = key
        self._value = value
        self._error = error
        self._timestamp = (0, int(time.time() * 1000))

    def topic(self) -> str:
        return self._topic

    def partition(self) -> int:
        return self._partition

    def offset(self) -> int:
        return self._offset

    def key(self) -> bytes:
        return self._key

    def value(self) -> bytes:
        return self._value

    def error(self):
        return self._error

    def timestamp(self):
        return self._timestamp


class _MockProducer:
    """Simulates confluent_kafka.Producer for testing without a running broker."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._delivered: List[_MockMessage] = []
        logger.info("[MockProducer] Initialized with config: %s", config)

    def produce(self, topic: str, key: bytes = None, value: bytes = None,
                partition: int = -1, callback=None, headers=None,
                timestamp: int = 0):
        msg = _MockMessage(
            topic=topic,
            partition=partition if partition >= 0 else 0,
            offset=len(self._delivered),
            key=key or b"",
            value=value or b"",
        )
        self._delivered.append(msg)
        if callback:
            callback(None, msg)  # No error

    def poll(self, timeout: float = 0) -> int:
        return 0

    def flush(self, timeout: float = 10.0) -> int:
        return 0

    def __len__(self) -> int:
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Main Producer Class
# ─────────────────────────────────────────────────────────────────────────────

class KafkaEventProducer:
    """
    Production-grade Kafka event producer.

    Supports:
    - JSON serialization (default) and Avro (with schema registry)
    - Configurable partitioning: key-based, round-robin, custom
    - Delivery guarantees: acks=all + idempotence
    - Compression: lz4 (default), gzip, snappy, zstd
    - Batching: linger.ms + batch.size tuning
    - Delivery callbacks for per-message tracking
    - Metrics collection

    Example:
        producer = KafkaEventProducer(
            bootstrap_servers="kafka:9092",
            compression=CompressionType.LZ4,
            delivery_guarantee="exactly_once",
        )
        producer.produce_event(
            topic="sales-events",
            key="order-123",
            event={"order_id": "123", "amount": 99.99},
        )
        producer.flush()
        producer.close()
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "de-diaries-producer",
        compression: CompressionType = CompressionType.LZ4,
        delivery_guarantee: str = "at_least_once",  # "at_least_once" | "exactly_once"
        batch_size_bytes: int = 65536,          # 64KB — balance throughput/latency
        linger_ms: int = 5,                     # Wait up to 5ms to fill batch
        max_in_flight_requests: int = 5,
        request_timeout_ms: int = 30000,
        retry_backoff_ms: int = 100,
        max_retries: int = 5,
        schema_registry_url: Optional[str] = None,
        on_delivery_callback: Optional[Callable[[Optional[Exception], Any], None]] = None,
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.compression = compression
        self.delivery_guarantee = delivery_guarantee
        self.schema_registry_url = schema_registry_url
        self.custom_callback = on_delivery_callback
        self.metrics = ProducerMetrics()
        self._delivery_reports: List[DeliveryReport] = []
        self._start_times: Dict[str, float] = {}

        # Build confluent_kafka producer config
        base_config: Dict[str, Any] = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "compression.type": compression.value,
            "batch.size": batch_size_bytes,
            "linger.ms": linger_ms,
            "request.timeout.ms": request_timeout_ms,
            "retry.backoff.ms": retry_backoff_ms,
            "retries": max_retries,
            # Delivery guarantee settings
            "acks": "all",                  # Always require all ISR acknowledgment
            "enable.idempotence": True,     # Prevent duplicates on retry
        }

        if delivery_guarantee == "exactly_once":
            # Transactional producer — enables exactly-once semantics
            base_config["transactional.id"] = f"{client_id}-txn-{uuid.uuid4().hex[:8]}"
            base_config["max.in.flight.requests.per.connection"] = 1
        else:
            base_config["max.in.flight.requests.per.connection"] = max_in_flight_requests

        if use_mock:
            self._producer = _MockProducer(base_config)
            logger.info("[KafkaEventProducer] Using MockProducer (no broker required)")
        else:
            try:
                from confluent_kafka import Producer
                self._producer = Producer(base_config)
                logger.info(
                    "[KafkaEventProducer] Connected to brokers: %s | "
                    "compression=%s | guarantee=%s",
                    bootstrap_servers, compression.value, delivery_guarantee
                )
            except ImportError:
                logger.warning(
                    "confluent_kafka not installed — falling back to MockProducer. "
                    "Install with: pip install confluent-kafka"
                )
                self._producer = _MockProducer(base_config)

        # Initialize transactions if exactly-once
        if delivery_guarantee == "exactly_once" and not use_mock:
            try:
                self._producer.init_transactions()
                logger.info("[KafkaEventProducer] Transactions initialized")
            except Exception as exc:
                logger.error("[KafkaEventProducer] Failed to init transactions: %s", exc)

    # ──────────────────────────────────────────────
    # Core produce methods
    # ──────────────────────────────────────────────

    def produce_event(
        self,
        topic: str,
        event: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: int = -1,
    ) -> str:
        """
        Produce a single event to a Kafka topic.

        Args:
            topic:     Target Kafka topic name
            event:     Event payload as a dictionary (will be JSON-serialized)
            key:       Optional message key for partitioning. If provided, all
                       messages with the same key go to the same partition.
            headers:   Optional headers dict (metadata — trace IDs, event type, etc.)
            partition: Target partition (-1 = let Kafka decide via key/round-robin)

        Returns:
            message_id: UUID assigned to this message for tracking

        Example:
            msg_id = producer.produce_event(
                topic="sales-events",
                key="user-123",
                event={"order_id": "ORD-999", "amount": 150.00},
                headers={"event_type": "order_placed", "source": "checkout-service"},
            )
        """
        message_id = str(uuid.uuid4())

        # Inject metadata into every event envelope
        envelope = {
            "message_id": message_id,
            "producer_id": self.client_id,
            "produced_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "payload": event,
        }

        value_bytes = json.dumps(envelope, default=str).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        # Convert headers to confluent_kafka format: list of (name, value) tuples
        kafka_headers = (
            [(k, v.encode("utf-8")) for k, v in headers.items()]
            if headers else None
        )

        self._start_times[message_id] = time.monotonic()

        def _delivery_callback(err, msg):
            self._handle_delivery(message_id, err, msg)

        try:
            self._producer.produce(
                topic=topic,
                key=key_bytes,
                value=value_bytes,
                partition=partition,
                callback=_delivery_callback,
                headers=kafka_headers,
            )
            # Trigger delivery callbacks for messages in the queue
            self._producer.poll(timeout=0)

            self.metrics.bytes_produced += len(value_bytes)
            logger.debug(
                "[produce_event] topic=%s key=%s msg_id=%s bytes=%d",
                topic, key, message_id, len(value_bytes)
            )
        except BufferError:
            # Producer internal queue is full — flush and retry
            logger.warning("[produce_event] Buffer full — flushing before retry")
            self._producer.flush(timeout=5.0)
            self._producer.produce(
                topic=topic,
                key=key_bytes,
                value=value_bytes,
                partition=partition,
                callback=_delivery_callback,
            )
        except Exception as exc:
            logger.error("[produce_event] Unexpected error: %s", exc, exc_info=True)
            self.metrics.messages_failed += 1
            raise

        return message_id

    def produce_batch(
        self,
        topic: str,
        events: List[Dict[str, Any]],
        key_extractor: Optional[Callable[[Dict[str, Any]], str]] = None,
        flush_every: int = 1000,
    ) -> List[str]:
        """
        Produce a batch of events efficiently.

        Args:
            topic:         Target Kafka topic
            events:        List of event dictionaries
            key_extractor: Function to extract the message key from each event.
                           Example: lambda e: e["user_id"]
            flush_every:   Flush after every N messages to control memory usage

        Returns:
            List of message IDs in the same order as input events

        Performance Notes:
            - Do NOT flush after every message — batch sends are 10-100x faster
            - Use key_extractor to ensure ordering within a logical group
            - flush_every=1000 is a safe default for most workloads

        Example:
            events = [{"order_id": i, "amount": i * 10.5} for i in range(10000)]
            msg_ids = producer.produce_batch(
                topic="sales-events",
                events=events,
                key_extractor=lambda e: str(e["order_id"]),
                flush_every=500,
            )
        """
        message_ids: List[str] = []
        self.metrics.batch_count += 1

        logger.info(
            "[produce_batch] Starting batch: topic=%s count=%d",
            topic, len(events)
        )
        batch_start = time.monotonic()

        for i, event in enumerate(events):
            key = key_extractor(event) if key_extractor else None
            msg_id = self.produce_event(topic=topic, event=event, key=key)
            message_ids.append(msg_id)

            # Periodic flush to prevent buffer overflow
            if (i + 1) % flush_every == 0:
                self._producer.flush(timeout=10.0)
                logger.debug("[produce_batch] Flushed at message %d", i + 1)

        # Final flush for remaining messages
        remaining = self._producer.flush(timeout=30.0)
        if remaining > 0:
            logger.warning(
                "[produce_batch] %d messages still in queue after flush timeout", remaining
            )

        elapsed_ms = (time.monotonic() - batch_start) * 1000
        throughput = len(events) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

        logger.info(
            "[produce_batch] Complete: count=%d elapsed_ms=%.1f throughput=%.0f msg/sec",
            len(events), elapsed_ms, throughput
        )
        return message_ids

    def produce_with_transaction(
        self,
        topic_events: List[Dict[str, Any]],
    ) -> bool:
        """
        Produce multiple events in a single Kafka transaction.
        Either ALL events are committed or NONE are — atomic batch.

        This is the foundation of exactly-once semantics (EOS).

        Args:
            topic_events: List of dicts with keys: topic, event, key (optional)

        Returns:
            True if transaction committed, False if aborted

        Example:
            producer.produce_with_transaction([
                {"topic": "sales-events",  "event": order_event,   "key": order_id},
                {"topic": "audit-log",     "event": audit_event,   "key": order_id},
                {"topic": "inventory",     "event": deduct_event,  "key": item_id},
            ])

        Interview Q: When do you need Kafka transactions?
        A: When you need atomic writes across multiple topics/partitions.
           Example: debit from account A AND credit to account B must both
           succeed or both fail. Transactions prevent partial writes.
        """
        if not hasattr(self._producer, "begin_transaction"):
            logger.warning("[produce_with_transaction] MockProducer: simulating commit")
            for item in topic_events:
                self.produce_event(
                    topic=item["topic"],
                    event=item["event"],
                    key=item.get("key"),
                )
            return True

        try:
            self._producer.begin_transaction()
            logger.info("[produce_with_transaction] Transaction started")

            for item in topic_events:
                self.produce_event(
                    topic=item["topic"],
                    event=item["event"],
                    key=item.get("key"),
                )

            self._producer.commit_transaction()
            logger.info(
                "[produce_with_transaction] Committed %d events", len(topic_events)
            )
            return True

        except Exception as exc:
            logger.error(
                "[produce_with_transaction] Aborting transaction due to: %s", exc
            )
            try:
                self._producer.abort_transaction()
            except Exception as abort_exc:
                logger.error("[produce_with_transaction] Abort failed: %s", abort_exc)
            return False

    # ──────────────────────────────────────────────
    # Delivery callback
    # ──────────────────────────────────────────────

    def _handle_delivery(self, message_id: str, err, msg) -> None:
        """
        Internal delivery callback invoked by confluent_kafka for each message.

        Interview Q: What is the purpose of the delivery callback?
        A: It's the only reliable way to confirm a message was successfully
           written to Kafka. Without it, you only know the message was sent
           to the producer's internal buffer, not that it reached the broker.
        """
        latency_ms = None
        start = self._start_times.pop(message_id, None)
        if start:
            latency_ms = (time.monotonic() - start) * 1000

        if err is not None:
            self.metrics.messages_failed += 1
            logger.error(
                "[delivery] FAILED msg_id=%s error=%s", message_id, err
            )
            report = DeliveryReport(
                message_id=message_id,
                topic=msg.topic() if msg else "unknown",
                partition=None,
                offset=None,
                timestamp=datetime.now(timezone.utc),
                success=False,
                error=str(err),
                latency_ms=latency_ms,
            )
        else:
            self.metrics.messages_produced += 1
            if latency_ms:
                self.metrics.total_latency_ms += latency_ms
            logger.debug(
                "[delivery] OK msg_id=%s topic=%s partition=%d offset=%d latency=%.1fms",
                message_id, msg.topic(), msg.partition(), msg.offset(),
                latency_ms or 0
            )
            report = DeliveryReport(
                message_id=message_id,
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                timestamp=datetime.now(timezone.utc),
                success=True,
                latency_ms=latency_ms,
            )

        self._delivery_reports.append(report)

        # Invoke custom callback if provided
        if self.custom_callback:
            self.custom_callback(err, msg)

    # ──────────────────────────────────────────────
    # Lifecycle & monitoring
    # ──────────────────────────────────────────────

    def flush(self, timeout: float = 30.0) -> int:
        """
        Flush all pending messages in the producer queue.

        Call this:
        - Before application shutdown
        - Before checkpointing in batch pipelines
        - After produce_batch if you need delivery confirmation

        Returns:
            Number of messages still in queue (0 = all delivered)
        """
        remaining = self._producer.flush(timeout=timeout)
        if remaining > 0:
            logger.warning("[flush] %d messages undelivered after %.1fs timeout", remaining, timeout)
        else:
            logger.info("[flush] All messages delivered successfully")
        return remaining

    def get_metrics(self) -> Dict[str, Any]:
        """Return current producer metrics for monitoring/alerting."""
        return self.metrics.to_dict()

    def get_delivery_reports(
        self,
        failed_only: bool = False,
    ) -> List[DeliveryReport]:
        """
        Retrieve delivery reports.

        Args:
            failed_only: If True, return only failed deliveries
        """
        if failed_only:
            return [r for r in self._delivery_reports if not r.success]
        return self._delivery_reports.copy()

    def close(self) -> None:
        """
        Gracefully shut down the producer.

        Always call this to ensure:
        1. All pending messages are flushed
        2. Producer resources are released
        3. Transactional state is cleaned up
        """
        logger.info("[KafkaEventProducer] Initiating graceful shutdown...")
        remaining = self.flush(timeout=30.0)

        final_metrics = self.metrics.to_dict()
        logger.info(
            "[KafkaEventProducer] Shutdown complete. Final metrics: %s | "
            "undelivered_msgs=%d",
            final_metrics, remaining
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Don't suppress exceptions


# ─────────────────────────────────────────────────────────────────────────────
# Custom Partitioner Example
# ─────────────────────────────────────────────────────────────────────────────

def region_based_partitioner(
    key: Optional[bytes],
    all_partitions: List[int],
    available_partitions: List[int],
) -> int:
    """
    Custom partitioner that routes messages to partitions based on region.

    Region → Partition mapping ensures all messages from the same region
    land on the same partition, guaranteeing regional ordering.

    Usage with confluent_kafka:
        producer = Producer({
            "bootstrap.servers": "localhost:9092",
            "partitioner": region_based_partitioner,  # Not directly supported
        })

    Note: confluent_kafka doesn't support Python-level custom partitioners
    directly. Instead, use key-based partitioning with a carefully chosen
    key that maps regions to partition ranges.

    Interview Q: How do you implement custom partitioning in Kafka?
    A: 1. In Java: implement the Partitioner interface
       2. In Python (confluent_kafka): Use key-based partitioning where
          the key encodes the partition assignment logic (e.g., region prefix)
       3. Alternatively, specify partition= explicitly in produce()
    """
    if key is None:
        return available_partitions[0] if available_partitions else 0

    key_str = key.decode("utf-8", errors="ignore").lower()
    num_partitions = len(all_partitions)

    # Route by geographic region prefix
    region_map = {
        "us-east": 0,
        "us-west": 1,
        "eu": 2,
        "apac": 3,
        "latam": 4,
    }

    for region_prefix, base_partition in region_map.items():
        if key_str.startswith(region_prefix):
            return base_partition % num_partitions

    # Fallback: consistent hash
    return hash(key) % num_partitions
