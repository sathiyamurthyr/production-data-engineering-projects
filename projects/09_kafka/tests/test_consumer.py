"""
Project 09: Apache Kafka for Real-Time Data Engineering
tests/test_consumer.py

Unit tests for Kafka Consumer and Consumer Group Manager.
"""

import pytest
from src.consumer.kafka_consumer import KafkaEventConsumer, ProcessedMessage, _MockMessage
from src.consumer.consumer_group_manager import ConsumerGroupManager


def test_consumer_parse_message(mock_consumer):
    """Test parsing raw Kafka message into ProcessedMessage dataclass."""
    raw = _MockMessage(
        topic="sales-events",
        partition=0,
        offset=105,
        key=b"user-123",
        value=b'{"payload": {"order_id": "ORD-1", "total_amount": 99.99}}',
        headers=[("event_type", b"order_placed")]
    )
    parsed = mock_consumer.parse_message(raw)
    assert parsed is not None
    assert parsed.topic == "sales-events"
    assert parsed.partition == 0
    assert parsed.offset == 105
    assert parsed.key == "user-123"
    assert parsed.value["payload"]["order_id"] == "ORD-1"
    assert parsed.headers.get("event_type") == "order_placed"


def test_consumer_manual_commit(mock_consumer):
    """Test manual offset commit execution."""
    committed = mock_consumer.commit()
    assert committed is True
    metrics = mock_consumer.metrics.to_dict()
    assert metrics["commits_successful"] == 1


def test_consumer_group_manager_lag():
    """Test consumer lag calculation in mock mode."""
    cgm = ConsumerGroupManager(use_mock=True)
    lags = cgm.get_consumer_lag(group_id="analytics-group", topics=["sales-events"])
    assert len(lags) > 0
    for l in lags:
        assert l.topic == "sales-events"
        assert l.lag >= 0
        assert l.log_end_offset >= l.committed_offset


def test_consumer_group_health_summary():
    """Test consumer group health summary generation."""
    cgm = ConsumerGroupManager(use_mock=True)
    summary = cgm.summarize_group_health(group_id="analytics-group", topics=["sales-events"], lag_alert_threshold=100)
    assert summary.group_id == "analytics-group"
    assert summary.partition_count > 0
    assert "state" in summary.to_dict()


def test_offset_reset():
    """Test resetting offsets for a consumer group."""
    cgm = ConsumerGroupManager(use_mock=True)
    success = cgm.reset_group_offsets(group_id="analytics-group", topic="sales-events", strategy="earliest")
    assert success is True
