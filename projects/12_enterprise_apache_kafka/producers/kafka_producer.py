"""
Enterprise Kafka Producer

Production patterns for event streaming.
"""

from typing import Any


def create_producer(
    bootstrap_servers: str = "localhost:9092",
    enable_idempotence: bool = True,
    acks: str = "all",
) -> Any:
    """
    Create production-ready Kafka producer.
    
    Business Use Case: Event streaming from applications.
    """
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        enable_idempotence=enable_idempotence,
        acks=acks,
        retries=5,
        batch_size=16384,
        linger_ms=5,
        compression_type="snappy",
    )


def send_with_retry(
    producer: Any,
    topic: str,
    value: dict[str, Any] | str | bytes,
    key: str | None = None,
    max_retries: int = 3,
) -> bool:
    """
    Send message with retry logic.
    
    Business Use Case: Reliable message delivery.
    """
    for attempt in range(max_retries):
        try:
            future = producer.send(
                topic=topic,
                value=value.encode() if isinstance(value, str) else value,
                key=key.encode() if key else None,
            )
            future.get(timeout=10)
            return True
        except Exception:
            if attempt == max_retries - 1:
                raise
            producer.flush()

    return False


def transaction_producer(
    producer: Any,
    topic: str,
    records: list[dict[str, Any]],
) -> None:
    """
    Send messages in transaction.
    
    Business Use Case: Atomic message delivery.
    """
    producer.begin_transaction()

    try:
        for record in records:
            producer.send(topic, record)
        producer.commit_transaction()
    except Exception:
        producer.abort_transaction()
        raise