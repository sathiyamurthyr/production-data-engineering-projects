"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/consumer/consumer_group_manager.py

Consumer Group Management & Lag Monitoring.

Provides operational utilities for:
- Consumer lag calculation across topics and partitions
- Group metadata inspection (active members, partition assignments)
- Programmatic offset reset (earliest, latest, specific offset, timestamp)
- Alerting thresholds for excessive consumer lag

Business Use Case:
  Real-time monitoring systems track consumer lag to detect lagging consumers,
  stuck stream processors, or partition hot-spotting before SLAs are breached.

Production Example:
  Airflow or Datadog polls lag metrics every 60 seconds. If lag exceeds 10,000 messages
  on `sales-events`, a Kubernetes HPA automatically scales up the consumer group pod count.

Interview Questions:
  Q: How is consumer lag calculated in Kafka?
  A: Lag = (Log End Offset) - (Current Consumer Committed Offset)
     Log End Offset (LEO) is the offset of the next message to be written to partition.
     Committed Offset is the last offset acknowledged by the consumer group.

  Q: What causes consumer lag spikes in production?
  A: 1. Upstream traffic burst (black friday sales spike)
     2. Slow downstream database writes (backpressure)
     3. Long processing time per message exceeding max.poll.interval.ms
     4. Uneven partition key distribution leading to hot partitions
     5. Repeated consumer crashes / constant group rebalancing

  Q: How do you reset consumer group offsets in production?
  A: 1. Stop all active instances of the consumer group
     2. Use kafka-consumer-groups CLI or AdminClient to reset offsets
     3. Option `--to-earliest`, `--to-latest`, `--to-offset <N>`, or `--to-datetime <ISO>`
     4. Restart the consumer group
"""

import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PartitionLagInfo:
    """Lag details for a specific topic partition."""
    topic: str
    partition: int
    log_end_offset: int
    committed_offset: int
    lag: int
    consumer_id: Optional[str] = None
    host: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsumerGroupSummary:
    """Aggregate health and status of a consumer group."""
    group_id: str
    state: str               # Stable, PreparingRebalance, CompletingRebalance, Empty, Dead
    total_lag: int
    partition_count: int
    member_count: int
    partitions_behind: List[PartitionLagInfo]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "state": self.state,
            "total_lag": self.total_lag,
            "partition_count": self.partition_count,
            "member_count": self.member_count,
            "partitions_behind": [p.to_dict() for p in self.partitions_behind],
        }


class ConsumerGroupManager:
    """
    Consumer Group Administrator & Lag Monitoring Utility.

    Communicates with Kafka brokers via AdminClient / Consumer APIs
    to inspect group state and manage offsets.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.use_mock = use_mock
        logger.info("[ConsumerGroupManager] Initialized servers=%s", bootstrap_servers)

    def get_consumer_lag(
        self,
        group_id: str,
        topics: List[str],
    ) -> List[PartitionLagInfo]:
        """
        Calculate consumer lag for each partition across specified topics.

        Args:
            group_id: Consumer group ID
            topics: Target topic names

        Returns:
            List of PartitionLagInfo dataclass instances
        """
        if self.use_mock:
            # Return synthetic lag data for test execution
            return [
                PartitionLagInfo(
                    topic=topic,
                    partition=p,
                    log_end_offset=1000 + (p * 500),
                    committed_offset=950 + (p * 490),
                    lag=50 + (p * 10),
                    consumer_id=f"consumer-{group_id}-{p}",
                    host="10.0.0.1"
                )
                for topic in topics
                for p in range(3)
            ]

        lag_results: List[PartitionLagInfo] = []
        try:
            from confluent_kafka.admin import AdminClient
            from confluent_kafka import Consumer, TopicPartition

            # Temporary consumer to fetch offsets
            consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": group_id,
                "enable.auto.commit": False,
            })

            for topic in topics:
                # Obtain metadata for partition count
                meta = consumer.list_topics(topic=topic, timeout=10.0)
                if topic not in meta.topics:
                    logger.warning("Topic %s not found in metadata", topic)
                    continue

                partitions = meta.topics[topic].partitions.keys()
                tps = [TopicPartition(topic, p) for p in partitions]

                # Fetch committed offsets
                committed = consumer.committed(tps, timeout=10.0)

                for tp in committed:
                    # Query high watermark (Log End Offset)
                    low_offset, high_offset = consumer.get_watermark_offsets(
                        TopicPartition(tp.topic, tp.partition), timeout=10.0
                    )
                    comm_offset = tp.offset if tp.offset >= 0 else low_offset
                    lag = max(0, high_offset - comm_offset)

                    lag_results.append(
                        PartitionLagInfo(
                            topic=tp.topic,
                            partition=tp.partition,
                            log_end_offset=high_offset,
                            committed_offset=comm_offset,
                            lag=lag,
                        )
                    )

            consumer.close()

        except Exception as exc:
            logger.error("[get_consumer_lag] Error calculating lag: %s", exc)

        return lag_results

    def summarize_group_health(
        self,
        group_id: str,
        topics: List[str],
        lag_alert_threshold: int = 1000,
    ) -> ConsumerGroupSummary:
        """
        Analyze consumer group health and flag partitions exceeding lag alert threshold.

        Args:
            group_id: Consumer group name
            topics: Subscribed topics
            lag_alert_threshold: Lag count above which warning alerts trigger

        Returns:
            ConsumerGroupSummary dataclass
        """
        lags = self.get_consumer_lag(group_id, topics)
        total_lag = sum(l.lag for l in lags)
        over_threshold = [l for l in lags if l.lag > lag_alert_threshold]

        state = "Stable"
        if over_threshold:
            state = "Lagging"

        summary = ConsumerGroupSummary(
            group_id=group_id,
            state=state,
            total_lag=total_lag,
            partition_count=len(lags),
            member_count=len(set(l.consumer_id for l in lags if l.consumer_id)),
            partitions_behind=over_threshold,
        )

        logger.info(
            "[summarize_group_health] group=%s state=%s total_lag=%d alarming_partitions=%d",
            group_id, state, total_lag, len(over_threshold)
        )
        return summary

    def reset_group_offsets(
        self,
        group_id: str,
        topic: str,
        strategy: str = "earliest",  # earliest, latest, to_offset
        target_offset: Optional[int] = None,
    ) -> bool:
        """
        Reset offsets for a consumer group on a given topic.

        WARNING: The consumer group MUST be inactive (no running instances)
        before executing offset resets.
        """
        logger.warning(
            "[reset_group_offsets] Resetting offset for group=%s topic=%s strategy=%s",
            group_id, topic, strategy
        )
        if self.use_mock:
            logger.info("[MockReset] Reset successful strategy=%s", strategy)
            return True

        try:
            from confluent_kafka import Consumer, TopicPartition, OFFSET_BEGINNING, OFFSET_END

            consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": group_id,
                "enable.auto.commit": False,
            })

            meta = consumer.list_topics(topic=topic, timeout=10.0)
            if topic not in meta.topics:
                logger.error("Topic %s not found", topic)
                return False

            partitions = meta.topics[topic].partitions.keys()
            new_offsets = []

            for p in partitions:
                tp = TopicPartition(topic, p)
                if strategy == "earliest":
                    tp.offset = OFFSET_BEGINNING
                elif strategy == "latest":
                    tp.offset = OFFSET_END
                elif strategy == "to_offset" and target_offset is not None:
                    tp.offset = target_offset
                else:
                    raise ValueError(f"Invalid strategy or target offset: {strategy}")

                new_offsets.append(tp)

            consumer.commit(offsets=new_offsets, asynchronous=False)
            consumer.close()
            logger.info("[reset_group_offsets] Reset completed for %d partitions", len(new_offsets))
            return True

        except Exception as exc:
            logger.error("[reset_group_offsets] Failed to reset offsets: %s", exc)
            return False
