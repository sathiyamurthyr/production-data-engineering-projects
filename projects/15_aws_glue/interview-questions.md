# Technical Interview Preparation: AWS Glue & Serverless ETL

This document contains deep technical questions and answers focusing on AWS Glue, Spark architecture, metadata cataloging, and best practices.

---

### Q1: What is the architectural difference between `SparkContext` and `GlueContext`?
**Answer**:
- **`SparkContext` (sc)**: The core entry point for Apache Spark. It handles the low-level connection to the Spark cluster coordinator, manages RDD distributions, registers executor nodes, and tracks worker tasks.
- **`GlueContext`**: An extension of `SparkContext` created by AWS. It wraps the Spark cluster manager and injects Glue-specific libraries. These libraries support:
  - Reading and writing native `DynamicFrame` structures.
  - Native integration with the AWS Glue Data Catalog (without needing to set up separate hive-metastore configurations).
  - Out-of-the-box S3 connection optimizations (like S3 select integration, partitioned index listings).
  - Integration with the AWS Glue Data Quality engine and Schema Registry.

---

### Q2: How do AWS Glue Job Bookmarks work under the hood? What happens if `job.commit()` is omitted?
**Answer**:
- **Under the Hood**: When a job bookmark is enabled, AWS Glue tracks stateful information (such as S3 object keys, file modification times, and partition details) inside an internal database. When reading S3 locations, Glue queries this metadata store and filters out files that have modification timestamps prior to or equal to the high-watermark timestamp of the last successful run.
- **Role of `job.commit()`**: The `job.commit()` call updates the internal state store with the list of processed S3 objects and commits the new high-watermark timestamp. If `job.commit()` is omitted or if the job crashes before hitting it:
  1. The new watermark is **not** persisted.
  2. The next run will re-process the exact same input files, resulting in duplicated outputs in downstream tables (unless downstream processes handle deduplication).

---

### Q3: How does AWS Glue handle a column that contains multiple active data types (e.g. integer in some files, string in others)?
**Answer**:
- Apache Spark would either throw a parsing exception, nullify the mismatching fields, or cast the entire column to string (widest common type).
- AWS Glue handles this using **`ChoiceType`** inside a `DynamicFrame`. A `ChoiceType` column maintains representations for both types simultaneously (e.g. `order_id` is kept as both a double and a string).
- Engineers resolve this using **`resolveChoice`**. You can cast the column using specs (e.g., `cast:double`), resolve it by keeping the type that is most common, or project the column split (e.g., splitting `order_id` into `order_id_double` and `order_id_string` in the output schema).

---

### Q4: Explain the differences between the three Glue worker types: `Standard`, `G.1X`, and `G.2X`. When should you use each?
**Answer**:
- **`Standard`**: Allocates 1 DPU (Data Processing Unit) consisting of 4 vCPUs and 16 GB of memory per worker. It runs two Spark executors (each with 5.5 GB memory). *Use case*: Small batch operations, flat file conversions, or simple database loads.
- **`G.1X`**: Allocates 1 DPU per worker consisting of 4 vCPUs and 16 GB of memory, but runs only one Spark executor (10 GB memory). *Use case*: Highly parallel jobs with memory-intensive ETL transformations.
- **`G.2X`**: Allocates 2 DPUs per worker consisting of 8 vCPUs and 32 GB of memory, running one executor (20 GB memory). *Use case*: Large datasets containing complex schemas, nested structures, deep joins, or large shuffles where other worker types experience Java heap space OOM.

---

### Q5: How do you perform data quality checks in a serverless Glue environment?
**Answer**:
- AWS Glue introduces a native **Glue Data Quality** engine that evaluates rules defined in **DQDL (Data Quality Definition Language)**.
- Rules can check row counts (`RowCount > 0`), completeness (`IsComplete "order_id"`), column ranges, patterns, data types, and custom conditions.
- Inside the ETL script, you invoke the `EvaluateDataQuality` class, passing the ruleset.
- In production, we capture the evaluation outcome:
  - If the evaluation outcome is `Passed`, we let the job run to completion.
  - If it is `Failed`, we can route the telemetry records to an S3 log location, notify engineering via an SNS trigger, and abort the job to prevent bad data from populating partition zones.

---

### Q6: What is a Glue Workflow, and how does it compare to triggering jobs via EventBridge?
**Answer**:
- **Glue Workflow**: An internal orchestration system that groups multiple Glue Jobs, Crawlers, and Triggers into a Directed Acyclic Graph (DAG). You configure conditional triggers (e.g., Run Job B only when Job A and Crawler C both succeed). It tracks state internally and is easy to construct within the Glue environment.
- **Amazon EventBridge**: A general-purpose serverless event bus. You trigger Glue jobs based on broad AWS events (e.g., a file is uploaded to S3, triggering an S3 Event Notification, which triggers a Glue Job run).
- **Comparison**: Use Glue Workflows for pure Glue pipelines (Crawler -> ETL Job -> Dependent Job). Use EventBridge when the pipeline depends on external systems (e.g., triggering Glue when a DynamoDB stream triggers, or when an Lambda function completes).


---

### Q7: When should you convert a Glue `DynamicFrame` to a Spark `DataFrame`, and vice versa?
**Answer**:
- Keep **`DynamicFrame`** for initial Bronze ingestion when handling messy semi-structured JSON, `ChoiceType` schema conflicts, Glue Job Bookmarks, and Glue Data Catalog relationalize transforms.
- Convert to a **Spark `DataFrame`** (`dyf.toDF()`) for heavy aggregations, Window functions, complex joins, and Catalyst/AQE optimizations, then convert back (`DynamicFrame.fromDF(df, glueContext, "name")`) if writing with Glue Catalog / bookmark features.

---

### Q8: How do Glue Crawlers work, and when should you avoid using them in production?
**Answer**:
Glue Crawlers scan S3 prefixes, infer schemas/partitions, and register or update tables in the Glue Data Catalog. In high-scale production, frequent Crawlers add S3 listing cost and can accidentally create fractured tables if file schemas vary slightly; prefer explicit DDL/Terraform/Spark catalog registration or `MSCK REPAIR TABLE` / Iceberg/Delta catalogs for strict governance.

---

### Q9: What is the Glue `Relationalize` transform, and how does it handle nested JSON arrays?
**Answer**:
`Relationalize.apply()` automatically flattens deeply nested JSON structs into `dot.separated` columns and extracts nested arrays into separate child tables joined by generated array index keys—saving hours of manual `explode()` boilerplate when loading nested API dumps into Redshift or RDS.

---

### Q10: How does Glue `groupingEnabled` (file grouping) solve the Small Files Problem on S3 reads?
**Answer**:
Setting `groupFiles="inPartition"` and `groupSize` (e.g., 128 MB) in `create_dynamic_frame.from_options()` combines thousands of tiny 50 KB JSON/CSV S3 objects into logical Spark input splits before creating tasks, slashing task scheduling overhead and S3 API throttling.

---

### Q11: Compare AWS Glue 4.0 vs. Glue Flex vs. Glue Streaming vs. Glue Ray.
**Answer**:
- **Glue 4.0 (Spark 3.3+):** Standard low-latency serverless Spark ETL with native Delta/Iceberg/Hudi support.
- **Glue Flex:** Uses spare AWS compute capacity for non-urgent batch jobs (up to ~35% cheaper, flexible start/SLA).
- **Glue Streaming:** Continuous Spark Structured Streaming reading Kinesis/Kafka.
- **Glue for Ray:** Distributed Python compute for Pandas/ML workloads that don't fit JVM Spark.

---

### Q12: How do you enable Pushdown Predicates in AWS Glue when reading partitioned S3 tables from the Glue Catalog?
**Answer**:
Pass `push_down_predicate="year == '2026' and month == '11'"` inside `create_dynamic_frame.from_catalog()`. Unlike a late Spark `.filter()`, this filters S3 partitions at the Glue Data Catalog metadata level before listing or downloading any Parquet files.

---

### Q13: How do you use Apache Iceberg or Delta Lake natively inside AWS Glue 4.0+?
**Answer**:
Pass `--datalake-formats=iceberg,delta` and corresponding Spark extensions (`IcebergSparkSessionExtensions` / `DeltaSparkSessionExtension`) in Glue Job Parameters, allowing serverless Glue jobs to perform ACID `MERGE INTO`, Time Travel, and compaction directly on S3.

---

### Q14: What is AWS Glue Schema Registry, and how does it compare to Confluent Schema Registry?
**Answer**:
AWS Glue Schema Registry is a free, serverless registry for Avro, JSON Schema, and Protobuf integrated with Kinesis, MSK (Kafka), Lambda, and Glue Streaming. Like Confluent Schema Registry, it enforces compatibility rules (`BACKWARD`, `FORWARD`, `FULL`) and embeds a schema version UUID in message headers.

---

### Q15: How do you optimize JDBC reads from RDS/PostgreSQL inside AWS Glue without overloading the source DB?
**Answer**:
Parallelize reads safely by setting `hashfield` (or `partitionColumn`, `lowerBound`, `upperBound`, `numPartitions` on an indexed numeric/date column) and `fetchsize` (e.g., 10,000), while capping `numPartitions` (e.g., 4–8) and running against a Read Replica so OLTP traffic isn't starved.

---

### Q16: How do AWS Glue Python Shell jobs differ from Glue Spark ETL jobs?
**Answer**:
Python Shell jobs run on a single lightweight container (0.0625 or 1 DPU) with ~1–16 GB RAM and start in seconds—ideal for lightweight REST API orchestration, S3 metadata checks, DuckDB/Polars transforms on < 2 GB data, or triggering Redshift `COPY` / SQL stored procedures at a fraction of Spark DPU cost.

---

### Q17: How do you monitor DPU utilization and enable Auto Scaling in AWS Glue?
**Answer**:
Enable **Glue Auto Scaling** (`--enable-auto-scaling=true`) with a `MaxCapacity` cap so Spark dynamically adds executors during heavy shuffles and releases idle workers during narrow stages, and inspect CloudWatch Metrics (`glue.driver.ExecutorAllocationManager.*`) + Spark UI to detect over-provisioned DPUs.

---

### Q18: How do you secure sensitive credentials inside AWS Glue ETL scripts?
**Answer**:
Store database passwords and API tokens in **AWS Secrets Manager**, attach IAM `secretsmanager:GetSecretValue` permission to the Glue Job's IAM Role, and fetch credentials at runtime via `boto3` or Glue Connections—never hardcode secrets in S3 scripts or plaintext job arguments.

---

### Q19: How do you test AWS Glue PySpark scripts locally before pushing to AWS?
**Answer**:
Use the official `amazon/aws-glue-libs` Docker image (or local PySpark with mocked `GlueContext` / `pytest` fixtures) to validate transformation logic, `DynamicFrame` conversions, and DQDL rules in CI/CD before deploying scripts to S3 via Terraform/GitHub Actions.

---

### Q20: What causes `Command failed with exit code 1` / S3 `AccessDenied` or OOM in Glue, and how do you debug it?
**Answer**:
Inspect the CloudWatch `/aws-glue/jobs/error` log group (separate from `output`), verify the Glue IAM Role covers both S3 bucket/prefix AND KMS key `kms:Decrypt`/`kms:GenerateDataKey` permissions, and enable **Continuous Logging** + **Spark UI logs to S3** to inspect executor heap OOMs.
