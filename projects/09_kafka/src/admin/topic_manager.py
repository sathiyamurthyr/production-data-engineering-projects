"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/admin/topic_manager.py

Kafka Topic Lifecycle Management.

Provides administration tools for:
- Creating topics with custom partition counts, replication factors, and configs
- Updating topic dynamic configs (retention.ms, max.message.bytes, cleanup.policy)
- Scaling partition count dynamically
- Topic deletion and metadata inspection
- Declarative provisioning of topics from YAML definition files

Business Use Case:
  Real-time platform automation and Infrastructure as Code (IaC). Enables CI/CD pipelines
  to provision topics, retention rules, and compaction policies automatically.

Production Example:
  Sales topic retention policy: `cleanup.policy=delete, retention.ms=604800000` (7 days).
  User profile CDC topic: `cleanup.policy=compact, min.cleanable.dirty.ratio=0.5`.

Interview Questions:
  Q: Can you decrease partition count of an existing topic in Kafka?
  A: No! Partition count can only be increased. Decreasing partition count would mean deleting
     data and breaking key-to-partition mapping. To reduce partitions, you must reindex into a new topic.

  Q: What is the difference between log deletion and log compaction?
  A: Log deletion removes log segments older than retention time/size.
     Log compaction retains at least the latest value for each message key, removing older duplicate keys.
"""

import logging
import os
import yaml
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TopicConfigSpec:
    """Specification model for topic creation."""
    name: str
    num_partitions: int = 6
    replication_factor: int = 1
    config: Dict[str, str] = field(default_factory=dict)


class TopicManager:
    """
    Kafka AdminClient wrapper for topic creation, inspection, and updates.
    Includes mock mode for local testing without active Kafka broker.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.use_mock = use_mock
        self._created_topics: Dict[str, TopicConfigSpec] = {}

        if not use_mock:
            try:
                from confluent_kafka.admin import AdminClient
                self._admin = AdminClient({"bootstrap.servers": bootstrap_servers})
                logger.info("[TopicManager] AdminClient initialized servers=%s", bootstrap_servers)
            except ImportError:
                logger.warning("confluent_kafka not installed — falling back to Mock TopicManager")
                self.use_mock = True

    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 6,
        replication_factor: int = 1,
        retention_ms: Optional[int] = 604800000,  # 7 days
        cleanup_policy: str = "delete",
        extra_config: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Create a single topic with specified partitions and configurations.
        """
        topic_cfg = extra_config or {}
        if retention_ms is not None:
            topic_cfg["retention.ms"] = str(retention_ms)
        topic_cfg["cleanup.policy"] = cleanup_policy

        spec = TopicConfigSpec(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            config=topic_cfg,
        )

        logger.info(
            "[create_topic] Creating topic=%s partitions=%d rf=%d config=%s",
            topic_name, num_partitions, replication_factor, topic_cfg
        )

        if self.use_mock:
            self._created_topics[topic_name] = spec
            return True

        try:
            from confluent_kafka.admin import NewTopic
            new_t = NewTopic(
                topic=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                config=topic_cfg,
            )
            futures = self._admin.create_topics([new_t])

            for t_name, f in futures.items():
                try:
                    f.result()  # Wait for result
                    logger.info("[create_topic] Successfully created %s", t_name)
                    return True
                except Exception as e:
                    logger.error("[create_topic] Topic creation failed for %s: %s", t_name, e)
                    return False
        except Exception as exc:
            logger.error("[create_topic] Admin error: %s", exc)
            return False

    def list_topics(self) -> List[str]:
        """List names of all existing Kafka topics."""
        if self.use_mock:
            return list(self._created_topics.keys())

        try:
            meta = self._admin.list_topics(timeout=10.0)
            return list(meta.topics.keys())
        except Exception as exc:
            logger.error("[list_topics] Error listing topics: %s", exc)
            return []

    def delete_topic(self, topic_name: str) -> bool:
        """Delete a topic from the cluster."""
        logger.info("[delete_topic] Deleting topic %s", topic_name)
        if self.use_mock:
            self._created_topics.pop(topic_name, None)
            return True

        try:
            futures = self._admin.delete_topics([topic_name])
            for t_name, f in futures.items():
                f.result()
            logger.info("[delete_topic] Successfully deleted topic %s", topic_name)
            return True
        except Exception as exc:
            logger.error("[delete_topic] Error deleting topic %s: %s", topic_name, exc)
            return False

    def provision_from_yaml(self, yaml_filepath: str) -> Dict[str, bool]:
        """
        Declaratively provision topics defined in a YAML specification file.
        """
        if not os.path.exists(yaml_filepath):
            logger.error("Topic definition file not found: %s", yaml_filepath)
            return {}

        with open(yaml_filepath, "r", encoding="utf-8") as f:
            yaml_content = yaml.safe_load(f)

        results = {}
        topics_list = yaml_content.get("topics", [])
        for topic_def in topics_list:
            name = topic_def["name"]
            num_part = topic_def.get("partitions", 6)
            rf = topic_def.get("replication_factor", 1)
            cfg = topic_def.get("config", {})

            success = self.create_topic(
                topic_name=name,
                num_partitions=num_part,
                replication_factor=rf,
                extra_config=cfg,
            )
            results[name] = success

        return results
