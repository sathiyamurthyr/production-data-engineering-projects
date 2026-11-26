# 04. Hive, Sqoop, Hadoop, Cloud & Performance — Interview Q&A

---

## Part A: Performance Case Studies & Tuning

### Q1: Describe a real-world ingestion automation challenge from your previous project.
**Answer:**
In a production enterprise migration (e.g., AbbVie), ingesting each source table via Sqoop into Hadoop/Hive required **2 YAML configs** (one for Sqoop extraction attributes, one for Hive standardization rules) and **at least 1 HQL script**. Across **500 tables**, manually authoring 1,000+ YAMLs and 500+ HQL scripts was error-prone and slow. I built a **Python metadata-driven automation utility** to generate and validate those artifacts dynamically from source catalog metadata—eliminating manual drift and turning it into a reusable client optimization framework.

---

### Q2: Describe production performance bottlenecks you faced and how you resolved them.
**Answer:**
1. **Sqoop Serial Bottleneck:** Used `--boundary-query` + `--split-by` to parallelize mappers on large RDBMS tables lacking primary keys.
2. **Hive Slow Joins:** Enabled **Map-Side Joins** (`hive.auto.convert.join=true`) when joining large fact tables with small lookup tables.
3. **Spark Data & Metadata Shipping:** Used **Broadcast variables / Broadcast Joins** so small reference datasets stay cached on worker nodes rather than re-shipping per task or shuffling across stages.

---

## Part B: Hive, Sqoop & File Formats

### Q3: What is Sqoop's default file format and compression, vs. the best analytical combination?
**Answer:**
- **Sqoop Default:** Plain **Text** (`--as-textfile`) and **gzip** (note: gzip is non-splittable).
- **Best Analytical Combination:** **Apache Parquet** + **Snappy** (columnar storage, embedded schema, splittable, fast CPU decompression, high space savings).

---

### Q4: How do you Sqoop a large RDBMS table that has NO primary key or unique key?
**Answer:**
1. Pass `--split-by <indexed_numeric_or_date_col>` with `--boundary-query "SELECT MIN(col), MAX(col) FROM table"` so Sqoop computes `N` balanced range queries across mappers instead of falling back to `-m 1` (single mapper bottleneck).
2. Cap `--num-mappers` conservatively (e.g., `4–8`) because `N` mappers open `N` concurrent DB connections and can overwhelm an OLTP source.
3. If no numeric/date split column exists, use `--autoreset-to-one-mapper` or extract via `MOD(ROWNUM, N)` / CDC snapshots.

---

### Q5: What is the difference between Internal (Managed) and External Tables in Hive?
**Answer:**
| Feature | Internal (Managed) Table | External Table |
|---|---|---|
| **Ownership** | Hive owns both metadata **and** underlying HDFS/S3 data files. | Hive owns only **metadata**; storage path is externally managed. |
| **`DROP TABLE` Impact** | Deletes metadata **and** permanently deletes data files. | Deletes metadata **only**; underlying HDFS/S3 data remains intact. |
| **Best Use Case** | Temporary/staging tables owned exclusively by Hive. | Production Data Lakes shared across Spark, Presto/Trino, and Athena. |

---

### Q6: How do you handle new column additions in Hive tables across Parquet vs. Avro?
**Answer:**
- **Parquet / Text:** Older Parquet files lack the new column; you often use `ALTER TABLE ... ADD COLUMNS` (reading missing fields as `NULL` in newer Hive/Spark) or recreate via a temp table + `INSERT OVERWRITE` when reordering/changing types.
- **Avro:** Excels when source DDLs evolve frequently—updating the external `.avsc` Avro schema file handles added columns with defaults seamlessly without rewriting historical data.

---

### Q7: When should you choose Avro vs. Parquet?
**Answer:**
- **Avro (Row-oriented):** Best for **write-heavy streaming / Kafka**, Schema Registry evolution, and tables whose columns change frequently.
- **Parquet (Column-oriented):** Best for **read-heavy analytics**, BI aggregations, Spark/Athena/Redshift Spectrum (reads only projected columns with Snappy compression).

---

### Q8: Compare Static Partitioning, Dynamic Partitioning, and `LOAD DATA` in Hive.
**Answer:**
- **Static Partitioning:** You explicitly hardcode the partition value at write/load time (`INSERT INTO tbl PARTITION (dt='2026-11-25') ...`). Faster when loading one known partition.
- **Dynamic Partitioning:** Hive derives partition directories automatically from data values (`SET hive.exec.dynamic.partition.mode=nonstrict; INSERT INTO tbl PARTITION (dt) SELECT ..., dt FROM src;`).
- **Hive Load Partition (`LOAD DATA [LOCAL] INPATH` + `MSCK REPAIR TABLE`):** Moves/copies raw files directly into the table's HDFS/S3 partition path and runs `ALTER TABLE ... ADD PARTITION` (or `MSCK REPAIR TABLE`) to register new partition metadata in the Hive Metastore.

---

### Q9: What is Data Salting, and how does `zipWithIndex()` / salting fix Data Skew?
**Answer:**
- **Salting:** Appending a pseudo-random prefix/suffix (`0..K-1` or `a-`, `b-`, `c-`, `d-` across `a-machine0001`, `b-machine0001`) to hot keys so skewed rows spread evenly across multiple reducers/regions instead of hitting one hot task.
- **`zipWithIndex()` / Salting in Joins:** When a single hot key causes one Spark partition to lag, salt the skewed table with `floor(rand() * K)` (or `zipWithIndex() % K`) and explode the small lookup table across `0..K-1` so join work distributes evenly.

---

## Part C: Hadoop, YARN, HDFS, Cloud & DevOps

### Q10: Explain YARN, JobTracker vs. ApplicationMaster/ResourceManager, and TaskTracker vs. NodeManager.
**Answer:**
- **Hadoop 1.x:** A single **JobTracker** handled both cluster resource management and job scheduling, while **TaskTrackers** executed MapReduce slots—creating a scalability bottleneck (~4,000 nodes max).
- **Hadoop 2.x+ / YARN (Yet Another Resource Negotiator):** Split responsibilities cleanly:
  - **ResourceManager (RM):** Global cluster resource allocator.
  - **NodeManager (NM):** Per-node container/health agent (replaced **TaskTracker**).
  - **ApplicationMaster (AM):** Per-application coordinator negotiating containers and handling task retries (replaced the per-job scheduling role of **JobTracker**).

---

### Q11: What is Rack Awareness in HDFS/Hadoop, and how do you run HDFS File Counts, Comparisons & Data Quality checks?
**Answer:**
- **Rack Awareness:** HDFS places replica 1 on the local node, replica 2 on a **different rack**, and replica 3 on another node in that second rack—guaranteeing fault tolerance against full rack/switch failures while minimizing cross-rack bandwidth on reads.
- **HDFS File Count & Verification Commands:**
  - `hdfs dfs -count -q /path` (directory count, file count, byte size)
  - `hdfs dfs -du -h /path` (partition sizes to spot empty/0-byte files)
  - `diff` / checksum (`hdfs dfs -checksum`) or Spark row-count + schema/null/hash reconciliation between source RDBMS and target HDFS/Hive tables (`source_count == target_count`, column checksums).

---

### Q12: Why is AWS S3 the backbone of modern Data Lakes, and how do Kubernetes and REST APIs fit in?
**Answer:**
- **AWS S3:** Provides 11 nines durability, decoupled storage vs. compute, **strong read-after-write consistency**, lifecycle tiering (Standard → Glacier), and native integration with Spark/EMR, Glue, Athena, and Redshift Spectrum.
- **Kubernetes (Containers):** Orchestrates containerized microservices, Airflow workers (`KubernetesExecutor`), and Spark/EMR-on-EKS jobs with auto-healing, dependency isolation, and horizontal autoscaling.
- **REST API Ingestion Experience:** Paginated extraction (cursor/offset), OAuth/Bearer auth via Secrets Manager, HTTP 429/5xx exponential backoff retries, JSON schema validation, and DLQ routing for malformed payloads.
