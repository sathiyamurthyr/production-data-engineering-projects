# Design Decisions: AWS Glue ETL Platform Implementation

This document details the engineering choices, trade-offs, and operational configurations selected for this AWS Glue architecture.

---

## 1. Compute Platform Choice: Serverless AWS Glue vs. EMR vs. Lambda

| Compute Platform | Cost Profile | Management Overhead | Warm-up Time | Scaling Characteristics | Decision Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AWS Glue (Serverless Spark)** | **Pay-per-second (DPU)** | **Zero (Serverless)** | **~1 minute (Glue 3.0+)** | **Auto-scaling worker nodes** | **Selected**: Best for daily/hourly batches, scheduled crawlers, zero-maintenance PySpark cluster setup. |
| **Amazon EMR** | Hourly EC2 instances + EMR premium | High (Cluster configuration, resizing, patches) | ~5-10 minutes | Manual or policy-based auto-scaling | Rejected: Excessive cost and overhead for periodic batch ETL. Better suited for 24/7 streaming or large shared data science workspaces. |
| **AWS Lambda** | Pay-per-execution millisecond | Low (Serverless) | <1 second | Concurrent scale (up to limits) | Rejected: Maximum timeout of 15 minutes, memory cap of 10GB, lack of native distributed Spark compute for large volumes. |

---

## 2. DynamicFrame vs. Apache Spark DataFrame
We elected to utilize AWS Glue `DynamicFrame` objects as the primary runtime container rather than converting directly to PySpark `DataFrames` at entry. 

### Trade-offs:
- **DynamicFrame Advantages**:
  - **Dynamic Schema Inference**: Handles dirty data where columns might contain multiple data types (e.g. `revenue` represented as a string `"100.00"` in some records and double `100.00` in others). Glue handles this using a `ChoiceType` column wrapper.
  - **Error Routing**: Records that fail schema matching or throw casting exceptions can be isolated without throwing runtime JVM exceptions, allowing the pipeline to finish cleanly.
- **Conversion Overhead**:
  - Converting between `DynamicFrame` and PySpark `DataFrame` (via `toDF()` and `fromDF()`) serializes the dataset across JVM and python boundaries, introducing minor latency.
  - **Decision**: Read and write data using native DynamicFrame sinks/sources. Use Spark DataFrame representations *only* within custom pytest assertions and complex window calculations where native DynamicFrame operations are not supported.

---

## 3. Glue Data Catalog Schema Evolution Strategy
We configure our catalog schemas using **Glue Crawlers** and explicitly control table updates.

- **Crawler Update Behavior**: Set to `UPDATE_IN_DATABASE`. When the crawler detects a new column, it appends it to the table metadata structure, preserving old columns.
- **Crawler Delete Behavior**: Set to `DEPRECATE_IN_DATABASE` (or `LOG` only). When an S3 object is deleted, we **do not** drop the table column. This ensures historical queries in Athena/Redshift Spectrum looking back at old partitions do not fail.
- **Schema Validation**: Evaluated at runtime using **AWS Glue Data Quality (DQDL)** definitions. Bad schemas fail early during ETL, preventing corrupted data from dirtying the S3 processed partition zones.

---

## 4. Partitioning Strategy
We selected `region` as the primary partition key for the curated output.
- **Query Pattern Alignment**: DOWNSTREAM analytics queries (via Athena/Presto) regularly filter on client region (`North`, `South`, `East`, `West`). Partitioning by `region` reduces the volume of S3 scanned data by ~75%.
- **Small File Avoidance**: Partitioning by daily timestamps (e.g. `year=YYYY/month=MM/day=DD`) for small-batch ecommerce data can lead to the "many small files" problem. Region partitioning aggregates data into highly performant files (>128MB per Parquet block).

---

## 5. Job Bookmarks: State Tracking for Incremental Load
AWS Glue Job Bookmarks are enabled (`--job-bookmark-option=job-bookmark-enable`).

- **Bookmark Mechanism**: Glue tracks metadata (such as timestamps, S3 file creation dates, and object keys) in a dedicated internal state store.
- **Execution Rationale**: During daily runs, the ETL job only processes new raw transaction files uploaded since the last successful run commit (`job.commit()`).
- **Rewinds & Reprocessing**: If a downstream bug is discovered, the bookmark can be reset (rewound to run ID or origin) via the AWS Console or boto3 CLI without modifying ETL code, enabling safe, repeatable backfills.
