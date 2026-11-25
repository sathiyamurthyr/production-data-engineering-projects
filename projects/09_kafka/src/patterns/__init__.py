"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/patterns/__init__.py
"""

from src.patterns.exactly_once import TransactionalStreamProcessor
from src.patterns.dead_letter_queue import DeadLetterQueueHandler, DLQEnvelope, ProcessingException, NonRetryableException, RetryableException
from src.patterns.kafka_connect_patterns import KafkaConnectManager, ConnectorStatus
from src.patterns.cdc_consumer import CDCConsumerParser, CDCEventRecord

__all__ = [
    "TransactionalStreamProcessor",
    "DeadLetterQueueHandler",
    "DLQEnvelope",
    "ProcessingException",
    "NonRetryableException",
    "RetryableException",
    "KafkaConnectManager",
    "ConnectorStatus",
    "CDCConsumerParser",
    "CDCEventRecord",
]
