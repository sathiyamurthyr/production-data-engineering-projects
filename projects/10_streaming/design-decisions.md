# Technical Design Decisions & Tradeoffs: PySpark Structured Streaming

> **Data Engineering Diaries** | Architecture Rationale & Tradeoff Analysis

---

## 1. Engine Choice: Structured Streaming vs Flink vs Spark DStreams

### Tradeoff Analysis
| Metric / Feature | PySpark Structured Streaming | Apache Flink | Spark DStreams (Legacy) |
|---|---|---|---|
| **Processing Paradigm** | Micro-batch (low latency 100ms-1s) | Native Event-driven (sub-10ms) | Micro-batch (Discretized Streams) |
| **API Integration** | Unified DataFrame/SQL API with Batch | DataStream / Table API | RDD-based API |
| **Delta Lake Integration** | Native first-class support | Connector support required | Primitive / Unsupported |
| **Operational Complexity** | Low (managed Spark cluster/Databricks) | Medium-High (Flink JobManager/TaskManagers) | Deprecated |
| **State Management** | Native RocksDB StateStore | RocksDB State Backend | In-memory checkpointing |

### Decision Rationale
We chose **PySpark Structured Streaming** because:
1. It shares the exact same DataFrame/SQL API as batch processing pipelines, drastically reducing code duplication and developer learning curve.
2. Most enterprise lakehouse workloads operate comfortably within 500ms - 5s latency SLAs. Flink is reserved for sub-50ms event-driven real-time alerting.
3. Native integration with Delta Lake guarantees ACID transactions and exact-once writes out-of-the-box.

---

## 2. Trigger Model: Micro-Batch vs Continuous Processing

### Tradeoff Analysis
- **Micro-Batch (`trigger(processingTime="10 seconds")`)**:
  - *Pros*: Excellent throughput, high compression efficiency, supports all stateful operators (joins, windows, deduplication), resilient.
  - *Cons*: Latency bound to micro-batch interval (typically 100ms - 10s).
- **Continuous Processing (`trigger(continuous="1 second")`)**:
  - *Pros*: Sub-millisecond latency (event-by-event processing).
  - *Cons*: Experimental, limited operator support (stateless only), higher CPU overhead due to long-running worker tasks.

### Decision Rationale
Default to **Micro-Batch mode** with a 10-second processing time trigger. Micro-batch yields maximum throughput per dollar and supports complex stateful windowed aggregations.

---

## 3. State Store Provider: RocksDB vs HDFSBacked

### Tradeoff Analysis
- **HDFSBackedStateStore (Default)**:
  - Stores state directly on JVM heap memory.
  - *Failure Point*: When maintaining state for millions of unique keys over long windows, heap memory spikes cause severe Stop-The-World GC pauses and Driver/Executor OOM crashes.
- **RocksDBStateStoreProvider**:
  - Stores state off-heap in native memory and local SSD storage, asynchronously writing state checkpoints to cloud storage.
  - *Pros*: Handles state sizing up to billions of keys without JVM GC pressure.

### Decision Rationale
Configure `RocksDBStateStoreProvider` for all production stateful streaming jobs.

---

## 4. Delta Lake vs Plain Parquet Sinks

### Tradeoff Analysis
- **Plain Parquet Sink**:
  - Creates thousands of small files ("Small File Problem").
  - Cannot handle updates/upserts (Append mode only).
  - Uncommitted files visible to readers during executor failure.
- **Delta Lake Sink**:
  - ACID transaction log guarantees atomic micro-batch commits.
  - Supports `foreachBatch` upserts (MERGE).
  - Automatic small file compaction via `OPTIMIZE` and auto-compact configs.

### Decision Rationale
Use **Delta Lake** as the default storage layer for all streaming sinks.
