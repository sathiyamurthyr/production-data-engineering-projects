"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/patterns/kafka_connect_patterns.py

Kafka Connect Integration Patterns.

Provides automation for:
- Deploying and updating Source & Sink connectors via Kafka Connect REST API
- Building production configurations for Snowflake, S3, JDBC, and Debezium CDC connectors
- Configuring Single Message Transformations (SMTs)
- Monitoring connector task state and restarting failed tasks automatically

Business Use Case:
  No-code / low-code stream ingestion. Moves data automatically from databases (CDC) into Kafka
  and streams Kafka events directly into cloud data warehouses (Snowflake) or object stores (S3).

Production Example:
  Snowflake Sink Connector continuously consumes `sales-events` and streams micro-batches into
  Snowflake `RAW_EVENTS.SALES` table with zero custom ingestion code.

Interview Questions:
  Q: What are Single Message Transformations (SMTs) in Kafka Connect?
  A: SMTs are lightweight, inline transformations applied to records as they pass through Connect.
     Examples: Filtering fields (`ReplaceField`), updating topic names (`RegexRouter`), converting timestamps (`TimestampConverter`),
     or unwrapping Debezium CDC envelopes (`ExtractNewRecordState`).

  Q: Explain Kafka Connect Architecture (Workers, Connectors, Tasks).
  A: Worker: JVM process executing Connect. Can run in Standalone or Distributed mode.
     Connector: Configures job logically (defines what to read/write, partitioning, task count).
     Task: Worker thread executing actual data copying logic across partitions.
"""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConnectorStatus:
    name: str
    connector_state: str   # RUNNING, PAUSED, FAILED
    tasks: List[Dict[str, Any]]
    worker_id: str


class KafkaConnectManager:
    """
    Kafka Connect REST API Client and Configuration Builder.
    """

    def __init__(
        self,
        connect_url: str = "http://localhost:8083",
        use_mock: bool = True,
    ):
        self.connect_url = connect_url.rstrip("/")
        self.use_mock = use_mock
        self._mock_connectors: Dict[str, Dict[str, Any]] = {}
        logger.info("[KafkaConnectManager] Initialized connect_url=%s", self.connect_url)

    def list_connectors(self) -> List[str]:
        """List active connector names."""
        if self.use_mock:
            return list(self._mock_connectors.keys())

        try:
            req = urllib.request.Request(f"{self.connect_url}/connectors")
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.error("[list_connectors] HTTP Request failed: %s", exc)
            return []

    def create_or_update_connector(
        self,
        name: str,
        config: Dict[str, Any],
    ) -> bool:
        """Create or update a connector configuration via REST API PUT."""
        logger.info("[create_or_update_connector] Registering connector: %s", name)

        if self.use_mock:
            self._mock_connectors[name] = config
            return True

        try:
            url = f"{self.connect_url}/connectors/{name}/config"
            data_bytes = json.dumps(config).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="PUT"
            )
            with urllib.request.urlopen(req) as resp:
                return resp.status in (200, 201)
        except Exception as exc:
            logger.error("[create_or_update_connector] Failed for %s: %s", name, exc)
            return False

    def get_connector_status(self, name: str) -> ConnectorStatus:
        """Fetch connector and task status."""
        if self.use_mock:
            return ConnectorStatus(
                name=name,
                connector_state="RUNNING",
                tasks=[{"id": 0, "state": "RUNNING", "worker_id": "worker-1:8083"}],
                worker_id="worker-1:8083"
            )

        try:
            url = f"{self.connect_url}/connectors/{name}/status"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                connector_info = res.get("connector", {})
                tasks_info = res.get("tasks", [])
                return ConnectorStatus(
                    name=name,
                    connector_state=connector_info.get("state", "UNKNOWN"),
                    tasks=tasks_info,
                    worker_id=connector_info.get("worker_id", "UNKNOWN"),
                )
        except Exception as exc:
            logger.error("[get_connector_status] Failed for %s: %s", name, exc)
            return ConnectorStatus(name=name, connector_state="FAILED", tasks=[], worker_id="UNKNOWN")

    # ──────────────────────────────────────────────
    # Pre-built Connector Configuration Builders
    # ──────────────────────────────────────────────

    @staticmethod
    def build_snowflake_sink_config(
        connector_name: str,
        topics: str,
        snowflake_url: str,
        snowflake_user: str,
        database: str,
        schema: str,
        private_key_pem: str,
    ) -> Dict[str, Any]:
        """
        Generate enterprise Snowflake Sink Connector configuration.
        """
        return {
            "connector.class": "com.snowflake.kafkaconnect.SnowflakeSinkConnector",
            "tasks.max": "3",
            "topics": topics,
            "snowflake.url.name": snowflake_url,
            "snowflake.user.name": snowflake_user,
            "snowflake.database.name": database,
            "snowflake.schema.name": schema,
            "snowflake.private.key": private_key_pem,
            "key.converter": "org.apache.kafka.connect.storage.StringConverter",
            "value.converter": "com.snowflake.kafkaconnect.converter.SnowflakeJsonConverter",
            # Single Message Transformation: Mask sensitive credit card field
            "transforms": "MaskCC",
            "transforms.MaskCC.type": "org.apache.kafka.connect.transforms.MaskField$Value",
            "transforms.MaskCC.fields": "card_number",
            "transforms.MaskCC.replacement": "xxxx-xxxx-xxxx-xxxx",
        }

    @staticmethod
    def build_s3_sink_config(
        connector_name: str,
        topics: str,
        s3_bucket: str,
        s3_region: str,
        flush_size: int = 10000,
        rotate_interval_ms: int = 300000,
    ) -> Dict[str, Any]:
        """
        Generate S3 Sink Connector configuration (Parquet output format with time partitioning).
        """
        return {
            "connector.class": "io.confluent.connect.s3.S3SinkConnector",
            "tasks.max": "4",
            "topics": topics,
            "s3.bucket.name": s3_bucket,
            "s3.region": s3_region,
            "s3.part.size": "5242880",  # 5MB part size
            "flush.size": str(flush_size),
            "rotate.interval.ms": str(rotate_interval_ms),
            "storage.class": "io.confluent.connect.s3.storage.S3Storage",
            "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
            "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
            "partition.duration.ms": "3600000",  # Hourly sub-folders
            "path.format": "'year'=YYYY/'month'=MM/'day'=dd/'hour'=HH",
            "locale": "en-US",
            "timezone": "UTC",
        }
