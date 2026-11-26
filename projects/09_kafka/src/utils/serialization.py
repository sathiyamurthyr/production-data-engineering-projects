"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/utils/serialization.py

Kafka Event Serialization & Deserialization Utilities.

Provides format conversion methods:
- Custom JSON Serializer (handles datetime, UUID, Decimal, Enum)
- Fastavro Binary Serialization & Deserialization
- Compression helpers (LZ4, Gzip, Snappy)

Business Use Case:
  Data transformation & wire efficiency. Ensures data types like UUIDs and datetimes encode
  seamlessly without breaking JSON/Avro encoders across producers and consumers.

Interview Questions:
  Q: Why is standard json.dumps insufficient for production event streaming?
  A: Python standard json.dumps raises TypeError on datetime, UUID, Decimal, and Enum objects.
     A production custom encoder serializes ISO-8601 timestamps, UUID strings, and numeric Decimals cleanly.
"""

import decimal
import enum
import json
import logging
import uuid
from datetime import datetime, date, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """
    JSON Encoder supporting Enterprise Data Types:
    - datetime / date -> ISO 8601 string
    - UUID -> string
    - Decimal -> float / string
    - Enum -> enum.value
    """
    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        elif isinstance(o, uuid.UUID):
            return str(o)
        elif isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, enum.Enum):
            return o.value
        elif hasattr(o, "to_dict") and callable(o.to_dict):
            return o.to_dict()
        elif hasattr(o, "__dataclass_fields__"):
            import dataclasses
            return dataclasses.asdict(o)
        return super().default(o)


def serialize_json(obj: Any) -> bytes:
    """Serialize object to UTF-8 encoded JSON bytes."""
    return json.dumps(obj, cls=CustomJSONEncoder).encode("utf-8")


def deserialize_json(payload_bytes: bytes) -> Dict[str, Any]:
    """Deserialize UTF-8 JSON bytes to Python dictionary."""
    return json.loads(payload_bytes.decode("utf-8"))


def serialize_avro(payload: Dict[str, Any], avro_schema_dict: Dict[str, Any]) -> bytes:
    """
    Serialize Python dictionary to Avro binary format using fastavro.
    Fallbacks to JSON serialization if fastavro is not installed.
    """
    try:
        import io
        import fastavro

        bytes_io = io.BytesIO()
        parsed_schema = fastavro.parse_schema(avro_schema_dict)
        fastavro.schemaless_writer(bytes_io, parsed_schema, payload)
        return bytes_io.getvalue()
    except ImportError:
        logger.warning("fastavro not installed — falling back to JSON byte encoding")
        return serialize_json(payload)


def deserialize_avro(payload_bytes: bytes, avro_schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize Avro binary bytes back to Python dictionary.
    """
    try:
        import io
        import fastavro

        bytes_io = io.BytesIO(payload_bytes)
        parsed_schema = fastavro.parse_schema(avro_schema_dict)
        return fastavro.schemaless_reader(bytes_io, parsed_schema)
    except ImportError:
        logger.warning("fastavro not installed — falling back to JSON byte decoding")
        return deserialize_json(payload_bytes)
