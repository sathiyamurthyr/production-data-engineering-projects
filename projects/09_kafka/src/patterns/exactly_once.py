"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/patterns/exactly_once.py

Exactly-Once Semantics (EOS) Pattern.

Implements Kafka's transactional read-process-write pattern:
1. Transactional Producer (`transactional.id`)
2. Consumer Isolation Level (`isolation.level=read_committed`)
3. Atomic commit of both output messages AND consumer offsets via `send_offsets_to_transaction()`

Business Use Case:
  Financial transfer & inventory updates. Guarantees that funds deducted from account A
  and credited to account B occur exactly once, preventing double debiting or missing events.

Production Example:
  Payment processing microservice reads `payment-intents`, processes validation, and writes
  to `payments-processed` and `audit-log`. Uses transactions to ensure atomic offset commit and write.

Interview Questions:
  Q: How does Kafka achieve Exactly-Once Processing across read-process-write loops?
  A: 1. Producer Idempotence (`enable.idempotence=true`) prevents duplicate writes from retries.
     2. Transactional Producer (`transactional.id`) coordinates multi-partition writes via Transaction Coordinator.
     3. Atomic Offset Commits: `send_offsets_to_transaction()` commits input offsets into `__consumer_offsets`
        as part of the same transaction as the output records.
     4. Consumers setting `isolation.level=read_committed` ignore aborted transactions.

  Q: What performance trade-off exists with Exactly-Once Semantics?
  A: Latency increases due to 2-phase commit overhead (Transaction Coordinator markers).
     Throughput drops by ~15-30% depending on transaction batch sizes.
"""

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TransactionalStreamProcessor:
    """
    Implements Exactly-Once Processing (EOS) read-process-write loop.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        transactional_id: str = "eos-processor-txn-1",
        input_topic: str = "raw-orders",
        output_topic: str = "processed-orders",
        group_id: str = "eos-consumer-group",
        use_mock: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.transactional_id = transactional_id
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id
        self.use_mock = use_mock
        self.processed_count = 0
        self.committed_transactions = 0

        logger.info(
            "[TransactionalStreamProcessor] Initialized txn_id=%s in=%s out=%s",
            transactional_id, input_topic, output_topic
        )

    def process_record_transform(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transformation logic executed inside transaction boundary."""
        payload = record.get("payload", record)
        amount = float(payload.get("total_amount", 0.0))
        return {
            **payload,
            "processed_amount_usd": round(amount, 2),
            "eos_processed": True,
            "processed_at": time.time(),
        }

    def run_transactional_batch(
        self,
        batch_size: int = 10,
        mock_input_records: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Executes a single transactional read-process-write cycle:
        1. Begin transaction
        2. Read N records from input topic
        3. Transform records
        4. Produce transformed records to output topic
        5. Send consumer offsets to transaction
        6. Commit transaction
        """
        logger.info("[EOS] Starting transaction batch size=%d...", batch_size)

        if self.use_mock or mock_input_records is not None:
            # Simulated transaction run for offline/unit test execution
            records = mock_input_records or [
                {"order_id": f"ORD-{i}", "total_amount": 100.0 + i}
                for i in range(batch_size)
            ]

            processed_batch = []
            for r in records:
                transformed = self.process_record_transform(r)
                processed_batch.append(transformed)

            self.processed_count += len(processed_batch)
            self.committed_transactions += 1
            logger.info(
                "[EOS-Mock] Transaction COMMITTED successfully! Processed %d records.",
                len(processed_batch)
            )
            return True

        try:
            from confluent_kafka import Consumer, Producer, TopicPartition

            # 1. Initialize Producer with transactional config
            producer = Producer({
                "bootstrap.servers": self.bootstrap_servers,
                "transactional.id": self.transactional_id,
                "enable.idempotence": True,
                "acks": "all",
            })
            producer.init_transactions()

            # 2. Initialize Consumer with read_committed isolation level
            consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "isolation.level": "read_committed",  # Essential for EOS!
            })
            consumer.subscribe([self.input_topic])

            # 3. Begin Transaction
            producer.begin_transaction()

            consumed_records = []
            offsets_to_commit = {}

            # Poll records
            for _ in range(batch_size):
                msg = consumer.poll(timeout=1.0)
                if msg is None or msg.error():
                    continue

                val = json.loads(msg.value().decode("utf-8"))
                consumed_records.append(val)

                # Track latest offset per topic/partition
                tp = TopicPartition(msg.topic(), msg.partition())
                offsets_to_commit[tp] = msg.offset() + 1  # Next offset to consume

            if not consumed_records:
                producer.abort_transaction()
                consumer.close()
                return True

            # 4. Transform and Produce output records
            for record in consumed_records:
                out_val = self.process_record_transform(record)
                producer.produce(
                    topic=self.output_topic,
                    key=str(out_val.get("order_id", "")).encode("utf-8"),
                    value=json.dumps(out_val).encode("utf-8"),
                )

            # 5. Send consumer offsets to transaction
            consumer_group_metadata = consumer.consumer_group_metadata()
            tp_offsets = [
                TopicPartition(tp.topic, tp.partition, offset)
                for tp, offset in offsets_to_commit.items()
            ]
            producer.send_offsets_to_transaction(tp_offsets, consumer_group_metadata)

            # 6. Commit Transaction
            producer.commit_transaction()
            self.processed_count += len(consumed_records)
            self.committed_transactions += 1

            consumer.close()
            logger.info("[EOS] Transaction COMMITTED for %d records", len(consumed_records))
            return True

        except Exception as exc:
            logger.error("[EOS] Transaction FAILED — Aborting: %s", exc, exc_info=True)
            try:
                producer.abort_transaction()
            except Exception:
                pass
            return False
