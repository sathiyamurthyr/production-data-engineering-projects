# Project 05 Design Decisions: PySpark Core & Distributed DataFrames

This document outlines key engineering decisions, API choices, trade-offs, and architectural compromises made in this project.

---

## 1. API Selection: PySpark DataFrames over RDDs & Datasets

### Decision
We use PySpark **DataFrames** (built on top of catalyst expressions) exclusively across all modules.

### Alternatives Considered
1. **RDD (Resilient Distributed Dataset)**:
   - *Pros*: Low-level record control, custom object manipulation.
   - *Cons*: Bypasses Catalyst Query Optimizer and Tungsten code generation. High GC overhead in JVM and slow Python serialization.
2. **Datasets (Scala / Java typed API)**:
   - *Pros*: Compile-time type safety.
   - *Cons*: Not natively available in Python (PySpark DataFrames *are* PySpark Datasets under the hood, typed to `Row`).

### Rationale
DataFrames provide structured column awareness, enabling predicate pushdown, vectorization, memory-efficient columnar storage, and seamless integration with SQL.

---

## 2. Storage Format Selection: Parquet & Delta Lake over CSV / JSON

### Decision
Output sinks strictly write to **Parquet** (with Snappy compression) or **Delta Lake**. CSV and JSON are used strictly as raw ingestion landing formats.

### Comparison Table

| Feature | CSV | JSON | Parquet | Delta Lake |
|---|---|---|---|---|
| **Storage Layout** | Row-oriented | Row-oriented | Columnar | Columnar (Parquet + Log) |
| **Compression** | Poor | Poor | Exceptional (Snappy/ZSTD) | Exceptional (Snappy/ZSTD) |
| **Schema Storage** | None (Header strings) | Implicit / Nested | Native (File Footer Metadata) | Native (Transaction Log JSON) |
| **Predicate Pushdown** | No | No | Yes (Row Groups min/max) | Yes (File Level + Row Group) |
| **ACID Transactions** | No | No | No | Yes (ACID Log) |
| **Schema Evolution** | No | No | Partial | Full (`mergeSchema`) |

---

## 3. Join Optimizations: Broadcast Hash Join vs Sort-Merge Join

### Decision
Small lookup datasets (such as `product_catalog.csv` < 10MB) are joined using explicit **Broadcast Hash Join** hints (`F.broadcast()`).

### Rationale
- **Sort-Merge Join (SMJ)** requires shuffling both large and small DataFrames across the network, followed by sorting by key.
- **Broadcast Hash Join (BHJ)** replicates the small lookup table to executor memory once. Large DataFrame partitions remain in-place, eliminating 100% of network shuffle overhead for the target join.

---

## 4. UDF Choice: Vectorized Pandas UDFs (PyArrow) over Python UDFs

### Decision
When PySpark native expressions cannot handle custom logic, we implement **Pandas UDFs** (`@pandas_udf`) built on Apache Arrow.

### Rationale
- **Standard Python UDFs**: Require row-by-row serialization from JVM to Python worker processes via socket IPC. This causes massive CPU bottlenecks and prevents Catalyst optimizations.
- **Pandas UDFs**: Leverage Apache Arrow's shared in-memory columnar format, transferring batches of data with zero-copy deserialization. Arrow passes arrays directly to NumPy/Pandas C-extensions, executing up to 100x faster than standard Python UDFs.

---

## 5. Schema Enforcement: Explicit StructType vs inferSchema

### Decision
All file readers enforce strict `StructType` schemas defined in Python.

### Rationale
`inferSchema=True` forces Spark to scan the entire input dataset twice (once for type inference, once for reading). On multi-terabyte datasets, this doubles total I/O execution time. Explicit schemas eliminate this tax and prevent unexpected type casting bugs (e.g. converting numeric IDs with leading zeros into integers).
