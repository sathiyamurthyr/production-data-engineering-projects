# Delta Lake Technical Interview Guide

> **Data Engineering Diaries** | Comprehensive Interview Q&A Reference

This guide contains senior data engineering interview questions covering Delta Lake architecture, ACID transaction protocol, data skipping, MERGE operations, and production troubleshooting.

---

## Category 1: Delta Lake Architecture & ACID Protocol

### Q1: How does Delta Lake provide ACID transactions on cloud object storage (S3/ADLS/GCS) which lack native transactional support?
**Answer:**
Delta Lake implements single-table ACID transactions through an immutable, ordered **Transaction Log** (`_delta_log`).
- **Atomicity**: Changes (adding/removing Parquet files) are written as single JSON commit logs (`00000.json`). A commit is atomic; readers see either all commit files or none.
- **Consistency**: Delta enforces schema on write, NOT NULL constraints, and CHECK constraints before committing new files to the log.
- **Isolation**: Delta uses **Optimistic Concurrency Control (OCC)**. Readers perform lock-free snapshot reads by reading log snapshots at a given commit version. Concurrent writers retry automatically if no conflicting file modifications occurred.
- **Durability**: Data files and transaction logs are stored directly on durable cloud object storage. Once written to the log, commits are immutable.

---

### Q2: Explain the structure of `_delta_log` and how Delta prevents reading thousands of JSON files over time.
**Answer:**
Each transaction creates a zero-padded JSON commit file (`00000000000000000001.json`) containing actions: `add` (new Parquet files with min/max statistics), `remove` (tombstoned old files), `metaData`, `protocol`, or `commitInfo`.

To avoid reading millions of small JSON log files as table history grows, Delta creates a **Checkpoint File** (`.checkpoint.parquet`) every 10 commits. A checkpoint aggregates all prior actions into a single Parquet file representing the current active table state. Readers simply load the latest checkpoint and replay only the JSON files written *after* that checkpoint.

---

## Category 2: Performance & Data Skipping

### Q3: How does Z-Ordering differ from standard Hive Partitioning, and when should you use each?
**Answer:**
- **Hive Partitioning**: Subdivides data into physical folder paths (`/year=2026/month=03/`). It is optimal for **low-cardinality** columns (< 10,000 distinct values) used in high-level filter predicates. Over-partitioning high-cardinality data leads to millions of tiny files and slow metadata listing.
- **Z-Ordering (Morton Curves)**: Co-locates multi-dimensional data within physical Parquet files without creating folders. It spatial-clusters data along high-cardinality columns (e.g. `user_id`, `customer_id`). Combined with Delta's file-level min/max column statistics, queries skip reading files whose value ranges don't overlap query filters.

**Rule of Thumb**: Partition by coarse dimensions (e.g., date), Z-Order by high-cardinality search/join keys (e.g., `user_id`).

---

### Q4: What happens under the hood during an `OPTIMIZE` command?
**Answer:**
`OPTIMIZE` performs bin-packing compaction. Spark reads small Parquet files (e.g., 1MB–10MB streaming files), merges them into larger target Parquet files (typically 128MB to 1GB), and writes out the new files. It then commits an `add` action for the new compact files and a `remove` action for the old small files in the transaction log. The old files remain on storage for time travel until `VACUUM` purges them.

---

## Category 3: Data Transformations & CDC

### Q5: What is the cause of `AnalysisException: Cannot perform MERGE because multiple source rows matched...` and how do you resolve it?
**Answer:**
This error occurs when multiple rows in the incoming source DataFrame match a single row in the target table based on the `ON` join condition. Delta cannot decide which source row's attribute values should overwrite the target row.

**Resolution**: Deduplicate the source DataFrame on the join key using `.dropDuplicates([key])` or window functions (`ROW_NUMBER() OVER (PARTITION BY key ORDER BY event_time DESC)`) prior to calling `DeltaTable.merge()`.

---

### Q6: How does Delta Change Data Feed (CDF) track updates and deletes?
**Answer:**
When CDF is enabled (`delta.enableChangeDataFeed = true`), Delta records change events in the log and `_change_data/` directory:
- **Inserts**: Emits rows with `_change_type = 'insert'`.
- **Deletes**: Emits rows with `_change_type = 'delete'`.
- **Updates**: Emits **two** records per updated row:
  1. `_change_type = 'update_preimage'`: Column state *before* update.
  2. `_change_type = 'update_postimage'`: Column state *after* update.

Downstream Structured Streaming jobs or batch consumers query CDF via `.option("readChangeFeed", "true")` to perform incremental updates without rescanning entire tables.

---

## Category 4: Lakehouse Architecture & Maintenance

### Q7: Why is running `VACUUM RETAIN 0 HOURS` dangerous in production?
**Answer:**
Running `VACUUM` with 0 hours retention immediately deletes all tombstoned files marked as removed in previous commits.
1. **Breaks Active Readers**: Any long-running batch query or streaming job reading an older snapshot will immediately fail with `FileNotFoundException`.
2. **Destroys Time Travel**: Users can no longer query previous table versions before the vacuum timestamp.

By default, Delta enforces a 7-day retention safety check to prevent accidental data purging.


---

### Q8: How do you implement SCD Type 2 (Slowly Changing Dimension) using Delta Lake `MERGE INTO`?
**Answer:**
Perform a staged two-part `MERGE` (or unioned `stagedUpdates` pattern):
1. Match active target rows (`is_current = true`) where attributes changed, and update `is_current = false`, `effective_end_date = current_timestamp()`.
2. Insert the new incoming rows with `is_current = true`, `effective_end_date = NULL` (using a `NULL` merge key trick so `WHEN NOT MATCHED` triggers insertion of the new version in a single atomic `MERGE`).

---

### Q9: What is the difference between Schema Enforcement and Schema Evolution (`mergeSchema`) in Delta Lake?
**Answer:**
- **Schema Enforcement (default):** Rejects writes whose columns or data types do not match the target Delta table schema, preventing silent data corruption.
- **Schema Evolution (`option("mergeSchema", "true")`):** Allows safe additive changes (new nullable columns) during append/merge, while still blocking breaking type changes unless `overwriteSchema=true` is explicitly specified.

---

### Q10: How does Delta Time Travel (`VERSION AS OF` / `TIMESTAMP AS OF`) work, and what limits it?
**Answer:**
Because old Parquet files are not physically deleted on update/delete/merge (only marked via `remove` actions in `_delta_log`), Delta reconstructs any historical version by replaying `_delta_log` up to that commit/timestamp. Time travel is bounded by `delta.logRetentionDuration` (default 30 days) and `VACUUM` file retention (default 7 days).

---

### Q11: What is the difference between `RESTORE TABLE` and `CLONE` (Shallow vs. Deep) in Delta Lake?
**Answer:**
- **`RESTORE TABLE`:** Creates a new commit reverting the live table state back to an earlier version or timestamp.
- **`SHALLOW CLONE`:** Copies only `_delta_log` metadata referencing the original Parquet files—instant and zero storage duplication (great for dev/QA testing).
- **`DEEP CLONE`:** Copies both `_delta_log` and physical Parquet files into an independent backup/DR table.

---

### Q12: How does Liquid Clustering improve upon traditional Hive Partitioning + `Z-ORDER`?
**Answer:**
Traditional `PARTITION BY` + `ZORDER` locks you into fixed directory layouts and requires full table rewrites to change clustering keys. **Liquid Clustering (`CLUSTER BY`)** incrementally clusters data using Hilbert curves without rigid subdirectories, lets you alter clustering keys (`ALTER TABLE ... CLUSTER BY`) with zero rewrite of existing data, and adapts automatically to skew.

---

### Q13: How do Deletion Vectors in Delta Lake 2.x/3.x speed up `DELETE`, `UPDATE`, and `MERGE`?
**Answer:**
Without Deletion Vectors, modifying 1 row in a 1 GB Parquet file requires Copy-on-Write (rewriting the entire 1 GB file). With **Deletion Vectors** (Merge-on-Read), Delta writes a tiny bitmap file flagging only the deleted row positions, deferring physical file compaction to async `OPTIMIZE` runs.

---

### Q14: What is Optimistic Concurrency Control (OCC) in Delta Lake, and when can a `ConcurrentModificationException` occur?
**Answer:**
Two concurrent writers read snapshot version $V$, write new Parquet files, and race to commit $V+1$. The second writer checks if the files it read/modified overlap with commits since $V$:
- Independent `APPEND`s or disjoint partition writes succeed automatically.
- Concurrent `UPDATE`/`DELETE`/`MERGE` touching the same files/partitions fails with `ConcurrentAppendException` or `ConcurrentDeleteReadException`.

---

### Q15: How do `replaceWhere` overwrites ensure idempotent partition reprocessing?
**Answer:**
`.option("replaceWhere", "event_date = '2026-11-25'")` atomically replaces only rows matching the predicate inside a single Delta transaction—failing closed if any incoming row violates the predicate—preventing accidental cross-partition overwrites.

---

### Q16: How do Delta `CHECK` constraints and Generated Columns enforce data quality at the storage layer?
**Answer:**
`ALTER TABLE ... ADD CONSTRAINT valid_amount CHECK (amount >= 0)` blocks bad rows at write time before commit. **Generated Columns** (e.g., `event_date DATE GENERATED ALWAYS AS (CAST(event_ts AS DATE))`) derive partition keys automatically from timestamps so queries filtering on `event_ts` also trigger partition pruning.

---

### Q17: Why is `spark.databricks.delta.retentionDurationCheck.enabled = false` discouraged in production?
**Answer:**
Disabling the 7-day safety check lets `VACUUM RETAIN 0 HOURS` delete files referenced by active readers or in-flight streaming checkpoints, risking unrecoverable `FileNotFoundException` errors and loss of rollback capability.

---

### Q18: How do you handle `overwriteSchema` safely when a breaking column type change is required?
**Answer:**
Validate downstream consumers first, take a `DEEP CLONE` or note the pre-change version for rollback, and apply `.option("overwriteSchema", "true")` only in a controlled migration job—never as a default setting in routine ETL pipelines.

---

### Q19: What is Delta UniForm (Universal Format), and why does it matter?
**Answer:**
Delta UniForm generates compatible **Apache Iceberg** and **Apache Hudi** metadata alongside `_delta_log` without duplicating Parquet data files, allowing Snowflake, Trino, BigQuery, or Spark engines to read the same Lakehouse tables natively.

---

### Q20: How do you minimize `_delta_log` metadata overhead for streaming micro-batches committing every few seconds?
**Answer:**
Tune trigger intervals (e.g., `processingTime="1 minute"` or `availableNow=True` when sub-second latency isn't required), enable checkpointing (`delta.checkpointInterval`), and schedule periodic `OPTIMIZE` + `VACUUM` jobs to keep active file counts and log sizes compact.
