"""
Project 09: Apache Kafka for Real-Time Data Engineering
tests/test_producer.py

Unit tests for Kafka Event Producer and Event Generator.
"""

import pytest
from src.producer.event_generator import EventGenerator
from src.producer.kafka_producer import KafkaEventProducer, PartitionStrategy, CompressionType
from src.producer.producer_config import get_producer_config_profile, ProducerConfigProfile


def test_event_generator_sales(event_generator):
    """Test generating sales events with schema validation."""
    event = event_generator.generate_sale()
    assert "event_id" in event
    assert "order_id" in event
    assert "total_amount" in event
    assert isinstance(event["items"], list)
    assert len(event["items"]) > 0
    assert event["total_amount"] > 0


def test_event_generator_clickstream(event_generator):
    """Test generating clickstream events."""
    event = event_generator.generate_click()
    assert "event_id" in event
    assert "page_type" in event
    assert "session_id" in event


def test_event_generator_iot(event_generator):
    """Test generating IoT sensor readings."""
    reading = event_generator.generate_iot_reading()
    assert "reading_id" in reading
    assert "device_id" in reading
    assert "value" in reading
    assert "sensor_type" in reading


def test_producer_single_event(mock_producer, event_generator):
    """Test producing a single event."""
    sale = event_generator.generate_sale()
    msg_id = mock_producer.produce_event(
        topic="sales-events",
        key=sale["user_id"],
        event=sale,
        headers={"event_type": "order_placed"}
    )
    assert msg_id is not None
    assert len(msg_id) > 0

    metrics = mock_producer.get_metrics()
    assert metrics["messages_produced"] == 1
    assert metrics["messages_failed"] == 0


def test_producer_batch(mock_producer, event_generator):
    """Test producing a batch of events with key extractor."""
    events = [event_generator.generate_sale() for _ in range(25)]
    msg_ids = mock_producer.produce_batch(
        topic="sales-events",
        events=events,
        key_extractor=lambda e: e["order_id"],
        flush_every=10
    )
    assert len(msg_ids) == 25
    metrics = mock_producer.get_metrics()
    assert metrics["messages_produced"] == 25


def test_producer_transactional(mock_producer, event_generator):
    """Test producing events atomically within a transaction."""
    topic_events = [
        {"topic": "sales-events", "event": event_generator.generate_sale(), "key": "key1"},
        {"topic": "audit-log", "event": {"action": "log"}, "key": "key2"},
    ]
    success = mock_producer.produce_with_transaction(topic_events)
    assert success is True


def test_producer_config_profiles():
    """Test retrieving pre-configured producer configuration profiles."""
    zero_loss = get_producer_config_profile(ProducerConfigProfile.ZERO_DATA_LOSS)
    assert zero_loss.acks == "all"
    assert zero_loss.enable_idempotence is True

    high_tp = get_producer_config_profile(ProducerConfigProfile.HIGH_THROUGHPUT)
    assert high_tp.batch_size == 131072
    assert high_tp.linger_ms == 20
