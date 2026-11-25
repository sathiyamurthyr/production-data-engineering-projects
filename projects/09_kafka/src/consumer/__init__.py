"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/consumer/__init__.py
"""

from src.consumer.kafka_consumer import KafkaEventConsumer, AutoOffsetReset, ProcessedMessage, ConsumerMetrics
from src.consumer.consumer_group_manager import ConsumerGroupManager, PartitionLagInfo, ConsumerGroupSummary
from src.consumer.stream_processor import StreamProcessor, TumblingWindowAggregator, WindowResult

__all__ = [
    "KafkaEventConsumer",
    "AutoOffsetReset",
    "ProcessedMessage",
    "ConsumerMetrics",
    "ConsumerGroupManager",
    "PartitionLagInfo",
    "ConsumerGroupSummary",
    "StreamProcessor",
    "TumblingWindowAggregator",
    "WindowResult",
]
