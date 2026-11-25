# Amazon Redshift Interview Questions & Answers

This document lists critical technical interview questions regarding Amazon Redshift, tailored for senior data engineering roles.

---

### Q1: How does Amazon Redshift achieve high performance for analytical queries?
**Answer:**
Amazon Redshift achieves fast query execution on massive datasets using three key design concepts:
1. **Massively Parallel Processing (MPP):** Queries are split across multiple compute nodes and processed in parallel across independent compute slices.
2. **Columnar Storage:** Data is stored on disk column-by-column rather than row-by-row. This reduces disk I/O because queries scanning specific columns only read those columns' blocks.
3. **Data Compression:** Columnar storage allows columns containing similar data types to be compressed efficiently (using AZ64 or ZSTD encodings). This reduces disk usage and read latencies.
4. **Compiled Code:** The leader node compiles queries into highly optimized C++ code and distributes it to the compute nodes, avoiding the overhead of interpreter execution.

---

### Q2: What are the different distribution styles in Amazon Redshift, and how do you choose among them?
**Answer:**
Redshift uses four distribution styles to determine how data is distributed across slices:
1. **KEY:** Data is distributed based on the hash value of a single column. Choose this for large fact and dimension tables joined together on a common high-cardinality key (e.g., `customer_id` or `product_id`). This ensures a **Colocated Join** (no data is moved across the network during execution).
2. **ALL:** A full copy of the table is written to the first slice of every compute node. Choose this for small lookup tables (< 2-3 million rows) to avoid data shuffling during joins.
3. **EVEN:** Rows are distributed round-robin across slices. Choose this when tables are joined infrequently, when there is no clear distribution key, or to balance storage when KEY distribution causes high data skew.
4. **AUTO:** Redshift assigns the distribution style based on the size of the table. Small tables start as ALL and automatically transition to EVEN or KEY as they grow.

---

### Q3: Why does the first column of a COMPOUND sort key need to be uncompressed (RAW encoding)?
**Answer:**
Redshift stores data in 1MB blocks and tracks the minimum and maximum values of each column in a block-level index called a **Zone Map**. 
When the first column of a compound sort key is uncompressed (`RAW`), the leader node can scan the Zone Maps and evaluate filters directly on the raw bytes without spending CPU cycles decompressing index metadata blocks. This speeds up the process of skipping irrelevant data blocks during disk scans.

---

### Q4: Are primary key and foreign key constraints enforced in Amazon Redshift?
**Answer:**
No. Redshift does not enforce primary, foreign, or unique key constraints during `INSERT`, `UPDATE`, or `COPY` operations. 
However, they should still be defined in your DDL statements because the Redshift Query Optimizer uses these constraints as informational metadata to optimize join execution plans, estimate cardinality, and perform query rewrites. Data engineers must ensure data uniqueness and referential integrity upstream during the ETL phase.

---

### Q5: How do you identify and resolve data skew in a Redshift cluster?
**Answer:**
Data skew occurs when one slice contains significantly more rows than others due to an unbalanced distribution key. This creates a bottleneck because the cluster is only as fast as its slowest slice (the hot slice).
- **Detection:** Query the catalog view `svv_diskusage` or `svv_table_info` to check row counts and disk block usage per slice.
- **Resolution:** Change the distribution style. If using `KEY`, select a column with higher cardinality and more uniform value distribution. If no such column exists, use `EVEN` distribution to distribute data uniformly.

---

### Q6: What is the difference between Redshift Spectrum and Amazon Athena?
**Answer:**
While both allow querying data directly in S3 using standard SQL, they serve different operational scopes:
- **Redshift Spectrum** is a feature of Amazon Redshift. It requires a provisioned Redshift cluster or Serverless workgroup. It is designed to run queries that combine external data lakes (S3) with local warehouse tables inside a single query environment.
- **Amazon Athena** is a serverless, standalone interactive query service. It does not require a warehouse cluster. You pay per query based on data scanned. Athena is ideal for ad-hoc queries, log analysis, and lightweight transformations directly on S3.

---

### Q7: Explain the difference between `DS_DIST_NONE`, `DS_BCAST_INNER`, and `DS_DIST_BOTH` in an EXPLAIN plan.
**Answer:**
These represent data redistribution steps across compute nodes:
- **`DS_DIST_NONE` (Optimal):** No data needs to be moved. The join is colocated (both tables have matching distribution keys on matching slices).
- **`DS_BCAST_INNER` (Acceptable for small tables):** The inner table is broadcast to all compute nodes. This is fast if the inner table is very small.
- **`DS_DIST_BOTH` (Expensive):** Both tables are reshuffled across the network to match keys on slices. This indicates suboptimal distribution design and causes significant network overhead on large tables.

---

### Q8: What is the purpose of `VACUUM` and `ANALYZE` in Redshift database maintenance?
**Answer:**
- **`VACUUM`:** Reclaims storage space from rows marked for deletion (from `DELETE` or `UPDATE` queries) and resorts data according to the sort keys. Running `VACUUM` is crucial to maintain sorting order so that Zone Maps continue block-skipping effectively.
- **`ANALYZE`:** Updates the statistical metadata of tables. The Query Planner relies on accurate statistics to calculate query execution paths and WLM memory allocations. Running `ANALYZE` after data loads prevents the planner from executing sub-optimal join plans.
Modern Redshift executes both operations automatically in the background, but manual runs are recommended after heavy batch updates or tables loads.


---

### Q9: What is the difference between `COMPOUND` and `INTERLEAVED` sort keys in Redshift?
**Answer:**
- **`COMPOUND` (default):** Sorts data strictly in the order of listed columns `(col1, col2, col3)`. Optimal when queries filter on `col1` (the prefix); useless if queries filter only on `col2`.
- **`INTERLEAVED`:** Assigns equal weight to every sort key column using Z-order curves. Useful when queries filter independently on different columns, though `VACUUM REINDEX` is far slower and costlier—making `COMPOUND` (or Redshift `AUTO` sort keys) preferred in most workloads.

---

### Q10: Why is the `COPY` command orders of magnitude faster than multi-row `INSERT` statements in Redshift?
**Answer:**
`COPY` reads compressed Parquet/CSV/JSON files **in parallel across all compute slices directly from S3**, bypassing Leader Node bottlenecks and automatically sampling rows to choose optimal column compression encodings (`AZ64`, `ZSTD`), whereas `INSERT` routes serially through the Leader Node.

---

### Q11: How does `UNLOAD` work in Redshift, and why use `PARALLEL ON` vs `PARALLEL OFF`?
**Answer:**
`UNLOAD` writes query results directly from compute slices to S3 in parallel (Parquet/CSV). Keeping `PARALLEL ON` (default) lets each slice write concurrently without funneling through one node; use `PARALLEL OFF` or `MAXFILESIZE` only when a downstream legacy consumer strictly requires a single merged file.

---

### Q12: How do you handle `UPSERT` / `MERGE` patterns cleanly in Amazon Redshift?
**Answer:**
Redshift supports native `MERGE INTO` as well as the classic high-throughput staging pattern inside an explicit `BEGIN; ... COMMIT;` transaction:
1. `COPY` new batch into a `TEMP` staging table (`LIKE target_table`).
2. `DELETE FROM target USING staging WHERE target.pk = staging.pk;`
3. `INSERT INTO target SELECT * FROM staging;`
This guarantees atomic all-or-nothing updates.

---

### Q13: Explain Redshift Workload Management (WLM) — Automatic WLM vs. Manual WLM and Concurrency Scaling.
**Answer:**
- **Automatic WLM (recommended):** Dynamically allocates memory and concurrency slots per query queue based on query complexity and priority, while Short Query Acceleration (SQA) fast-tracks sub-second BI queries ahead of heavy ETL.
- **Concurrency Scaling:** Automatically spins up transient read/write scaling clusters within seconds during burst traffic so dashboards never queue behind ETL loads.

---

### Q14: Compare Redshift Provisioned (RA3) vs. Redshift Serverless.
**Answer:**
- **RA3 Provisioned:** Separates compute from **Redshift Managed Storage (RMS)** backed by S3, ideal for predictable 24/7 steady-state workloads with Reserved Instance discounts.
- **Redshift Serverless:** Bills per RPU-second only while queries execute (scales to zero when idle), ideal for bursty, intermittent, or dev/analytics workloads.

---

### Q15: What is Redshift AQUA (Advanced Query Accelerator) on RA3 nodes?
**Answer:**
AQUA is a hardware-accelerated cache layer sitting between RA3 compute nodes and S3 Managed Storage that pushes down `SCAN`, `FILTER`, `LIKE`, and simple aggregations directly onto custom Nitro/FPGA hardware—cutting network transfer to compute nodes by up to 10x.

---

### Q16: How does Redshift Data Sharing work without copying data?
**Answer:**
Data Sharing allows a Producer RA3/Serverless cluster to grant live, transactionally consistent read access to specific schemas/tables/views to Consumer clusters (across accounts/regions via RMS) with zero ETL duplication and isolated Consumer compute billing.

---

### Q17: How do Redshift Materialized Views accelerate BI dashboards, and when do they refresh incrementally?
**Answer:**
Materialized Views precompute expensive joins and aggregations. When base tables only receive `INSERT`s (`AUTO REFRESH YES`), Redshift performs fast **incremental refreshes**; if base tables undergo `UPDATE`/`DELETE`s, Redshift falls back to full recomputation.

---

### Q18: Why should you avoid `SELECT *` and oversized `VARCHAR(65535)` columns in Redshift?
**Answer:**
Even with columnar storage, `SELECT *` forces scanning and network redistribution of unused columns. Defining `VARCHAR(65535)` allocates oversized intermediate sort/hash buffers in WLM memory during joins and `GROUP BY`s—causing unnecessary disk spills (`svl_query_summary` `is_diskbased = true`).

---

### Q19: Which Redshift system tables/views do you check first when debugging a slow query?
**Answer:**
- `SYS_QUERY_HISTORY` / `STL_QUERY`: Total runtime, queue time vs execution time.
- `SVL_QUERY_SUMMARY` / `SYS_QUERY_DETAIL`: Step-level broadcast/redistribution (`DS_DIST_BOTH`), row skew across slices, and `is_diskbased` spills.
- `SVV_TABLE_INFO`: Unsorted %, stats staleness (`stats_off`), ghost rows needing `VACUUM`, and skew ratio.

---

### Q20: How does Zero-ETL integration between Amazon Aurora/RDS and Redshift work?
**Answer:**
AWS Aurora/RDS Zero-ETL continuously replicates transactional CDC changes near-real-time into Amazon Redshift tables without maintaining custom Glue/DMS/Kafka pipelines—automatically creating target schemas and applying updates/deletes cleanly.
