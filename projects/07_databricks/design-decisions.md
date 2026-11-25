# Architectural Design Decisions & Tradeoffs: Databricks Engineering

This document outlines key technical decisions, alternative choices, rationale, and tradeoffs made when designing production Databricks data platforms.

---

## 1. Governance: Unity Catalog vs. Legacy Hive Metastore

### Decision
Migrate all production workloads from legacy **Hive Metastore** to **Unity Catalog (UC)** 3-tier namespace (`catalog.schema.table`).

### Rationale
- **Cross-Workspace Governance**: Legacy Hive metastores required separate metastores per workspace or complex external metastore sync. Unity Catalog centralizes governance across multiple workspaces in Azure, AWS, and GCP.
- **Fine-Grained RBAC & Dynamic Security**: UC provides standard ANSI SQL `GRANT` and `REVOKE` privileges down to row filters and column masks.
- **Data Lineage**: Automated runtime data lineage capture across notebooks, jobs, and SQL queries.

### Tradeoffs
- **Migration Effort**: Requires updating table references from `hive_metastore.db.table` to `catalog.schema.table`.
- **Runtime Versioning**: Requires DBR 11.3 LTS or higher.

---

## 2. Ingestion: Auto Loader (`cloudFiles`) vs. Standard Batch / Stream Reading

### Decision
Standardize on **Databricks Auto Loader (`cloudFiles`)** for raw cloud file landing ingestion.

### Comparison Table

| Metric / Capability | Standard PySpark `readStream` | Databricks Auto Loader (`cloudFiles`) |
| :--- | :--- | :--- |
| **Directory Discovery** | Full S3/ADLS listing on every batch (O(N) files) | Event Notification Mode (SNS/SQS or Event Grid) or RocksDB cached listing |
| **Schema Evolution** | Crashes on unexpected columns | Automatic `addNewColumns` or rescued data tracking (`_rescued_data`) |
| **Cost Scaling** | API request cost spikes on millions of files | Near-zero directory listing API cost |
| **Scalability Limit** | Degrades at ~100k files | Handles 100M+ files seamlessly |

---

## 3. Pipeline Framework: Delta Live Tables (DLT) vs. Standalone Notebook Jobs

### Decision
Adopt **Delta Live Tables (DLT)** for core Medallion pipelines (Bronze -> Silver -> Gold).

### Rationale
- **Declarative Development**: Developers specify target transformations; DLT automatically manages task dependencies, retry logic, and batch/streaming execution transitions.
- **Data Quality Enforcement**: Native `@dlt.expect`, `@dlt.expect_or_drop`, and `@dlt.expect_or_fail` capture quality metrics automatically into event logs.
- **Automated CDC**: Built-in `dlt.apply_changes()` handles complex SCD Type 1 & 2 merges without manual error-prone MERGE SQL statements.

---

## 4. Execution Engine: Photon Engine vs. Standard PySpark JVM Engine

### Decision
Enable **Photon Engine** (`runtime_engine: "PHOTON"`) on all production job clusters and SQL Warehouses.

### Rationale
- Photon is a native C++ vectorized execution engine that executes columnar transformations directly in CPU cache.
- Delivers up to 3x-5x query acceleration on string manipulation, complex joins, and Delta writes.
- Reduces compute wall-clock execution duration, offsetting the slight increase in DBU cost.
