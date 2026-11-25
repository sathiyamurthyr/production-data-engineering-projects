"""
Project 09: Apache Kafka for Real-Time Data Engineering
tests/test_stream_processor.py

Unit tests for Stream Processing, Tumbling Window Aggregation, DLQ, CDC, and EOS.
"""

from datetime import datetime, timezone
import pytest
from src.consumer.kafka_consumer import ProcessedMessage
from src.consumer.stream_processor import StreamProcessor, TumblingWindowAggregator
from src.patterns.dead_letter_queue import DeadLetterQueueHandler, NonRetryableException
from src.patterns.cdc_consumer import CDCConsumerParser, CDCEventRecord
from src.patterns.exactly_once import TransactionalStreamProcessor


def test_stream_processor_filter_and_enrich(stream_processor):
    """Test filtering cancelled orders and enriching valid orders."""
    valid_msg = ProcessedMessage(
        topic="sales-events",
        partition=0,
        offset=1,
        key="u1",
        value={"payload": {"event_type": "placed", "total_amount": 250.0, "region": "us-east"}},
        headers={},
        timestamp=datetime.now(timezone.utc),
        raw_value_bytes=b""
    )
    enriched = stream_processor.process_sales_event(valid_msg)
    assert enriched is not None
    assert enriched["order_category"] == "Large"
    assert "processed_at" in enriched

    cancelled_msg = ProcessedMessage(
        topic="sales-events",
        partition=0,
        offset=2,
        key="u2",
        value={"payload": {"event_type": "cancelled", "total_amount": 50.0, "region": "us-east"}},
        headers={},
        timestamp=datetime.now(timezone.utc),
        raw_value_bytes=b""
    )
    filtered = stream_processor.process_sales_event(cancelled_msg)
    assert filtered is None
    assert stream_processor.filtered_count == 1


def test_tumbling_window_aggregator():
    """Test tumbling window bucket aggregation and emission."""
    aggregator = TumblingWindowAggregator(window_size_sec=60)
    now = datetime(2026, 1, 1, 12, 0, 10, tzinfo=timezone.utc)

    msg1 = ProcessedMessage(
        topic="sales-events", partition=0, offset=1, key="k1",
        value={"region": "us-east", "total_amount": 100.0},
        headers={}, timestamp=now, raw_value_bytes=b""
    )
    msg2 = ProcessedMessage(
        topic="sales-events", partition=0, offset=2, key="k2",
        value={"region": "us-east", "total_amount": 150.0},
        headers={}, timestamp=now, raw_value_bytes=b""
    )

    aggregator.add_event(msg1, value_extractor=lambda p: float(p["total_amount"]))
    aggregator.add_event(msg2, value_extractor=lambda p: float(p["total_amount"]))

    # Advance watermark to emit closed window
    watermark = datetime(2026, 1, 1, 12, 2, 0, tzinfo=timezone.utc)
    results = aggregator.emit_closed_windows(watermark_dt=watermark, metric_name="total_revenue")

    assert len(results) == 1
    res = results[0]
    assert res.group_key == "us-east"
    assert res.count == 2
    assert res.sum_val == 250.0
    assert res.avg_val == 125.0


def test_dlq_handler(dlq_handler):
    """Test poison message handling routing to Dead Letter Queue."""
    msg = ProcessedMessage(
        topic="sales-events", partition=0, offset=99, key="k",
        value={"invalid": "data"}, headers={}, timestamp=datetime.now(timezone.utc), raw_value_bytes=b""
    )

    def failing_processor(m):
        raise NonRetryableException("Malformed JSON payload")

    success = dlq_handler.process_with_dlq(msg, failing_processor)
    assert success is True
    assert len(dlq_handler.dlq_records_sent) == 1
    env = dlq_handler.dlq_records_sent[0]
    assert env.original_offset == 99
    assert env.error_type == "NonRetryableException"


def test_cdc_parser():
    """Test Debezium CDC message parsing."""
    parser = CDCConsumerParser()
    msg = ProcessedMessage(
        topic="dbserver1.public.users",
        partition=0,
        offset=10,
        key='{"id": 42}',
        value={
            "payload": {
                "op": "u",
                "ts_ms": 1700000000000,
                "source": {"db": "prod", "schema": "public", "table": "users"},
                "before": {"id": 42, "name": "Alice", "email": "old@example.com"},
                "after": {"id": 42, "name": "Alice", "email": "new@example.com"}
            }
        },
        headers={},
        timestamp=datetime.now(timezone.utc),
        raw_value_bytes=b""
    )

    cdc = parser.parse_cdc_message(msg)
    assert cdc is not None
    assert cdc.is_update is True
    changed = cdc.get_changed_fields()
    assert "email" in changed
    assert changed["email"] == ("old@example.com", "new@example.com")


def test_exactly_once_processor():
    """Test transactional read-process-write loop in mock mode."""
    processor = TransactionalStreamProcessor(use_mock=True)
    success = processor.run_transactional_batch(batch_size=5)
    assert success is True
    assert processor.committed_transactions == 1
    assert processor.processed_count == 5
