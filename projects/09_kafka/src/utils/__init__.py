"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/utils/__init__.py
"""

from src.utils.serialization import (
    CustomJSONEncoder,
    serialize_json,
    deserialize_json,
    serialize_avro,
    deserialize_avro,
)
from src.utils.kafka_utils import (
    parse_bootstrap_servers,
    check_kafka_connectivity,
    wait_for_kafka_ready,
)

__all__ = [
    "CustomJSONEncoder",
    "serialize_json",
    "deserialize_json",
    "serialize_avro",
    "deserialize_avro",
    "parse_bootstrap_servers",
    "check_kafka_connectivity",
    "wait_for_kafka_ready",
]
