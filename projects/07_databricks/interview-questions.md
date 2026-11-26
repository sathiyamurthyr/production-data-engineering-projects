# Databricks Data Engineering Interview Guide

This guide contains 25+ real-world interview questions and in-depth technical answers for Data Engineering candidates targeting Databricks roles.

---

## 1. Platform Architecture & Compute

### Q1: Describe the Databricks architecture. What is the difference between Control Plane and Data Plane?
**Answer:**
Databricks separates control and processing into two distinct planes:
- **Control Plane**: Managed by Databricks in their cloud environment. Includes the Web UI, notebook execution manager, job scheduler, Unity Catalog metastore index, and REST API router.
- **Data Plane**: Located inside the customer's cloud account (AWS, Azure, or GCP). Includes Spark driver and worker nodes, serverless SQL compute clusters, and storage buckets (S3/ADLS/GCS).
Data never leaves the customer's Data Plane, ensuring security and compliance boundaries.

### Q2: What is Databricks Connect v2 and how does it execute PySpark code remotely?
**Answer:**
Databricks Connect v2 leverages the open-source **Spark Connect** protocol based on gRPC and Apache Arrow. Local Python code builds an unresolved logical plan. This plan is serialized and transmitted over gRPC to the remote Databricks cluster driver. The cluster compiles, optimizes (via Catalyst/Photon), and executes the physical plan against cloud storage, streaming result data back to the client as Arrow record batches.

### Q3: What is the difference between All-Purpose Clusters and Job Clusters?
**Answer:**
- **All-Purpose Clusters**: Interactive compute shared among developers for ad-hoc analysis and notebook development. They stay active until manually stopped or auto-terminated. Higher DBU cost.
- **Job Clusters**: Ephemeral clusters created automatically by the Databricks Jobs service when a job starts and terminated immediately upon completion. Lower DBU cost (~50% cost savings compared to interactive clusters).

---

## 2. Governance & Unity Catalog

### Q4: Explain the 3-tier namespace in Unity Catalog. Why is it superior to Hive Metastore?
**Answer:**
The 3-tier namespace is `catalog.schema.table`. It allows organizing data across business domains and deployment environments (e.g. `dev.finance.transactions`, `prod.finance.transactions`) within a single central metastore. Unlike Hive Metastore, Unity Catalog provides workspace-independent central governance, standard ANSI SQL access control (`GRANT`/`REVOKE`), dynamic row filters/column masks, and automated cross-table lineage tracking.

### Q5: How do Dynamic Data Masking and Row-Level Filters work in Unity Catalog?
**Answer:**
- **Dynamic Column Masking**: SQL UDFs check user group membership using functions like `IS_ACCOUNT_GROUP_MEMBER('pii_admins')`. If the user is authorized, the raw value is returned; otherwise, a masked format (e.g. `XXX-XX-1234`) is returned dynamically during query execution.
- **Row-Level Filtering**: A SQL filter function is attached to a table via `ALTER TABLE ... SET ROW FILTER`. The function executes implicitly during query evaluation to prune unauthorized rows based on user role or department tags.

---

## 3. Storage, Ingestion, & Delta Live Tables (DLT)

### Q6: How does Auto Loader (`cloudFiles`) differ from standard PySpark streaming file readers?
**Answer:**
Standard file readers perform full directory list scans on cloud storage, which becomes prohibitively slow and expensive as file counts exceed hundreds of thousands. Auto Loader uses **File Notification Mode** (cloud event notifications via SQS/Event Grid) or an optimized RocksDB file list cache to incrementally detect new files. Additionally, Auto Loader automatically handles schema inference, schema evolution, and rescued data column (`_rescued_data`) management.

### Q7: What are the three expectation modes in Delta Live Tables (DLT)?
**Answer:**
1. `@dlt.expect("valid_id", "id IS NOT NULL")`: Logs quality metric failures to the DLT event log but lets the invalid record pass through.
2. `@dlt.expect_or_drop("valid_id", "id IS NOT NULL")`: Logs the failure and silently drops invalid records from the target table.
3. `@dlt.expect_or_fail("valid_id", "id IS NOT NULL")`: Logs the failure and halts the entire pipeline run immediately upon detecting invalid data.

### Q8: How does `dlt.apply_changes()` simplify Change Data Capture (CDC)?
**Answer:**
`dlt.apply_changes()` automates ingestion of CDC log feeds into target tables. It handles out-of-order event arrivals, primary key deduplication, sequence ordering (by timestamp or version offset), and automatically maintains target tables as **SCD Type 1** (overwriting updates) or **SCD Type 2** (maintaining full history with effective start/end dates).

---

## 4. Performance Tuning & Optimization

### Q9: What is the Photon execution engine?
**Answer:**
Photon is Databricks' high-performance C++ native execution engine. It replaces standard Spark JVM execution for SQL and DataFrame workloads. Photon uses vectorized SIMD execution and direct CPU cache alignment to execute string parsing, aggregations, joins, and Delta file writes up to 5x faster than standard Spark Java bytecode execution.

### Q10: How does Adaptive Query Execution (AQE) optimize runtime join plans?
**Answer:**
AQE modifies Spark query execution plans based on runtime statistics gathered during shuffle stages:
1. **Dynamic Partition Coalescing**: Merges small post-shuffle partitions into larger partitions to avoid the small-file problem.
2. **Dynamic Join Selection**: Converts Sort-Merge Joins to Broadcast Hash Joins if runtime partition statistics show one side is smaller than the broadcast threshold.
3. **Dynamic Skew Join Handling**: Detects skewed partitions (unusually large data chunks) and splits them into smaller sub-partitions, duplicating matching rows on the join side to eliminate executor bottlenecks.


---

### Q11: What is Liquid Clustering in Databricks, and how does it compare to `PARTITION BY` + `Z-ORDER`?
**Answer:**
Liquid Clustering (`CLUSTER BY`) replaces rigid directory partitioning and manual `ZORDER` maintenance with automatic, incremental Hilbert-curve clustering. You can change clustering keys later via `ALTER TABLE` without rewriting historical files, and it eliminates over-partitioning small-file issues.

---

### Q12: Explain Serverless Compute vs. Classic Compute in Databricks (SQL Warehouses & Jobs).
**Answer:**
- **Classic Compute:** Clusters spin up inside your cloud VPC (3–5+ minutes startup), requiring instance-type selection and VPC/subnet capacity planning.
- **Serverless Compute:** Managed by Databricks with ~2–10 second startup, instant elastic autoscaling, automatic runtime patching, and zero idle-VM management.

---

### Q13: How do Databricks Asset Bundles (DABs) enable CI/CD across `dev`, `staging`, and `prod`?
**Answer:**
DABs define jobs, DLT pipelines, Unity Catalog targets, and cluster configs declaratively in `databricks.yml`. In GitHub Actions/Azure DevOps, `databricks bundle validate` verifies syntax and `databricks bundle deploy -t prod` promotes identical tested artifacts across workspaces cleanly.

---

### Q14: What is the difference between `%run` and `dbutils.notebook.run()` in notebook orchestration?
**Answer:**
- **`%run`:** Executes another notebook inline within the **same SparkSession and variable scope** (ideal for importing shared helper functions).
- **`dbutils.notebook.run()`:** Launches a separate isolated job run with parameters and a timeout, returning a string exit value (better for modular orchestration, though Databricks Workflows multi-task DAGs are preferred in production).

---

### Q15: How do Databricks Disk Cache (formerly Delta Cache) and Spark `cache()` differ?
**Answer:**
- **Spark `cache()`:** Stores deserialized JVM/columnar blocks in executor **RAM**, competing with shuffle/execution memory and requiring explicit `cache()` calls.
- **Databricks Disk Cache:** Automatically caches remote cloud-storage Parquet pages onto local NVMe **SSDs** on worker nodes transparently, accelerating repeated scans with zero executor heap pressure.

---

### Q16: How does Auto Loader handle schema evolution and unexpected corrupt fields via `_rescued_data`?
**Answer:**
When `cloudFiles.schemaEvolutionMode = "addNewColumns"` is enabled, Auto Loader adds newly seen columns and restarts the stream cleanly. Any type-mismatched or unparseable fields are preserved as JSON inside `_rescued_data` instead of dropping records or failing the pipeline.

---

### Q17: Explain Databricks Secret Scopes and how they prevent credential leaks in notebooks.
**Answer:**
Secret Scopes store credentials either in Databricks-backed encrypted storage or backed by Azure Key Vault / AWS Secrets Manager. Calling `dbutils.secrets.get(scope, key)` injects secrets at runtime and automatically prints `[REDACTED]` if anyone tries to `print()` or display the value in notebook outputs.

---

### Q18: What are Cluster Policies and Instance Pools, and why do platform teams enforce them?
**Answer:**
- **Cluster Policies:** JSON rules limiting allowed node types, DBU caps, Photon/LTS versions, and mandatory auto-termination timers (preventing runaway cost).
- **Instance Pools:** Pre-warmed idle VMs that shrink cluster startup time from minutes to seconds across frequent short jobs.

---

### Q19: Explain Databricks Vector Search and how it integrates with Unity Catalog & Delta Lake.
**Answer:**
Databricks Vector Search creates managed vector indexes directly synced from a source **Delta Table** with Change Data Feed (`Delta Sync Index`). Updates to the Bronze/Silver/Gold Delta table automatically update embeddings while inheriting Unity Catalog ACL governance.

---

### Q20: How does System Tables (`system.billing.usage`, `system.access.audit`, `system.access.table_lineage`) help FinOps & Governance?
**Answer:**
Unity Catalog exposes operational telemetry as SQL-queryable Delta tables (`system.*`), letting data platform teams build automated dashboards for DBU spend attribution per job/user, audit unauthorized access attempts, and trace column-level lineage across workspaces.

---

### Q21: How do you troubleshoot a slow Databricks Jobs multi-task DAG?
**Answer:**
Check the **Jobs Run Timeline** to separate cluster startup time from task execution time; inspect the Spark UI for shuffle skew or spill; verify Photon is enabled for SQL/DataFrame-heavy tasks; and share a single Job Cluster across sequential small tasks to avoid repeated spin-up delays.

---

### Q22: What is the difference between a Materialized View and a Streaming Table in Databricks SQL / DLT?
**Answer:**
- **Streaming Table:** Processes each new input row **exactly once** (append-only/incremental ingestion via Auto Loader or Kafka).
- **Materialized View:** Represents a precomputed query (aggregations, joins) refreshed incrementally where possible or recomputed as needed when upstream tables change.

---

### Q23: How does Unity Catalog manage external cloud storage securely via Storage Credentials & External Locations?
**Answer:**
Instead of distributing IAM access keys or SAS tokens to workspaces, an admin creates a **Storage Credential** (IAM Role / Managed Identity) and binds it to an **External Location** (`s3://bucket/prefix/`). Users receive `READ FILES` or `CREATE EXTERNAL TABLE` grants on the External Location without ever seeing raw cloud keys.

---

### Q24: What is Predictive Optimization in Unity Catalog?
**Answer:**
Predictive Optimization automatically monitors managed Unity Catalog Delta tables and schedules `OPTIMIZE`, `VACUUM`, and `ANALYZE` statistics updates only when fragmentation or query patterns justify the DBU cost—eliminating manual maintenance scripts.

---

### Q25: How does MLflow integrate with Unity Catalog for enterprise ML & LLM pipelines?
**Answer:**
MLflow Model Registry in Unity Catalog (`catalog.schema.model_name`) governs ML models and LLM endpoints under the same 3-tier namespace, RBAC permissions, lineage tracking (linking training datasets to registered models), and stage aliases (`@champion`, `@challenger`) as Delta tables.
