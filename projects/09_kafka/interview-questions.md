# 🎯 Apache Kafka Data Engineering Interview Q&A (30+ Real World Questions)

> **Data Engineering Diaries** | Project 09: Apache Kafka for Real-Time Data Engineering  
> Author: Sathiya Murthy

---

## Category 1: Core Kafka Architecture & Fundamentals

### Q1: What is Apache Kafka and how does its architecture differ from traditional message brokers like RabbitMQ?
**Answer:**  
Apache Kafka is a distributed, append-only, partitioned commit log service designed for high-throughput stream processing. Unlike traditional message brokers (like RabbitMQ) that follow a "smart broker, dumb consumer" model (where the broker tracks message state and deletes records immediately upon ACK), Kafka operates on a "dumb broker, smart consumer" model:
- Messages are immutable and appended sequentially to log files on disk.
- Consumers maintain their own position in the log using **Offsets**.
- Messages are retained based on time/size configuration (`retention.ms`), allowing consumers to replay historical streams at any time.

---

### Q2: Explain the role of Partitions, Segment Files, and Offsets in Kafka.
**Answer:**  
- **Partition**: A single topic is split into $N$ partitions distributed across cluster brokers to achieve horizontal throughput scaling. A partition is the unit of parallelism in Kafka.
- **Segment File**: Each partition is physically stored on disk as a sequence of segment files (`.log`, `.index`, `.timeindex`). Segments are rotated when they reach max size (e.g. 1GB) or age (`segment.ms`).
- **Offset**: A monotonically increasing 64-bit integer assigned to each record within a partition that uniquely identifies its position.

---

### Q3: What is the In-Sync Replicas (ISR) list and why is `min.insync.replicas` crucial?
**Answer:**  
- **ISR (In-Sync Replicas)**: The subset of partition replica brokers that are caught up with the leader broker within `replica.lag.time.max.ms`.
- **`min.insync.replicas`**: Broker/Topic configuration that specifies the minimum number of ISR replicas that MUST acknowledge a write when a producer uses `acks=all`. If the active ISR count drops below `min.insync.replicas`, the leader rejects new write requests with a `NotEnoughReplicasException`, guaranteeing zero data loss.

---

### Q4: How does KRaft (Kafka Raft Metadata Mode) replace ZooKeeper in modern Kafka?
**Answer:**  
Starting in Kafka 3.3+, KRaft replaces external ZooKeeper metadata management:
- **Architecture**: A subset of Kafka brokers are elected as Controller nodes using a consensus algorithm based on Raft.
- **Benefits**:
  1. Metadata stored in internal `@metadata` Kafka topic.
  2. Eliminates metadata synchronization bottleneck between ZooKeeper and Kafka controllers.
  3. Supports scaling to millions of partitions per cluster with sub-second failover.

---

## Category 2: Producer Guarantees & Tuning

### Q5: What is the difference between `acks=0`, `acks=1`, and `acks=all`?
**Answer:**  
- **`acks=0`**: Producer returns immediately after pushing message into network socket. Fire-and-forget. Maximum throughput, high data loss risk.
- **`acks=1`**: Producer waits for the partition Leader to write to local log. Medium throughput, data loss risk if Leader crashes before replicating to ISR.
- **`acks=all` (or `-1`)**: Producer waits for the Leader AND all current ISR replicas to acknowledge the write. Zero data loss guarantee when combined with `min.insync.replicas >= 2`.

---

### Q6: How does Producer Idempotence (`enable.idempotence=true`) work under the hood?
**Answer:**  
When `enable.idempotence=true`:
1. Broker assigns a unique 64-bit Producer ID (PID) during initialization.
2. Producer attaches PID and a sequence number (0, 1, 2...) to every message sent to a partition.
3. Broker stores the highest sequence number per PID for each partition.
4. If a network retry occurs, the broker detects duplicate sequence numbers and discards duplicates silently while acknowledging success to producer.

---

### Q7: How do `linger.ms` and `batch.size` impact producer throughput and latency?
**Answer:**  
- **`batch.size`**: Maximum bytes allowed per message batch (e.g. 64KB).
- **`linger.ms`**: Maximum time producer delays sending a batch to wait for additional records to accumulate.
- **Impact**: Setting `linger.ms=10` and `batch.size=65536` allows smaller individual records to combine into larger batches. Larger batches increase network transmission efficiency, improve compression ratios (LZ4/Snappy), and boost overall throughput by 10x-100x at the cost of $10\text{ms}$ latency.

---

## Category 3: Consumer Groups & Offset Management

### Q8: What happens during a Consumer Group Rebalance?
**Answer:**  
When a consumer joins, leaves, or crashes, or when topic partitions increase:
1. Group Coordinator triggers a rebalance.
2. Under Eager Rebalance, all consumers stop processing and revoke assigned partitions.
3. Under **Cooperative Sticky Reassignor** (`cooperative-sticky`), consumers only revoke partitions being moved, allowing unaffected partitions to continue processing without pipeline stall.
4. Assigned partitions are recalculated and assigned to group members.

---

### Q9: Why is `enable.auto.commit=false` recommended in data engineering pipelines?
**Answer:**  
Auto-commit (`enable.auto.commit=true`) commits offsets periodically on a timer regardless of processing success. If worker node crashes after auto-commit but before database write completes, records are lost. Manual commit (`enable.auto.commit=false`) after processing guarantees **At-Least-Once Delivery**.

---

### Q10: How do you calculate and monitor Consumer Lag?
**Answer:**  
$$\text{Lag} = \text{Log End Offset (LEO)} - \text{Committed Offset}$$
Monitored using `kafka-consumer-groups.sh` CLI or Prometheus JMX exporter. High lag indicates slow processing, downstream database backpressure, or unhandled exceptions.

---

## Category 4: Advanced Streaming Patterns

### Q11: Explain Exactly-Once Semantics (EOS) in Kafka.
**Answer:**  
EOS guarantees that in a read-process-write loop, each message is processed exactly once downstream. Achieved by:
1. Idempotent Producer (`enable.idempotence=true`).
2. Transactional Producer (`transactional.id`).
3. Atomic commits of output records AND input consumer offsets via `send_offsets_to_transaction()`.
4. Consumers set `isolation.level=read_committed`.

---

### Q12: How do you implement Dead Letter Queue (DLQ) for poison messages?
**Answer:**  
Catch exceptions during record processing. Unrecoverable errors (JSON parse failure) bypass retries and publish directly to a `.DLQ` topic enriched with diagnostic headers (`stacktrace`, `original_offset`, `timestamp`). This prevents pipeline blockage.

---

### Q13: What is Change Data Capture (CDC) with Debezium?
**Answer:**  
Debezium tails database transaction logs (PostgreSQL WAL, MySQL Binlog) and streams row-level `INSERT`, `UPDATE`, `DELETE` events to Kafka as structured JSON/Avro change envelopes containing `before` and `after` row states.


---

## Category 5: Schema Registry, Partitioning & Production Operations

### Q14: What is Confluent Schema Registry, and how do Avro/Protobuf compatibility modes protect downstream consumers?
**Answer:**  
Schema Registry stores versioned schemas (`subject-value`) outside Kafka messages, embedding only a 4-byte Schema ID inside each message header. Compatibility modes (`BACKWARD`, `FORWARD`, `FULL`, `TRANSITIVE`) reject breaking schema changes at producer publish time—for example, `BACKWARD` allows adding optional fields with defaults so new consumers can still read older messages.

---

### Q15: How do you choose the Partition Key for a Kafka topic? What happens if you pick a skewed key?
**Answer:**  
Pick a high-cardinality key that groups events requiring strict ordering (e.g., `order_id` or `account_id`). Picking a low-cardinality or hot key (like `country="IN"` or `merchant_id="NULL"`) sends 80% of traffic to one partition, saturating a single broker and leaving other consumer instances idle.

---

### Q16: Can you decrease the number of partitions in a live Kafka topic? Why or why not?
**Answer:**  
You can **increase** partitions (`kafka-topics --alter`), but you **cannot decrease** them in place without recreating the topic. Increasing partitions also breaks key-based hash routing continuity (`hash(key) % N`) for existing keys unless consumers handle cross-partition history.

---

### Q17: What is Log Compaction (`cleanup.policy=compact`) vs. Time-Based Retention (`delete`)?
**Answer:**  
- **`delete` (default):** Deletes entire old segments once `retention.ms` or `retention.bytes` is exceeded (used for event/clickstream logs).
- **`compact`:** Retains at least the **latest value per record key** forever, removing superseded older versions and `null`-payload tombstones after `delete.retention.ms` (ideal for CDC state snapshots and KTables).

---

### Q18: Explain `auto.offset.reset = earliest` vs. `latest`, and when each applies.
**Answer:**  
`auto.offset.reset` applies **only when a consumer group has no committed offset** (a brand-new group or expired `offsets.retention.minutes`). `earliest` reads from the oldest available offset; `latest` skips history and reads only new arriving messages.

---

### Q19: What causes a consumer group rebalance storm (`max.poll.interval.ms` exceeded), and how do you fix it?
**Answer:**  
If processing a batch takes longer than `max.poll.interval.ms` (default 5 min), the broker assumes the consumer froze, evicts it, and triggers a rebalance—causing the next consumer to pick up the same heavy batch and crash too. Fix by lowering `max.poll.records`, optimizing batch writes, moving slow work to async/DLQ, or raising `max.poll.interval.ms`.

---

### Q20: Explain the Outbox Pattern for dual-write consistency between PostgreSQL and Kafka.
**Answer:**  
Writing to Postgres and publishing to Kafka separately isn't atomic—one can succeed while the other fails. With the **Transactional Outbox Pattern**, the app writes business state AND an event row to an `outbox` table inside the **same DB transaction**, and Debezium/Kafka Connect reliably tails the `outbox` via WAL into Kafka.

---

### Q21: How does Zero-Copy (`sendfile`) contribute to Kafka's extreme throughput?
**Answer:**  
Traditional apps copy disk blocks -> OS Page Cache -> JVM user space -> socket buffer -> NIC. Kafka uses the OS `sendfile()` syscall to transfer bytes directly from the OS Page Cache to the NIC socket buffer without copying into JVM heap or triggering Java GC.

---

### Q22: What is the difference between `unclean.leader.election.enable=false` vs `true`?
**Answer:**  
- `false` (recommended for financial/DE data): If all ISR brokers die, the partition stays offline until an ISR returns—preserving zero data loss.
- `true`: Allows an out-of-sync replica to become leader, favoring availability at the cost of silently losing uncommitted/unreplicated tail messages.

---

### Q23: How does Kafka Connect scale horizontally across workers and connectors?
**Answer:**  
Kafka Connect runs in Distributed Mode using internal topics (`connect-configs`, `connect-offsets`, `connect-status`). Setting `tasks.max` splits work (e.g., partitioning JDBC table pulls or reading multiple Kafka partitions) across multiple Connect worker pods automatically.

---

### Q24: What are Single Message Transforms (SMTs) in Kafka Connect, and when should you avoid them?
**Answer:**  
SMTs perform lightweight per-record operations inside Connect (masking PII, renaming fields, routing topics, extracting `after` from Debezium envelopes). Avoid heavy joins, stateful aggregations, or external API calls in SMTs—offload those to Spark Structured Streaming or Flink.

---

### Q25: How do you handle poison-pill deserialization errors in a Python Kafka consumer?
**Answer:**  
Wrap deserialization separately from business logic, catch `SerializationError` / `UnicodeDecodeError`, preserve the raw `bytes` payload + partition + offset + error headers, publish to `<topic>.dlq`, and commit the offset so one corrupt byte sequence never stalls the entire partition.

---

### Q26: Explain `replication.factor=3` with `min.insync.replicas=2` and `acks=all`.
**Answer:**  
This classic production trio tolerates **1 broker failure** (whether planned rolling restart or hardware crash) with **zero downtime and zero data loss**: writes succeed as long as 2 of 3 replicas ack, while protecting against split-brain writes if 2 brokers go down simultaneously.

---

### Q27: What is `isolation.level=read_committed` vs `read_uncommitted`?
**Answer:**  
With transactional producers (`EOS`), aborted or in-flight transaction messages sit in the partition log before a commit/abort marker. `read_committed` ensures consumers never expose aborted/uncommitted records, halting at the Last Stable Offset (LSO) until open transactions resolve.

---

### Q28: How do you replay the last 24 hours of events in Kafka without changing consumer code?
**Answer:**  
Stop the consumer group and run `kafka-consumer-groups.sh --reset-offsets --to-datetime <ISO-timestamp> --execute` (which maps timestamps via `.timeindex` files to exact partition offsets), then restart consumers.

---

### Q29: Compare Kafka Streams / Flink vs. Spark Structured Streaming for consuming Kafka.
**Answer:**  
- **Kafka Streams:** Lightweight Java library embedded directly in microservices—great for sub-10ms per-event stateful apps.
- **Apache Flink:** True event-at-a-time distributed streaming with millisecond latency and rich CEP/state backends.
- **Spark Structured Streaming:** Micro-batch (and Continuous) processing deeply integrated with Delta Lake/Iceberg Lakehouse batch+streaming unification.

---

### Q30: How do you benchmark and capacity-plan a Kafka cluster for a new ingestion pipeline?
**Answer:**  
Estimate peak ingestion MB/s × (`replication.factor` for inter-broker replication + consumer fan-out factor), size partition counts from single-partition consumer throughput limits, verify disk capacity for `retention.ms` × daily volume × `replication.factor`, and load-test with `kafka-producer-perf-test.sh`.
