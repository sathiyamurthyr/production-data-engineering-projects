# Enterprise Design Decisions and Rationale

This document outlines the core architectural and implementation decisions made for **03 Advanced SQL for Data Engineering**.

---

## 1. ANSI SQL Compatibility with Engine Dialect Notes

### Decision
Write primary SQL code using strict ANSI SQL standards compatible with PostgreSQL, SQLite, Snowflake, and Databricks SQL, while providing explicit inline notes and reference blocks for engine-specific syntax (e.g. `crosstab` in Postgres, native `PIVOT` in Snowflake).

### Rationale
In enterprise environments, data engineering workloads frequently span operational databases (PostgreSQL/MySQL), local testing engines (SQLite), and cloud analytical warehouses (Snowflake, BigQuery, Databricks). Maintaining ANSI SQL portability ensures data engineers can deploy queries across heterogeneous data platforms without re-architecting baseline logic.

---

## 2. Window Functions vs. Self-Joins for Analytical Aggregations

### Decision
Exclusively use Window Functions (`SUM() OVER()`, `ROW_NUMBER()`, `LAG()`, `LEAD()`) for running totals, moving averages, top-N grouping, and sessionization rather than self-joins (`JOIN ON t1.id >= t2.id`).

### Rationale
- **Performance**: Self-joins for running totals exhibit quadratic $O(N^2)$ time and space complexity, leading to severe memory spills on large tables. Window functions execute in $O(N \log N)$ time with single-pass memory overhead per partition.
- **Readability**: Window specifications cleanly decouple partitioning, sorting, and frame boundaries, preventing complex nested join logic.

---

## 3. High Sentinel Dates (`9999-12-31`) for SCD Type 2 Effective Bounds

### Decision
Use `'9999-12-31 23:59:59'` as the `valid_to` timestamp for active SCD Type 2 dimension rows instead of `NULL`.

### Rationale
- **Index Usage**: Relational query planners cannot effectively utilize B-tree index range scans when predicates contain `OR valid_to IS NULL`.
- **Query Simplicity**: Downstream BI analysts and star-schema join queries can use clean `BETWEEN valid_from AND valid_to` predicates without needing defensive `COALESCE` or conditional `OR` clauses.

---

## 4. Hash Key MD5 / SHA-256 for Data Vault 2.0 Ingestion

### Decision
Utilize string MD5/SHA256 hashes of natural business keys for Hub and Link table primary keys rather than auto-incrementing database sequences.

### Rationale
- **Parallelization**: Hash keys can be calculated independently by distributed ingestion workers (Spark, Flink, Kafka Connect) prior to database insertion.
- **Lock Contention**: Auto-incrementing sequences create global table lock bottlenecks during multi-node concurrent ingestion. Hash keys remove all cross-worker sequence synchronization.

---

## 5. Deduplication via `ROW_NUMBER()` over `GROUP BY MAX()`

### Decision
Use `ROW_NUMBER() OVER (PARTITION BY pk ORDER BY event_timestamp DESC)` inside a CTE to isolate the latest record version during CDC deduplication and ETL staging loading.

### Rationale
- **Full Row Integrity**: `GROUP BY pk` combined with `MAX(timestamp)` requires secondary joins back to the source table to retrieve non-aggregated payload columns, leading to double table scans. `ROW_NUMBER()` extracts the entire payload tuple cleanly in one pass.
- **Deterministic Tie-Breaking**: Secondary order columns (e.g. `raw_id DESC`, `lsn_seq DESC`) can be appended to the window specification to resolve identical timestamp conflicts deterministically.

---

## 6. Embedded SQLite In-Memory Python Testing Framework

### Decision
Build unit testing fixtures around Python's standard library `sqlite3` engine using a custom dictionary result factory (`QueryExecutor`).

### Rationale
- **Zero External Dependencies**: Enables lightning-fast, zero-setup local unit testing without requiring Docker containers or active PostgreSQL instances.
- **CI/CD Speed**: In-memory execution allows running complete pytest test suites in under 1 second.
