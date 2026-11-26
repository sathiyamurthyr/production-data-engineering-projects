"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/admin/__init__.py
"""

from src.admin.topic_manager import TopicManager, TopicConfigSpec
from src.admin.schema_registry import LocalSchemaRegistry, CompatibilityMode, SALES_EVENT_AVRO_SCHEMA
from src.admin.kafka_admin import KafkaClusterAdmin, ClusterHealthReport, BrokerInfo, PartitionHealth

__all__ = [
    "TopicManager",
    "TopicConfigSpec",
    "LocalSchemaRegistry",
    "CompatibilityMode",
    "SALES_EVENT_AVRO_SCHEMA",
    "KafkaClusterAdmin",
    "ClusterHealthReport",
    "BrokerInfo",
    "PartitionHealth",
]
