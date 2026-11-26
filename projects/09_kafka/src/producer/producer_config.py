"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/producer/producer_config.py

Producer Configuration Management Module.

Provides environment-aware, validated configuration objects for Kafka producers.
Includes preset configuration profiles:
- ZERO_DATA_LOSS: Strongest durability (acks=all, idempotence, 3+ replicas)
- HIGH_THROUGHPUT: Optimized for batching, compression, and high volume
- LOW_LATENCY: Optimized for minimal latency (linger.ms=0, no compression)

Business Use Case:
  Enterprise Kafka deployments require standardized configuration profiles across
  microservices to enforce consistency in security, retries, and performance guarantees.

Production Example:
  Financial transaction service uses ZERO_DATA_LOSS profile.
  Clickstream telemetry ingestor uses HIGH_THROUGHPUT profile.

Interview Questions:
  Q: How do you configure Kafka producer for zero data loss?
  A: 1. acks=all (all ISR replicas must acknowledge)
     2. enable.idempotence=true (prevents duplicates on retry)
     3. retries=sys.maxsize (retry until delivered)
     4. max.in.flight.requests.per.connection <= 5 (1 if ordering without idempotence)
     5. min.insync.replicas=2 on broker side

  Q: How do linger.ms and batch.size affect producer throughput and latency?
  A: batch.size sets maximum bytes sent per batch. linger.ms sets max delay before sending batch.
     Higher linger.ms (e.g. 10-50ms) allows larger batches to accumulate, increasing throughput
     and compression ratio at the cost of slight latency increase.
"""

import os
import logging
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SecurityProtocol(str, Enum):
    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class SaslMechanism(str, Enum):
    PLAIN = "PLAIN"
    SCRAM_SHA_256 = "SCRAM-SHA-256"
    SCRAM_SHA_512 = "SCRAM-SHA-512"
    GSSAPI = "GSSAPI"


class ProducerConfigProfile(str, Enum):
    ZERO_DATA_LOSS = "zero_data_loss"
    HIGH_THROUGHPUT = "high_throughput"
    LOW_LATENCY = "low_latency"
    BALANCED = "balanced"


class KafkaProducerConfig(BaseModel):
    """
    Validated Kafka Producer Configuration model.
    Supports environment variable overrides and profile generation.
    """
    bootstrap_servers: str = Field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        description="Comma-separated list of broker host:port addresses"
    )
    client_id: str = Field(
        default_factory=lambda: os.getenv("KAFKA_CLIENT_ID", "de-diaries-producer"),
        description="Client identification string passed to brokers"
    )
    acks: str = Field(
        default="all",
        description="Acknowledgment level: 0, 1, or all (-1)"
    )
    enable_idempotence: bool = Field(
        default=True,
        description="Ensure exactly-once delivery at producer level"
    )
    retries: int = Field(
        default=2147483647,  # INT_MAX
        description="Number of retries on transient errors"
    )
    retry_backoff_ms: int = Field(
        default=100,
        description="Backoff time in ms before retrying failed request"
    )
    max_in_flight_requests_per_connection: int = Field(
        default=5,
        description="Max unacknowledged requests allowed on a single connection"
    )
    compression_type: str = Field(
        default="lz4",
        description="Compression codec: none, gzip, snappy, lz4, zstd"
    )
    batch_size: int = Field(
        default=65536,  # 64 KB
        description="Max bytes for batching messages per partition"
    )
    linger_ms: int = Field(
        default=10,
        description="Max time in ms to delay send for batch accumulation"
    )
    buffer_memory: int = Field(
        default=33554432,  # 32 MB
        description="Total memory size for producer buffering un-sent messages"
    )
    max_block_ms: int = Field(
        default=60000,
        description="Max time send() or partitionsFor() will block"
    )
    request_timeout_ms: int = Field(
        default=30000,
        description="Max time client waits for request response"
    )
    security_protocol: SecurityProtocol = Field(
        default=SecurityProtocol.PLAINTEXT,
        description="Security protocol used to communicate with brokers"
    )
    sasl_mechanism: Optional[SaslMechanism] = Field(
        default=None,
        description="SASL mechanism for authentication"
    )
    sasl_username: Optional[str] = Field(
        default_factory=lambda: os.getenv("KAFKA_SASL_USERNAME"),
        description="SASL authentication username"
    )
    sasl_password: Optional[str] = Field(
        default_factory=lambda: os.getenv("KAFKA_SASL_PASSWORD"),
        description="SASL authentication password"
    )
    ssl_ca_location: Optional[str] = Field(
        default_factory=lambda: os.getenv("KAFKA_SSL_CA_LOCATION"),
        description="Path to CA certificate file"
    )

    def to_confluent_kafka_dict(self) -> Dict[str, Any]:
        """Convert pydantic settings to librdkafka / confluent-kafka dictionary format."""
        cfg: Dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": self.client_id,
            "acks": self.acks,
            "enable.idempotence": self.enable_idempotence,
            "retries": self.retries,
            "retry.backoff.ms": self.retry_backoff_ms,
            "max.in.flight.requests.per.connection": self.max_in_flight_requests_per_connection,
            "compression.type": self.compression_type,
            "batch.size": self.batch_size,
            "linger.ms": self.linger_ms,
            "buffer.memory": self.buffer_memory,
            "max.block.ms": self.max_block_ms,
            "request.timeout.ms": self.request_timeout_ms,
            "security.protocol": self.security_protocol.value.lower(),
        }

        if self.sasl_mechanism:
            cfg["sasl.mechanism"] = self.sasl_mechanism.value
            if self.sasl_username:
                cfg["sasl.username"] = self.sasl_username
            if self.sasl_password:
                cfg["sasl.password"] = self.sasl_password

        if self.ssl_ca_location:
            cfg["ssl.ca.location"] = self.ssl_ca_location

        return cfg


def get_producer_config_profile(profile: ProducerConfigProfile) -> KafkaProducerConfig:
    """
    Factory function to retrieve pre-configured Producer profiles.

    Profiles:
    - ZERO_DATA_LOSS: acks=all, idempotence=True, max_in_flight=5, retries=max
    - HIGH_THROUGHPUT: batch_size=128KB, linger_ms=20, compression=lz4
    - LOW_LATENCY: batch_size=16KB, linger_ms=0, compression=none
    - BALANCED: safe defaults balancing speed and safety
    """
    if profile == ProducerConfigProfile.ZERO_DATA_LOSS:
        return KafkaProducerConfig(
            acks="all",
            enable_idempotence=True,
            max_in_flight_requests_per_connection=5,
            retries=2147483647,
            compression_type="lz4",
            linger_ms=10,
            batch_size=65536,
        )
    elif profile == ProducerConfigProfile.HIGH_THROUGHPUT:
        return KafkaProducerConfig(
            acks="1",
            enable_idempotence=False,
            compression_type="lz4",
            linger_ms=20,
            batch_size=131072,  # 128KB
            buffer_memory=67108864,  # 64MB
        )
    elif profile == ProducerConfigProfile.LOW_LATENCY:
        return KafkaProducerConfig(
            acks="1",
            enable_idempotence=False,
            compression_type="none",
            linger_ms=0,
            batch_size=16384,  # 16KB
        )
    else:  # BALANCED
        return KafkaProducerConfig()
