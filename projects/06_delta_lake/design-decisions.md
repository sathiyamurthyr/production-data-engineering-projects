# Architectural Design Decisions & Trade-off Analysis

> **Data Engineering Diaries** | Project 06: Delta Lake

This document details key architectural decisions, design patterns, and storage format comparisons evaluated when engineering this Delta Lake reference architecture.

---

## 1. Storage Format Evaluation: Delta Lake vs. Iceberg vs. Hudi vs. Parquet

### Comparison Matrix

| Architectural Feature | Vanilla Parquet | Delta Lake (3.x) | Apache Iceberg | Apache Hudi |
| :--- | :--- | :--- | :--- | :--- |
| **ACID Transactions** | ❌ No | ✅ Single-table ACID | ✅ Multi-table ACID (via catalog) | ✅ Single-table ACID |
| **Time Travel** | ❌ No | ✅ By Version & Timestamp | ✅ By Snapshot ID & Timestamp | ✅ By Savepoint & Commit |
| **Schema Evolution** | ⚠️ Partial (schema drift risk) | ✅ `mergeSchema` / `overwriteSchema` | ✅ Full in-place column renaming/deletion | ✅ Full evolution support |
| **Data Skipping** | ❌ None (file listing overhead) | ✅ File min/max stats + Z-Ordering | ✅ Manifest-level column stats | ✅ Record index & bloom filters |
| **CDC Integration** | ❌ Manual diffing required | ✅ Native Change Data Feed (CDF) | ✅ Change Log Views | ✅ Native Copy-on-Write / Merge-on-Read |
| **Engine Ecosystem** | ✅ Universal | ✅ Spark, Trino, Flink, Presto, DuckDB | ✅ Spark, Flink, Trino, Presto, Dremio | ⚠️ Spark-centric, growing Flink |

### Decision Rationale for Delta Lake
- **Spark & Databricks Native Alignment**: Delta Lake delivers optimal write throughput and zero-copy optimization on Spark clusters.
- **Change Data Feed**: Native CDF simplifies Bronze-to-Silver incremental pipelines without requiring custom timestamp tracking.
- **Z-Ordering Performance**: Multi-dimensional spatial clustering provides high query performance on high-cardinality columns without the directory file sprawl of Hive partitioning.

---

## 2. Partitioning vs. Z-Ordering Decision Framework

### Decision Tree

```
                       Is dataset total size > 1 TB?
                              /          \
                             /            \
                           NO             YES
                          /                \
            Use Z-ORDER BY only     Are candidate columns low-cardinality (< 10,000 distinct)?
           (Avoid small files)              /                   \
                                           /                     \
                                         YES                     NO
                                         /                         \
                          Partition BY low-cardinality      Z-ORDER BY high-cardinality
                          (e.g., event_date, region)        (e.g., user_id, device_id)
```

### Trade-off Summary
- **Hive Partitioning**: Subdivides data into disk directories (`/date=2026-03-01/`). Perfect for coarse-grained partition pruning, but over-partitioning creates millions of 1MB files and overloads cloud object store metadata operations.
- **Z-Ordering (Morton Curves)**: Organizes data *within* Parquet files. Enables fine-grained file pruning without changing folder structure. Limited to 1–4 high-cardinality columns.

---

## 3. Maintenance Policy Decisions: VACUUM & Retention

### Decision Rationale
- **Default Retention**: Fixed at 7 days (168 hours).
- **Safety Overrides**: Disabling the safety threshold (`spark.databricks.delta.vacuum.parallelDelete.enabled`) is strictly restricted to automated test fixtures or dedicated retention purge scripts during scheduled maintenance windows.
- **Rationale**: Long-running ETL jobs or analyst ad-hoc queries opening a snapshot will fail with `FileNotFoundException` if active tombstoned files are vacuumed out from underneath them.

---

## 4. Upsert Strategy: MERGE INTO vs. Overwrite

### Decision
- **SCD Type 1 Updates**: Enforce pre-deduplication of incoming source DataFrames on primary keys before running `MERGE INTO`.
- **Reason**: Duplicate primary keys in source cause runtime `AnalysisException`. Pre-deduplication using window functions (`ROW_NUMBER() OVER (PARTITION BY key ORDER BY timestamp DESC)`) guarantees deterministic single-row matching.
