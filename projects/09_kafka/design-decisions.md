# 🧠 Architectural Design Decisions & Technical Tradeoffs

> **Data Engineering Diaries** | Project 09: Apache Kafka for Real-Time Data Engineering  
> Author: Sathiya Murthy

---

## 1. Streaming Infrastructure Choice: Kafka vs. Alternatives

### Decision Matrix

| Metric / Requirement | Apache Kafka | RabbitMQ | AWS Kinesis Data Streams | Decision Rationale |
|---|---|---|---|---|
| **Primary Architecture** | Distributed Append-Only Commit Log | Smart Broker / Dumb Consumer Queue | Managed Sharded Stream | **Kafka Chosen**: Permanent log retention enables replayability, essential for data warehousing & ML feature stores. |
| **Throughput** | 1,000,000+ msg/sec per cluster | 50,000 msg/sec | 1,000 msg/sec per shard | **Kafka Chosen**: Massive scale batching & zero-copy network transmission (`sendfile`). |
| **Event Replay** | Supported (reset offsets to any timestamp) | Not Supported (messages deleted on ACK) | Supported (up to 365 days) | **Kafka Chosen**: Critical for reprocessing events after downstream bug fixes. |
| **Ordering Guarantees** | Strict per-partition ordering | Per-queue ordering (single consumer) | Per-shard ordering | **Kafka Chosen**: Key-based partitioning guarantees ordering per user/order ID. |
| **Infrastructure Overhead** | High (Requires KRaft / ZooKeeper) | Low | Zero (AWS Managed Service) | **Kafka Chosen**: Docker Compose / Kubernetes Helm charts automate deployment. |

---

## 2. Producer Guarantee Selection: `acks=all` + Idempotence vs. `acks=1`

### Decision: Enterprise Default = `acks=all` + `enable.idempotence=true`

- **Tradeoff Analysis**:
  - `acks=1` offers ~15% faster latency because only the partition leader writes to disk before acknowledging. However, if the leader crashes before replicating to followers, **data loss occurs**.
  - `acks=all` (with `min.insync.replicas=2`) guarantees that at least 2 brokers have written the message to disk before responding to the producer.
  - Enabling `enable.idempotence=true` assigns a 64-bit Producer ID (PID) and sequence number to every message batch. If network retries occur, the broker deduplicates records automatically.

---

## 3. Compression Codec Benchmark & Tradeoffs

| Codec | Compression Ratio | CPU Overhead (Producer) | CPU Overhead (Consumer) | Throughput (MB/s) | Recommendation |
|---|---|---|---|---|---|
| **None** | 1.0x | 0% | 0% | 120 MB/s | Development / Testing |
| **GZIP** | 4.2x | High (CPU bound) | Medium | 45 MB/s | Cold Archival Storage |
| **Snappy** | 2.5x | Low | Low | 350 MB/s | Legacy Microservices |
| **LZ4** | **3.1x** | **Very Low** | **Very Low** | **480 MB/s** | **Production Standard (Chosen)** |
| **ZSTD** | 3.8x | Medium | Low | 310 MB/s | High-Volume Financial Logs |

---

## 4. Consumer Offset Commit Strategy

### Decision: `enable.auto.commit=False` with Manual Batch Commits

- **Why Auto-Commit (`enable.auto.commit=True`) Fails in Data Engineering**:
  Auto-commit periodically commits offsets every $N$ seconds regardless of whether message processing succeeded in the application code. If a stream processor crashes midway through processing a batch, committed offsets advance, resulting in **silent data loss**.

- **Manual Batch Commit Strategy**:
  ```python
  # Process N records first, then commit
  if uncommitted_records >= 100:
      consumer.commit(asynchronous=False)
  ```
  Guarantees **At-Least-Once Delivery**. Any reprocessing on failure is safely handled via downstream idempotent upserts or deduplication keys.

---

## 5. Serialization Format Choice: Avro + Schema Registry vs. Raw JSON

- **Raw JSON Downsides**:
  1. High payload size: Key strings (`"event_timestamp"`, `"shipping_fee"`) repeated in every message.
  2. No schema governance: A breaking field rename in upstream microservice crashes all downstream ETL jobs.

- **Avro + Schema Registry Solution**:
  1. Messages serialized into compact binary without repeating field names.
  2. A 4-byte Schema ID header points to the exact schema version in Schema Registry.
  3. Strict **BACKWARD compatibility rules** enforce that producers cannot drop mandatory fields without default values.
