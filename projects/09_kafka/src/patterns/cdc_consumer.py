"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/patterns/cdc_consumer.py

Debezium Change Data Capture (CDC) Consumer Pattern.

Parses database CDC stream events produced by Debezium (PostgreSQL WAL / MySQL Binlog):
- Extraction of `before` vs `after` row states
- Identification of CDC operation types:
    'c' -> Create / INSERT
    'u' -> Update / UPDATE
    'd' -> Delete / DELETE
    'r' -> Read / Snapshot Initial Load
- Audit metadata extraction (source database, table, transaction ID, LSN / binlog position)
- Conversion of raw CDC events into unified analytical events or SCD Type 2 dimension updates

Business Use Case:
  Real-time database replication to Data Warehouse (Snowflake, Databricks Delta Lake) without bulk ETL.
  Captures row-level database changes instantly as microservices commit transactions.

Production Example:
  Postgres `public.users` table changes captured by Debezium Postgres Connector into `dbserver1.public.users`.
  This CDC consumer parses updates and maintains a real-time replica in Delta Lake.

Interview Questions:
  Q: What is Change Data Capture (CDC) and how does Debezium work with Kafka?
  A: CDC captures row-level database modifications (INSERT, UPDATE, DELETE) by tailing transaction logs
     (PostgreSQL WAL, MySQL Binlog, Oracle Redo Log). Debezium publishes these change records as JSON/Avro
     events to Kafka topics, enabling low-latency database streaming without impacting database CPU/queries.

  Q: How do you handle DELETE operations in CDC consumer streams?
  A: Debezium sends a tombstone record (null payload with message key = primary key) following a Delete event ('d').
     Consumers can either soft-delete records in downstream storage or append a deleted_at timestamp.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from src.consumer.kafka_consumer import ProcessedMessage

logger = logging.getLogger(__name__)


@dataclass
class CDCEventRecord:
    """Parsed Debezium CDC Event envelope."""
    operation: str              # 'c' (Create), 'u' (Update), 'd' (Delete), 'r' (Read)
    database_name: str
    schema_name: str
    table_name: str
    ts_ms: int
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    primary_key: Optional[Dict[str, Any]]
    transaction_id: Optional[str]

    @property
    def is_insert(self) -> bool:
        return self.operation in ('c', 'r')

    @property
    def is_update(self) -> bool:
        return self.operation == 'u'

    @property
    def is_delete(self) -> bool:
        return self.operation == 'd'

    def get_changed_fields(self) -> Dict[str, Tuple[Any, Any]]:
        """
        For UPDATE operations, compare before and after states to return changed fields.
        Returns dict of: field_name -> (old_value, new_value)
        """
        if not self.is_update or not self.before_state or not self.after_state:
            return {}

        changes = {}
        for k, new_val in self.after_state.items():
            old_val = self.before_state.get(k)
            if old_val != new_val:
                changes[k] = (old_val, new_val)
        return changes


class CDCConsumerParser:
    """
    Debezium CDC Message Parser & Transformation Engine.
    """

    def parse_cdc_message(self, msg: ProcessedMessage) -> Optional[CDCEventRecord]:
        """
        Parse raw ProcessedMessage containing Debezium CDC envelope.
        """
        raw_dict = msg.value
        payload = raw_dict.get("payload", raw_dict)

        op = payload.get("op")
        if not op:
            logger.warning("[CDCConsumerParser] Message lacks CDC 'op' field offset=%d", msg.offset)
            return None

        source = payload.get("source", {})
        db_name = source.get("db", "unknown")
        schema_name = source.get("schema", "public")
        table_name = source.get("table", "unknown")
        ts_ms = payload.get("ts_ms", 0)

        before = payload.get("before")
        after = payload.get("after")
        tx_info = payload.get("transaction", {})
        tx_id = tx_info.get("id") if tx_info else None

        pk = None
        if msg.key:
            try:
                pk = json.loads(msg.key)
            except Exception:
                pk = {"key": msg.key}

        event = CDCEventRecord(
            operation=op,
            database_name=db_name,
            schema_name=schema_name,
            table_name=table_name,
            ts_ms=ts_ms,
            before_state=before,
            after_state=after,
            primary_key=pk,
            transaction_id=tx_id,
        )

        logger.debug(
            "[parse_cdc_message] CDC op=%s db=%s table=%s ts=%d",
            op, db_name, table_name, ts_ms
        )
        return event

    def transform_cdc_to_analytical_envelope(self, cdc_record: CDCEventRecord) -> Dict[str, Any]:
        """
        Convert CDC record into standardized analytical change log format.
        """
        effective_payload = cdc_record.after_state if not cdc_record.is_delete else cdc_record.before_state
        op_map = {
            "c": "INSERT",
            "r": "SNAPSHOT_READ",
            "u": "UPDATE",
            "d": "DELETE"
        }

        return {
            "cdc_metadata": {
                "operation_type": op_map.get(cdc_record.operation, "UNKNOWN"),
                "source_db": cdc_record.database_name,
                "source_table": cdc_record.table_name,
                "event_timestamp": datetime.fromtimestamp(cdc_record.ts_ms / 1000.0, tz=timezone.utc).isoformat(),
                "changed_fields": list(cdc_record.get_changed_fields().keys()) if cdc_record.is_update else [],
            },
            "record_data": effective_payload,
        }
