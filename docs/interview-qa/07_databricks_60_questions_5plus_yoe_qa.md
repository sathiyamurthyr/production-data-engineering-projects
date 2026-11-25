# 07. Databricks Interview Questions & Answers (5+ Years Experience — 60 Questions + Follow-Ups)

Production-focused, architecture, optimization, and troubleshooting Q&As for **Senior Data Engineer**, **Lead Data Engineer**, and **Databricks** interviews.

---

## 1. Databricks Architecture

### Q1. Explain the Databricks architecture in detail.
**Answer:**
- **Control Plane:** Managed by Databricks in its own cloud account; hosts the Web UI, notebooks, Jobs scheduler, cluster manager, Unity Catalog metastore service, and REST APIs.
- **Compute Plane (Data Plane):** Runs inside the **customer's** cloud VPC/VNet (AWS/Azure/GCP) where Spark Driver and Worker nodes execute (or Serverless compute managed in isolated Databricks-managed accounts with private links). Customer data stays in the customer's Data Plane.
- **Workspace:** The logical UI/API environment organizing notebooks, repos, jobs, and compute for a team/environment (`dev`, `prod`).
- **Clusters:** Managed Spark/Photon compute groups (Driver + Workers) spun up via cloud VMs/containers.
- **Unity Catalog:** Centralized 3-tier (`catalog.schema.table`) governance layer handling RBAC, storage credentials, external locations, column masking, row filters, and automated lineage.
- **DBFS:** Legacy Databricks File System abstraction over workspace root S3/ADLS buckets (largely superseded by Unity Catalog **Volumes** and **External Locations** for security).
- **Delta Lake:** Open ACID storage layer over Parquet files using `_delta_log` for transactions, time travel, and data skipping.

---

### Q2. Why does Databricks separate the Control Plane and Data Plane?
**Answer:**
1. **Data Sovereignty & Security:** Raw data and PII never leave the customer's cloud account/VPC or cloud storage (S3/ADLS/GCS).
2. **Managed Operations:** Databricks upgrades UI, scheduler, and orchestration planes seamlessly without customers managing control infrastructure.
3. **Compliance:** Enables PrivateLink/VNet injection, customer-managed KMS keys (CMK), and strict IAM isolation.

---

### Q3. What happens internally when you click "Run" on a notebook?
**Answer:**
1. **Driver Attachment / Creation:** The Control Plane routes the command over secure tunnel/gRPC to the cluster's **Spark Driver** (running a REPL process per notebook/user).
2. **DAG Generation:** Lazy transformations build an unresolved logical plan → Catalyst analyzes catalog metadata (Unity Catalog) → optimizes logical & physical plans → splits stages at shuffles into a **DAG**.
3. **Task Scheduling:** Driver requests/uses executor slots and schedules 1 Task per partition per stage based on data locality.
4. **Executor Communication:** Executors deserialize task closures, read Parquet/Delta partitions from S3/ADLS, execute Photon/JVM bytecode, exchange shuffle blocks if needed, and send status/metrics back to Driver.
5. **Result Collection:** Actions (`display()`, `.show()`, `.collect()`) stream bounded result rows back to the Driver and Control Plane Web UI.

---

### Q4. Explain the lifecycle of a Spark job in Databricks.
**Answer:**
`Notebook/Job Trigger` → `SparkSession submits Logical Plan` → `Catalyst Analysis & Optimization` → `Physical Plan & Stage Split (DAGScheduler)` → `TaskSet sent to TaskScheduler` → `Executors execute Tasks (with AQE runtime re-optimization between stages)` → `Delta commit / sink write` → `Metrics & logs persisted to Driver/Cluster logs & System Tables`.

---

### Q5. What is the difference between Interactive (All-Purpose) Clusters and Job Clusters?
**Answer:**
- **Interactive (All-Purpose) Clusters:** Shared, long-lived clusters for ad-hoc exploration and notebook development; stay running until stopped/auto-terminated; **~2x higher DBU rate**.
- **Job Clusters:** Ephemeral clusters spun up specifically for an automated workflow run and terminated immediately on completion; **~50% cheaper per DBU** and provide clean workload isolation.

---

## 2. Cluster Questions

### Q6. What happens if the Driver node crashes?
**Answer:**
The entire Spark application fails immediately—all in-memory state, cached RDDs/DataFrames, active `SparkContext`, and running notebook variables are lost. Running Jobs restart according to retry policy; Streaming jobs recover from their **checkpoint** directory once a new cluster/driver starts.

---

### Q7. What happens if an Executor crashes?
**Answer:**
The Driver detects the lost heartbeat, marks the executor dead, requests a replacement executor from the cluster manager, and reschedules only the failed/lost tasks (plus any missing shuffle/cached partitions) onto surviving executors using **RDD/stage lineage**. The job succeeds unless task failures exceed `spark.task.maxFailures` (default `4`).

---

### Q8. Explain cluster auto-scaling.
**Answer:**
Databricks monitors pending task queues, shuffle demands, and executor utilization. Under load, it provisions additional worker nodes up to `max_workers`; when workers sit idle and hold no active shuffle/cache state (or via graceful decommission), it scales down toward `min_workers`. **Optimized Autoscaling** scales up aggressively in steps and scales down aggressively on job clusters.

---

### Q9. What is cluster auto-termination?
**Answer:**
Automatically terminates an idle All-Purpose cluster after $N$ minutes of zero active Spark commands/JDBC queries (e.g., `15–30 minutes`), preventing forgotten interactive clusters from burning cloud VM + DBU bills overnight.

---

### Q10. How do cluster policies work?
**Answer:**
Cluster policies are JSON rule templates attached to users/groups that restrict cluster configurations—enforcing allowed DBR LTS versions, Photon toggle, node types, max workers/DBUs, mandatory tags (for FinOps cost allocation), and mandatory auto-termination limits.

---

## 3. Delta Lake

### Q11. Why is Delta Lake better than raw Parquet?
**Answer:**
Raw Parquet lacks multi-file atomicity, concurrency control, and mutation support. Delta Lake adds:
- **ACID transactions** via `_delta_log`
- **Schema enforcement & safe evolution**
- **`UPDATE`, `DELETE`, `MERGE INTO`** support (plus Deletion Vectors)
- **Time Travel & `RESTORE`**
- **Unified batch + streaming** & Change Data Feed (CDF)
- **Data skipping** via file-level min/max stats & Z-Order/Liquid Clustering

---

### Q12. Explain the structure of `_delta_log`.
**Answer:**
`_delta_log/` sits at the root of every Delta table and acts as the single source of truth for table state—storing an ordered, immutable sequence of commit versions (`00000000000000000000.json`, `00000000000000000001.json`, ...) containing `add`, `remove`, `metaData`, `protocol`, and `commitInfo` actions, alongside periodic Parquet checkpoints.

---

### Q13. What files exist inside `_delta_log`?
**Answer:**
1. **JSON commit files (`000000...001.json`):** Incremental transaction logs per version.
2. **Checkpoint Parquet files (`000000...010.checkpoint.parquet`):** Compact snapshots aggregating all active files up to version $N$.
3. **CRC files (`.000000...001.crc`):** Checksums containing table metrics (total size, file count, row count) for fast `COUNT(*)` / integrity verification.
4. **`_last_checkpoint` file:** Small JSON pointer naming the latest valid checkpoint version so readers don't scan the entire `_delta_log` directory.

---

### Q14. Explain the Delta transaction commit process.
**Answer:**
1. Read snapshot at current version $V$.
2. Write new data Parquet files to table storage (uncommitted—invisible to readers).
3. Attempt atomic creation of `V+1.json` via put-if-absent (cloud storage atomic rename/conditional PUT or DynamoDB lock on older S3).
4. If `V+1.json` already exists, check OCC conflict rules; if non-conflicting, retry commit at `V+2.json`.

---

### Q15. What happens if `_delta_log` is deleted?
**Answer:**
- The directory is **no longer readable as a Delta table**.
- **ACID guarantees, schema metadata, partition metadata, and Time Travel are lost**.
- Historical tombstoned Parquet files and active Parquet files sit mixed together on storage—reading raw Parquet directly would resurrect deleted/updated duplicate rows! (Recovery requires restoring `_delta_log` from object-storage versioning/backups.)

---

### Q16. What is a checkpoint in Delta Lake?
**Answer:**
A Parquet snapshot file written inside `_delta_log` containing the reconciled net set of active `add` files, metadata, and protocol actions as of version $V$ (removing files that were added and later removed).

---

### Q17. Why are checkpoint files created?
**Answer:**
Without checkpoints, opening a table with 100,000 commits would require downloading and parsing 100,000 tiny JSON files. Checkpoints bound metadata read time to **1 Parquet checkpoint + at most a few trailing JSON files** (`delta.checkpointInterval`, default `10` commits).

---

### Q18. Difference between JSON commit files and checkpoint files?
**Answer:**
- **JSON commit files:** Record the **delta/actions of a single transaction** (`add`/`remove` for commit $V$).
- **Checkpoint files:** Store the **cumulative active table state** at version $V$ in compressed columnar Parquet format for fast metadata skipping.

---

### Q19. Explain Optimistic Concurrency Control (OCC).
**Answer:**
Readers never take locks (snapshot isolation). Writers work optimistically without locking the table during compute, then validate at commit time whether any concurrent commit since their read version $V$ touched conflicting files or violated isolation invariants—retrying automatically if safe, or failing fast with a conflict exception.

---

### Q20. What happens if two users update the same Delta table simultaneously?
**Answer:**
- **Both append (`INSERT`) or touch disjoint partitions:** Both succeed automatically via OCC retry.
- **Both `UPDATE`/`DELETE`/`MERGE` overlapping files/partitions:** The first writer commits version $V+1$; the second writer detects a file conflict (`ConcurrentAppendException` / `ConcurrentDeleteReadException`) and aborts cleanly without corrupting the table. (Enabling **Row-Level Concurrency** with Deletion Vectors reduces file-level conflicts when different rows in the same file are modified.)

---

## 4. Delta Merge

### Q21. Explain how `MERGE` works internally.
**Answer:**
1. **Scan & Join (Phase 1):** Reads target files matching join predicates (using data skipping/partition pruning) and joins source with target to identify matched (`UPDATE`/`DELETE`) and unmatched (`INSERT`) rows.
2. **Rewrite / Deletion Vectors (Phase 2):** Without Deletion Vectors, any target Parquet file with $\ge 1$ matched row is read in full, modified, and written out as a **brand-new Parquet file**, plus new files for inserted rows. With Deletion Vectors, matched old rows are flagged in a tiny `.bin` bitmap and updated rows are appended as new files.
3. **Commit:** Atomically commits `add` and `remove` actions to `_delta_log`.

---

### Q22. Why is `MERGE` slower than `APPEND`?
**Answer:**
`APPEND` simply writes new Parquet files and commits `add` actions without touching existing data. `MERGE` must: (1) scan and join target files against source, (2) shuffle/sort-merge or broadcast-join keys, and (3) copy-on-write rewrite entire untouched rows inside affected target Parquet files (unless Deletion Vectors are enabled).

---

### Q23. How do you optimize `MERGE` performance?
**Answer:**
1. **Add Partition Filters to the `ON` Clause:** e.g., `t.event_date = s.event_date AND t.id = s.id` so Delta prunes 99% of target partitions!
2. **Enable Deletion Vectors & Photon** to avoid full Parquet file rewrites.
3. **Deduplicate & Filter Source First** to shrink shuffle volume and prevent multi-match errors.
4. **Z-Order / Liquid Cluster** on the merge join key (`id`) so file min/max stats skip irrelevant files.
5. **Use `WHEN MATCHED AND <change_condition>`** so identical unchanged rows aren't rewritten!

---

### Q24. What is file rewriting during `MERGE`?
**Answer:**
Parquet files are **immutable**—you cannot modify a single row in place. Under Copy-on-Write, changing 1 row inside a 256 MB Parquet file forces Spark to rewrite all remaining 999,999 unchanged rows into a new 256 MB file and mark the old file `remove` (write amplification).

---

### Q25. Explain `MERGE` conflicts.
**Answer:**
1. **Intra-source ambiguity:** Multiple source rows match 1 target row → `UnsupportedOperationException: Cannot perform Merge as multiple source rows matched...` (fix by deduplicating source before merge).
2. **Concurrent write conflicts:** Another job runs `UPDATE`/`DELETE`/`OPTIMIZE` on the same files while `MERGE` executes → `ConcurrentDeleteReadException` / `ConcurrentAppendException` (fix via partition isolation `ON t.dt = ...`, row-level concurrency, or job serialization).

---

## 5. Performance Optimization

### Q26. Your Databricks job increased from 20 minutes to 3 hours. How do you troubleshoot?
**Answer:**
Follow a structured bottleneck checklist:
1. **Cluster & Queue Check:** Did cluster boot/spot reclamation take longer, or did autoscaling fail to add nodes?
2. **Spark UI → Jobs/Stages:** Identify which single stage accounts for 80%+ of runtime.
3. **Tasks Tab (Skew / Stragglers):** Compare **Median vs. Max task duration** and Shuffle Read Size. One 2.5-hour task means **Data Skew** or `NULL` key explosion.
4. **Shuffle & Spill:** Check `Shuffle Read/Write` and **Disk Spill** (memory shortage causing excessive serialization/disk I/O).
5. **Executors Tab (GC):** If `GC Time > 10%` of task time, executors are thrashing heap.
6. **Storage / Small Files:** Check input file count (`_delta_log` metrics); millions of tiny S3/ADLS files cause slow listing and huge task counts (`OPTIMIZE` needed).

---

### Q27. Explain Adaptive Query Execution (AQE).
**Answer:**
Enabled by default in Spark 3.x (`spark.sql.adaptive.enabled=true`), AQE collects runtime statistics at shuffle boundaries and dynamically re-optimizes remaining stages:
1. **Coalesces small shuffle partitions** (`advisoryPartitionSizeInBytes`) to eliminate tiny tasks.
2. **Converts Sort-Merge Join to Broadcast Join** if runtime filtered size drops below threshold.
3. **Splits skewed shuffle partitions** (`skewJoin.enabled=true`) across multiple tasks.

---

### Q28. What is partition pruning?
**Answer:**
When a table is physically partitioned (`PARTITION BY (event_date)`), queries filtering on `WHERE event_date = '2026-11-25'` skip reading all other date directories entirely at planning/execution time. (**Dynamic Partition Pruning** even prunes fact partitions using dimension filters at runtime.)

---

### Q29. What is predicate pushdown?
**Answer:**
Pushing filter conditions (`WHERE amount > 100`) down to the storage reader (Parquet/Delta/JDBC) so row groups whose min/max stats don't overlap `> 100` are never read into memory—cutting I/O and decompression dramatically.

---

### Q30. Difference between Partition Pruning and Z-Ordering.
**Answer:**
- **Partition Pruning:** Coarse-grained **directory-level** skipping for **low-cardinality** columns (`date`, `region`).
- **Z-Ordering:** Fine-grained **file-level** multi-dimensional spatial clustering (Morton curves) within partitions for **high-cardinality** columns (`customer_id`, `order_id`), relying on Delta's per-file min/max column stats.

---

### Q31. What causes shuffle?
**Answer:**
Wide transformations that require redistributing rows across partitions over the network: `groupBy`, `join` (except Broadcast), `distinct`, `orderBy` / `sort`, `repartition`, and window functions (`OVER (PARTITION BY ...)`).

---

### Q32. What causes data skew?
**Answer:**
Uneven key distribution in `join` or `groupBy`—such as hot keys (`country='US'`, `merchant_id='amazon'`), millions of `NULL` / `-1` default keys, or heavily skewed input partitions—forcing one task to process 90% of the data.

---

### Q33. How do you fix data skew?
**Answer:**
1. Enable **AQE Skew Join** (`spark.sql.adaptive.skewJoin.enabled=true`).
2. Use **Broadcast Join** for smaller dimension tables.
3. **Filter/isolate `NULL` or dummy keys** before joining.
4. Apply **Key Salting** for heavy fact-to-fact joins or skewed `groupBy` aggregations.

---

### Q34. Explain salting.
**Answer:**
Append a random integer `0..K-1` to the skewed join key of the large table (`concat(key, '_', floor(rand()*16))`) and explode an array `[0..15]` on the matching key of the smaller table. This splits 1 giant overloaded key bucket into $K$ parallel join tasks.

---

### Q35. Broadcast join vs Shuffle join.
**Answer:**
- **Broadcast Hash Join:** Copies the small table (< 10–100 MB) to every executor once and joins locally with **zero shuffle of the large table**—fastest whenever one side fits comfortably in executor memory.
- **Sort-Merge / Shuffle Hash Join:** Repartitions **both** tables by join key across the network, sorts/hashes them, and joins matching partitions—necessary when both tables are large.

---

## 6. Delta Optimization

### Q36. What does `OPTIMIZE` do?
**Answer:**
`OPTIMIZE table_name [ZORDER BY (col)]` compacts many small Parquet files into target ~128 MB–1 GB files (bin-packing) and optionally co-locates data along Z-Order/Liquid Clustering columns, committing new `add` and old `remove` actions atomically without blocking concurrent readers.

---

### Q37. What does `VACUUM` do?
**Answer:**
`VACUUM table_name [RETAIN N HOURS]` physically deletes tombstoned Parquet files from cloud storage that are no longer referenced by the current version and are older than the retention threshold (default **7 days / 168 hours**).

---

### Q38. Difference between `OPTIMIZE` and `VACUUM`.
**Answer:**
- **`OPTIMIZE`:** Merges small active files into larger files to **speed up reads** (temporarily *increases* storage because old files are kept for Time Travel).
- **`VACUUM`:** Physically deletes unreferenced old files past retention to **reclaim storage costs** (cannot restore Time Travel versions older than vacuumed threshold).

---

### Q39. What is Auto Optimize?
**Answer:**
Databricks' automated write-time optimization combining two properties: **Optimized Writes** (`delta.autoOptimize.optimizeWrite`, which adaptively coalesces/rebalances partitions in memory *before* writing to S3/ADLS) and **Auto Compaction**.

---

### Q40. What is Auto Compaction?
**Answer:**
(`delta.autoOptimize.autoCompact`) Automatically runs a lightweight mini-`OPTIMIZE` immediately after a Delta write/streaming commit finishes if many small files exist in a partition, targeting ~128 MB file sizes without needing separate `OPTIMIZE` schedules for every streaming table.

---

## 7. Streaming

### Q41. Explain Auto Loader.
**Answer:**
Auto Loader (`cloudFiles`) is Databricks' incremental cloud-storage ingestion source. It tracks newly arrived files via **File Notification mode** (SQS/Event Grid/PubSub) or scalable **RocksDB directory-listing state**, supports billions of files with minimal cost, infers/evolves schemas automatically, and captures bad fields in `_rescued_data`.

---

### Q42. Difference between Auto Loader and standard Structured Streaming file reader.
**Answer:**
Standard `spark.readStream.parquet/json` lists the **entire** cloud directory tree on every micro-batch trigger (O(total files), slow and costly on millions of files) and offers no built-in `_rescued_data` or cloud event notifications. Auto Loader processes files incrementally in $O(\text{new files})$ using RocksDB state + event notifications and handles schema evolution natively.

---

### Q43. Explain checkpointing.
**Answer:**
Structured Streaming persists `offsets/` (exact input ranges read per batch), `commits/` (completed batch IDs), `state/` (RocksDB/state snapshots for stateful ops), and `metadata` to durable cloud storage so restarted jobs resume cleanly from the exact failure point.

---

### Q44. What happens if the checkpoint directory is deleted?
**Answer:**
All offset tracking and stateful operator memory (dedup keys, stream-stream join buffers, running aggregates) are **permanently lost**. Restarting the stream either re-reads all source data from `earliest` (risking massive duplicates unless downstream is idempotent) or skips missed gaps if set to `latest`.

---

### Q45. Explain exactly-once processing.
**Answer:**
Guaranteed end-to-end when 3 conditions hold:
1. **Replayable source** (Kafka offsets, Auto Loader file log)
2. **Durable checkpointing** (WAL tracking offsets + state)
3. **Idempotent / transactional sink** (Delta Lake atomic commits / `MERGE` with `txnAppId`/`txnVersion`) so re-executing an interrupted micro-batch produces identical target state.

---

## 8. Unity Catalog

### Q46. What is Unity Catalog?
**Answer:**
Databricks' unified governance solution across all workspaces in an account—providing centralized access control (tables, volumes, models, functions), automated column-level lineage, audit logging, data discovery, and secure Delta Sharing.

---

### Q47. Explain Catalog → Schema → Table hierarchy.
**Answer:**
A 3-level ANSI SQL namespace (`catalog.schema.table`, e.g., `prod_lakehouse.silver_payments.transactions`):
- **Catalog:** Top-level isolation boundary (by environment `dev`/`prod` or business unit).
- **Schema (Database):** Logical grouping of tables, views, volumes, and functions (`bronze`, `silver`, `gold`).
- **Table / View / Volume:** Concrete managed/external Delta tables, views, or unstructured file Volumes.

---

### Q48. Difference between Hive Metastore and Unity Catalog.
**Answer:**
- **Hive Metastore (HMS):** Workspace-scoped legacy metastore; lacks fine-grained row/column security, cross-workspace governance, automated column-level lineage, and unified model/file governance; relies on instance profiles/DBFS mounts.
- **Unity Catalog:** Account-level central metastore using Storage Credentials + External Locations, standard SQL `GRANT`/`REVOKE`, dynamic row filters & column masks, automated lineage, and system tables.

---

### Q49. Explain row-level security.
**Answer:**
Attach a SQL UDF row filter to a table (`ALTER TABLE orders SET ROW FILTER region_filter ON (region)`). Inside the UDF, `IS_ACCOUNT_GROUP_MEMBER()` checks the querying user's group and returns `TRUE` only for authorized rows—enforced transparently on every query without changing user SQL.

---

### Q50. Explain column masking.
**Answer:**
Attach a SQL masking function to sensitive columns (`ALTER TABLE users ALTER COLUMN ssn SET MASK mask_ssn`). Users in authorized groups (`pii_admins`) see the real value; everyone else sees masked output (`XXX-XX-1234`) dynamically at query runtime.

---

## 9. Production Scenarios

### Q51. Daily job processes duplicate records. How would you debug?
**Answer:**
1. Check Delta History (`DESCRIBE HISTORY tbl`) to see if the job ran twice or retried mid-append.
2. Verify ingestion mode: did someone use `.mode("append")` instead of `MERGE INTO` or `replaceWhere`?
3. Inspect upstream CDC/API source for duplicate keys before merge, and verify `ROW_NUMBER()` deduplication in Silver.
4. For streaming `foreachBatch()`, verify idempotent write logic (`MERGE` or `txnVersion`).

---

### Q52. Schema changed in the source system. What would you do?
**Answer:**
- **Additive nullable column:** Enable `mergeSchema` / Auto Loader `addNewColumns` in Bronze/Silver safely after checking downstream Gold/BI compatibility.
- **Type change / renamed / dropped column:** Fail fast in Bronze/Silver quarantine (`_rescued_data`), coordinate with upstream producer via Data Contracts, backfill or migrate via explicit `CAST`/view alias so downstream consumers don't break.

---

### Q53. Delta table contains 5 million small files. How would you fix it?
**Answer:**
1. Run `OPTIMIZE tbl` in manageable partition chunks (`WHERE dt BETWEEN ...`) on a memory/compute-optimized cluster (avoid hitting driver memory limits on a single giant `OPTIMIZE` across all history).
2. Enable `autoOptimize.optimizeWrite` and `autoCompact` (or widen streaming trigger intervals) to stop creating small files going forward.
3. Re-evaluate over-partitioning (`PARTITION BY` high-cardinality columns)—migrate to **Liquid Clustering (`CLUSTER BY`)**.
4. Schedule `VACUUM` after retention window to clean up the 5M tombstoned files.

---

### Q54. Streaming job suddenly stopped. How do you investigate?
**Answer:**
1. Inspect the exception stack trace in the Driver logs / Job Run UI (`OutOfMemoryError`, `FileNotFoundException` from aggressive `VACUUM`, Kafka `OffsetOutOfRange` / `ConcurrentDeleteReadException`, or schema mismatch).
2. Check last committed batch in `/checkpoint/commits/` vs `/offsets/`.
3. Fix the root cause (e.g., cap `maxOffsetsPerTrigger`, switch to RocksDB state store, fix schema handling) and restart cleanly from the same checkpoint.

---

### Q55. Delta table is corrupted. What recovery options do you have?
**Answer:**
1. **Bad ETL write / accidental `DELETE`/`UPDATE`:** Use Delta Time Travel (`RESTORE TABLE tbl TO VERSION AS OF <good_ver>`).
2. **Accidental `DROP TABLE` (Managed/External):** Run `UNDROP TABLE` (Unity Catalog retains dropped managed tables for 7 days) or recreate External table pointing to the intact S3/ADLS Delta path!
3. **Missing Parquet files after aggressive `VACUUM` or corrupted `_delta_log`:** Restore missing objects/log versions from S3/ADLS Versioning / Cross-Region Replication backups or `DEEP CLONE` DR replica.

---

## 10. Advanced Architecture

### Q56. Design a Medallion Architecture for a payment platform.
**Answer:**
- **Bronze (Raw Immutable):** Auto Loader + Kafka ingest raw JSON/Avro payment & webhook events with `_ingested_at`, `_source_file`, `_rescued_data`; append-only, schema-on-read/evolution enabled.
- **Silver (Cleansed & Conformed):** Deduplicate via `ROW_NUMBER()` over `(txn_id, lsn)`, enforce currency/amount types & DLT/DQ expectations (quarantine invalid rows to DLQ), tokenize/mask PCI/PII (`PAN`, `IFSC`), and `MERGE INTO` SCD2/current tables with CDF enabled.
- **Gold (Business Marts):** Star schema (`fact_settlements`, `dim_merchants`, `dim_customers`) + daily merchant reconciliation & fraud aggregates, Liquid Clustered on `(merchant_id, settlement_date)`.
- **Monitoring:** DLT event logs, `StreamingQueryListener` lag alerts, Data Health checks, and `system.billing.usage` FinOps dashboards.

---

### Q57. How would you design a Databricks platform for 50 TB/day?
**Answer:**
- **Ingestion:** Auto Loader (File Notification mode via SQS/Event Grid) + partitioned Kafka topics; `maxFilesPerTrigger`/`maxOffsetsPerTrigger` backpressure caps.
- **Compute & Engine:** **Photon** enabled on Job Clusters / Serverless Compute with Autoscaling and Spot Instance Pools for non-critical batch workers; disable interactive cluster usage for prod jobs.
- **Storage & Layout:** Delta Lake with **Deletion Vectors + Liquid Clustering** (no over-partitioning), `optimizeWrite`, and scheduled `OPTIMIZE`/`VACUUM` via Predictive Optimization.
- **Query & Optimization:** AQE enabled, Broadcast joins for dimensions, avoid Python UDFs (use SQL/Photon/Arrow).
- **Governance & Observability:** Unity Catalog 3-tier isolation (`prod`/`dev`), RBAC + row/column masks, System Tables for cost/lineage monitoring, and PagerDuty/Slack SLA alerts.

---

### Q58. How do you implement CI/CD in Databricks?
**Answer:**
1. **Source Control:** Databricks Git Folders synced to GitHub/Azure DevOps feature branches.
2. **Infrastructure as Code:** **Terraform** provisions workspaces, Unity Catalog catalogs/external locations, IAM/Service Principals, and cluster policies.
3. **Deployment:** **Databricks Asset Bundles (`databricks.yml`)** define jobs, DLT pipelines, and variables across `dev` → `staging` → `prod`.
4. **Pipeline:** GitHub Actions / Azure DevOps runs `ruff`/`pytest` unit tests (with local Spark fixtures), `databricks bundle validate`, deploys to staging for integration tests, and deploys to prod via Service Principal OAuth/OIDC.

---

### Q59. How do you secure a Databricks environment?
**Answer:**
- **Identity & Auth:** SSO + SCIM provisioning; run production jobs strictly as **Service Principals** (never personal user tokens).
- **Governance:** **Unity Catalog** least-privilege `GRANT`s, Storage Credentials/External Locations (no DBFS root/IAM keys), dynamic row filters & column masks.
- **Secrets:** **Secret Scopes** backed by Azure Key Vault / AWS Secrets Manager.
- **Compute & Network:** **Cluster Policies** restricting nodes/auto-termination; VPC/VNet injection, PrivateLink, IP access lists, and Customer-Managed Encryption Keys (CMK).

---

### Q60. Describe the most difficult Databricks production issue you've solved. *(Interview Framework)*
**Answer (Structured STAR Example):**
- **Situation:** A daily Silver `MERGE` job processing 2B payment events jumped from 25 minutes to 4+ hours and intermittently failed with executor OOMs.
- **Root Cause Analysis:** Spark UI showed 199 tasks finishing in 40s while 1 task stalled for 3.5 hours (`Shuffle Read = 180 GB`). Investigation revealed `merchant_id = 'UNKNOWN'` accounted for 35% of rows (massive key skew), and the `MERGE` omitted a `settlement_date` partition predicate, forcing full-table Parquet file rewrites.
- **Resolution:** (1) Split `merchant_id = 'UNKNOWN'` rows out of the skewed join, (2) added a dynamic `settlement_date` filter derived from source batch min/max dates into the `MERGE ON` clause, (3) enabled **Deletion Vectors** + **Photon**, and (4) enabled AQE skew join.
- **Preventive Measures & Impact:** Added automated stage-skew monitoring alerts and a unit test verifying partition pruning; runtime dropped from **4+ hours to 14 minutes** (~75% DBU cost savings).

---

## Frequently Asked Production Follow-Up Questions

1. **What happens if the Driver runs out of memory?**
   - The Spark application crashes (`java.lang.OutOfMemoryError` on Driver). Common causes: calling `.collect()` / `.toPandas()` on huge DataFrames, broadcasting too many large tables (`spark.sql.autoBroadcastJoinThreshold`), or massive Catalyst/checkpoint metadata. Fix by removing `.collect()`, lowering broadcast thresholds, and sizing driver memory appropriately.

2. **What happens if Executors are idle?**
   - You pay cloud VM + DBU costs for unused compute. Common causes: a single-threaded Python step running on the Driver (e.g., Pandas/API loop), severe data skew (1 straggler task holding the whole cluster), or `coalesce(1)` before a heavy calculation. Fix with autoscaling, removing skew, and parallelizing driver bottlenecks.

3. **Why do you get `OutOfMemoryError` in Spark?**
   - **Executor Heap OOM:** Skewed partition too large for one core, `collect_list()` on giant groups, oversized broadcast table, or excessive `cache()` pressure.
   - **Off-Heap / Container Kill (`Exit code 137`):** PyArrow/Pandas UDFs or RocksDB exceeding `spark.executor.memoryOverhead`.

4. **How do you tune `spark.sql.shuffle.partitions`?**
   - Enable **AQE** (`spark.sql.adaptive.enabled=true`) so Spark auto-tunes post-shuffle partitions dynamically! For static tuning or streaming (where AQE is off), target ~**128 MB per shuffle partition** ($\text{Total Shuffle Bytes} / 128 \text{ MB}$) or 2x–3x total cluster cores.

5. **Why is your `MERGE` operation slow?**
   - Missing partition filter in `ON` clause (scanning entire table), Copy-on-Write rewriting huge files for a few updates (enable Deletion Vectors), unindexed/non-Z-Ordered join keys, or skewed/unfiltered source DataFrames.

6. **What happens when `VACUUM` is run with a very short retention period (e.g., `0 HOURS`)?**
   - It deletes files still needed by active concurrent readers (causing `FileNotFoundException`) and destroys Time Travel history. Keep default 7+ days (`168 HOURS`).

7. **Can `OPTIMIZE` run while users are reading the table?**
   - **Yes.** Delta Lake uses Snapshot Isolation—readers continue reading the pre-`OPTIMIZE` Parquet files safely until `OPTIMIZE` commits, and new queries seamlessly switch to the compacted files.

8. **How does Time Travel work internally?**
   - Delta never overwrites existing Parquet files in place; it records `add`/`remove` actions in `_delta_log`. `VERSION AS OF V` simply reconstructs the active file list at commit $V$ (as long as those files haven't been purged by `VACUUM`).

9. **How do you recover from accidental table deletion?**
   - In Unity Catalog, run `UNDROP TABLE catalog.schema.table` (within 7 days for managed tables). For External tables, `DROP TABLE` removes only metadata—recreate the table pointing to the existing S3/ADLS Delta location.

10. **How do you monitor Databricks jobs in production?**
    - Combine **Jobs Failure/Duration Alerts** (Slack/PagerDuty), **Spark UI / Ganglia / Compute Metrics**, **DLT Event Logs** for DQ expectations, and **Unity Catalog System Tables** (`system.lakeflow.job_run_timeline`, `system.billing.usage`).

11. **How do you optimize cloud storage costs for Delta Lake?**
    - Schedule regular `VACUUM` (so unreferenced Copy-on-Write/compacted files don't accumulate indefinitely), compact small files with `OPTIMIZE`, enable **Deletion Vectors** (less file churn), apply S3/ADLS Intelligent-Tiering/Lifecycle policies on cold archives, and avoid redundant full-table `DEEP CLONE` copies where `SHALLOW CLONE` suffices.
