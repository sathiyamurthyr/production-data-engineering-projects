"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/producer/__init__.py
"""

from src.producer.kafka_producer import KafkaEventProducer, PartitionStrategy, CompressionType, DeliveryReport
from src.producer.event_generator import EventGenerator, SaleEvent, ClickEvent, IoTReading
from src.producer.producer_config import KafkaProducerConfig, ProducerConfigProfile, get_producer_config_profile

__all__ = [
    "KafkaEventProducer",
    "PartitionStrategy",
    "CompressionType",
    "DeliveryReport",
    "EventGenerator",
    "SaleEvent",
    "ClickEvent",
    "IoTReading",
    "KafkaProducerConfig",
    "ProducerConfigProfile",
    "get_producer_config_profile",
]
