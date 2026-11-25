"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/admin/schema_registry.py

Confluent Schema Registry & Avro Schema Management.

Provides utilities for:
- Registering and fetching Avro schemas from Schema Registry
- Validating message payloads against Avro schema schemas
- Checking schema compatibility modes (BACKWARD, FORWARD, FULL, NONE)
- Schema evolution testing (ensuring safe field additions/removals)

Business Use Case:
  Data governance and contract enforcement. Prevents malformed producer records from
  breaking downstream consumer pipelines by asserting strict schema compatibility.

Production Example:
  Avro schemas enforce contract validation on `sales-events`. When the checkout service
  adds a new field `device_id`, the Schema Registry checks BACKWARD compatibility to ensure
  old analytics consumers will not crash.

Interview Questions:
  Q: Why use Avro over JSON/Protobuf in Kafka pipelines?
  A: Avro provides compact binary encoding without including schema headers in every message.
     Schemas are stored centrally in Schema Registry and referenced by a 4-byte Schema ID,
     saving up to 80% bandwidth over raw JSON while retaining strong typing.

  Q: Explain Schema Compatibility Modes (BACKWARD vs FORWARD vs FULL).
  A: BACKWARD: New schema can read data written by previous schema (Consumers updated first).
     FORWARD: Old schema can read data written by new schema (Producers updated first).
     FULL: Old and new schemas are completely mutually compatible.
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CompatibilityMode(str, Enum):
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    FULL = "FULL"
    NONE = "NONE"


# Sample Production Avro Schemas
SALES_EVENT_AVRO_SCHEMA = {
    "type": "record",
    "name": "SaleEventRecord",
    "namespace": "com.dediaries.kafka",
    "doc": "Avro schema for sales and order lifecycle events",
    "fields": [
        {"name": "event_id", "type": "string", "doc": "Unique event UUID"},
        {"name": "order_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "region", "type": "string"},
        {"name": "total_amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"},
        {"name": "event_timestamp", "type": "string"},
        {
            "name": "coupon_code",
            "type": ["null", "string"],
            "default": None,
            "doc": "Optional coupon code used",
        },
    ],
}


class LocalSchemaRegistry:
    """
    In-Memory Schema Registry client & fastavro validator.
    Simulates Confluent Schema Registry HTTP service for standalone & test execution.
    """

    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url or "http://localhost:8081"
        self._schemas_by_subject: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._id_counter = 1000
        logger.info("[LocalSchemaRegistry] Initialized url=%s", self.registry_url)

    def register_schema(
        self,
        subject: str,
        avro_schema_dict: Dict[str, Any],
    ) -> int:
        """
        Register a new schema under a subject (e.g. 'sales-events-value').

        Returns:
            schema_id (int): Unique integer ID assigned to schema
        """
        if subject not in self._schemas_by_subject:
            self._schemas_by_subject[subject] = {}

        # Check if identical schema already exists
        for schema_id, existing_schema in self._schemas_by_subject[subject].items():
            if existing_schema == avro_schema_dict:
                logger.info("[register_schema] Subject %s schema already registered with ID %d", subject, schema_id)
                return schema_id

        self._id_counter += 1
        new_id = self._id_counter
        self._schemas_by_subject[subject][new_id] = avro_schema_dict
        logger.info("[register_schema] Registered subject=%s schema_id=%d", subject, new_id)
        return new_id

    def get_schema(self, subject: str, schema_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve registered schema by subject and ID."""
        return self._schemas_by_subject.get(subject, {}).get(schema_id)

    def validate_payload(
        self,
        payload: Dict[str, Any],
        avro_schema_dict: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a Python dictionary against an Avro schema using fastavro if available,
        or fallback basic type checking.
        """
        try:
            import fastavro
            from fastavro.validation import validate

            parsed_schema = fastavro.parse_schema(avro_schema_dict)
            isValid = validate(payload, parsed_schema)
            if isValid:
                return True, None
            else:
                return False, "Validation failed against fastavro schema"
        except ImportError:
            # Basic validation fallback
            required_fields = [
                f["name"] for f in avro_schema_dict.get("fields", [])
                if "default" not in f and not (isinstance(f.get("type"), list) and "null" in f.get("type"))
            ]
            missing = [rf for rf in required_fields if rf not in payload]
            if missing:
                return False, f"Missing required fields: {missing}"
            return True, None
        except Exception as exc:
            return False, str(exc)

    def check_backward_compatibility(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that new_schema is BACKWARD compatible with old_schema.

        Rule for BACKWARD compatibility:
        - New fields MUST have default values.
        - Required fields from old schema MUST NOT be removed.
        """
        old_fields = {f["name"]: f for f in old_schema.get("fields", [])}
        new_fields = {f["name"]: f for f in new_schema.get("fields", [])}

        # Check for removed fields without default in old schema
        for old_name, old_f in old_fields.items():
            if old_name not in new_fields:
                if "default" not in old_f:
                    return False, f"Field '{old_name}' removed without default value"

        # Check newly added fields in new schema have defaults
        for new_name, new_f in new_fields.items():
            if new_name not in old_fields:
                if "default" not in new_f and not (isinstance(new_f.get("type"), list) and "null" in new_f.get("type")):
                    return False, f"Newly added field '{new_name}' lacks a default value"

        return True, None
