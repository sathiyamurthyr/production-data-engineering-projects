"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/admin/kafka_admin.py

Cluster Health Monitoring & Admin Management.

Provides utilities for:
- Cluster metadata reporting (brokers, topics, active controller)
- Under-replicated partitions (URP) detection
- Offline partition identification
- Cluster health status reporting for SRE / DevOps alerting

Business Use Case:
  Kafka Cluster SRE observability. Automates health checks and alerts if broker nodes
  drop out of the In-Sync Replica (ISR) pool or if topics lose quorum.

Production Example:
  SRE monitoring script queries cluster metadata every 30 seconds. If `under_replicated_partitions > 0`,
  a PagerDuty incident is triggered for broker investigation.

Interview Questions:
  Q: What is an Under-Replicated Partition (URP)?
  A: A partition where the number of In-Sync Replicas (ISR) is less than the configured replication factor.
     URPs indicate broker hardware failure, network degradation, or disk I/O bottlenecks.

  Q: What happens if a topic loses its leader partition?
  A: Kafka elects a new leader from the ISR pool. If unclean.leader.election.enable=false (default),
     Kafka will NOT elect a non-ISR replica, preserving data integrity but halting writes until ISR recovers.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BrokerInfo:
    id: int
    host: str
    port: int
    is_controller: bool = False


@dataclass
class PartitionHealth:
    topic: str
    partition: int
    leader: int
    replicas: List[int]
    isr: List[int]
    is_under_replicated: bool
    is_offline: bool


@dataclass
class ClusterHealthReport:
    total_brokers: int
    total_topics: int
    total_partitions: int
    under_replicated_partitions: int
    offline_partitions: int
    is_healthy: bool
    brokers: List[BrokerInfo]
    unhealthy_partitions: List[PartitionHealth]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_brokers": self.total_brokers,
            "total_topics": self.total_topics,
            "total_partitions": self.total_partitions,
            "under_replicated_partitions": self.under_replicated_partitions,
            "offline_partitions": self.offline_partitions,
            "is_healthy": self.is_healthy,
            "brokers": [b.__dict__ for b in self.brokers],
            "unhealthy_partitions": [p.__dict__ for p in self.unhealthy_partitions],
        }


class KafkaClusterAdmin:
    """
    Cluster Administrative & Health Check Utility.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.use_mock = use_mock

        if not use_mock:
            try:
                from confluent_kafka.admin import AdminClient
                self._admin = AdminClient({"bootstrap.servers": bootstrap_servers})
            except ImportError:
                logger.warning("confluent_kafka not installed — using Mock KafkaClusterAdmin")
                self.use_mock = True

    def get_cluster_health(self) -> ClusterHealthReport:
        """
        Perform health check on Kafka cluster and report under-replicated or offline partitions.
        """
        if self.use_mock:
            # Synthetic mock cluster health response
            brokers = [
                BrokerInfo(id=1, host="broker-1.kafka", port=9092, is_controller=True),
                BrokerInfo(id=2, host="broker-2.kafka", port=9092, is_controller=False),
                BrokerInfo(id=3, host="broker-3.kafka", port=9092, is_controller=False),
            ]
            return ClusterHealthReport(
                total_brokers=3,
                total_topics=5,
                total_partitions=30,
                under_replicated_partitions=0,
                offline_partitions=0,
                is_healthy=True,
                brokers=brokers,
                unhealthy_partitions=[],
            )

        try:
            meta = self._admin.list_topics(timeout=10.0)
            controller_id = getattr(meta, "controller_id", -1)

            brokers = [
                BrokerInfo(
                    id=b.id,
                    host=b.host,
                    port=b.port,
                    is_controller=(b.id == controller_id)
                )
                for b in meta.brokers.values()
            ]

            total_partitions = 0
            urp_count = 0
            offline_count = 0
            unhealthy: List[PartitionHealth] = []

            for t_name, t_meta in meta.topics.items():
                for p_id, p_meta in t_meta.partitions.items():
                    total_partitions += 1
                    is_urp = len(p_meta.isrs) < len(p_meta.replicas)
                    is_offline = p_meta.leader < 0

                    if is_urp:
                        urp_count += 1
                    if is_offline:
                        offline_count += 1

                    if is_urp or is_offline:
                        unhealthy.append(
                            PartitionHealth(
                                topic=t_name,
                                partition=p_id,
                                leader=p_meta.leader,
                                replicas=list(p_meta.replicas),
                                isr=list(p_meta.isrs),
                                is_under_replicated=is_urp,
                                is_offline=is_offline,
                            )
                        )

            is_healthy = (urp_count == 0 and offline_count == 0)

            return ClusterHealthReport(
                total_brokers=len(brokers),
                total_topics=len(meta.topics),
                total_partitions=total_partitions,
                under_replicated_partitions=urp_count,
                offline_partitions=offline_count,
                is_healthy=is_healthy,
                brokers=brokers,
                unhealthy_partitions=unhealthy,
            )

        except Exception as exc:
            logger.error("[get_cluster_health] Health check failed: %s", exc)
            return ClusterHealthReport(
                total_brokers=0,
                total_topics=0,
                total_partitions=0,
                under_replicated_partitions=0,
                offline_partitions=0,
                is_healthy=False,
                brokers=[],
                unhealthy_partitions=[],
            )
