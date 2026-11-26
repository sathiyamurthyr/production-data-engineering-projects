# Technical Design Decisions

This document details the architectural and engineering design decisions implemented in Project 16.

---

## 1. Compute Paradigm: Amazon EMR (EC2) vs EMR Serverless

We evaluated three execution runtimes: EMR on EC2, EMR on EKS, and EMR Serverless.

```
       Compute Options Evaluation
 ┌───────────────────┬────────────────────────────────────────────────────────┐
 │ Option            │ Decision Drivers                                       │
 ├───────────────────┼────────────────────────────────────────────────────────┤
 │ EMR on EC2        │ SELECTED for long-running, customized, high-throughput │
 │                   │ batch operations where fine-grained YARN tuning is     │
 │                   │ required and instances must be warmed up.              │
 ├───────────────────┼────────────────────────────────────────────────────────┤
 │ EMR Serverless    │ SELECTED for transient ETL pipelines (triggered by     │
 │                   │ Airflow/boto3) to eliminate cluster cold starts, role  │
 │                   │ management, and idle node billing.                     │
 ├───────────────────┼────────────────────────────────────────────────────────┤
 │ EMR on EKS        │ REJECTED due to heavy operational overhead of managing │
 │                   │ Kubernetes nodes, namespaces, and cluster autoscalers. │
 └───────────────────┴────────────────────────────────────────────────────────┘
```

**Decision:** We implemented design patterns for **both** paradigms:
- **EMR on EC2** via [cluster_config.py](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/src/cluster_config.py) for persistent or high-scale workloads requiring heavy custom bootstrap packages.
- **EMR Serverless** via [emr_serverless.py](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/src/emr_serverless.py) for transient, event-driven pipelines.

---

## 2. Cluster Topology: Instance Fleets vs. Instance Groups

EMR offers two configuration models for provisioning EC2 instances:

| Feature | Instance Groups | Instance Fleets (Selected) |
| :--- | :--- | :--- |
| **Resilience** | Tied to a single instance type. If AWS runs out of Spot capacity for that type, the cluster fails. | Allows specifying up to 30 instance types per fleet. AWS automatically selects active capacity. |
| **Bidding Strategy** | Single price point configuration per group. | Supports allocation strategies (e.g., Capacity-Optimized) across multiple instance sizes. |
| **Storage (EBS)** | Configured identically per group. | Dynamic mapping per instance configuration type. |

**Decision:** We utilized **Instance Fleets** in [configs/emr_cluster_config.json](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/configs/emr_cluster_config.json). It provides deep spot pool diversification, ensuring that if `r5.xlarge` Spot capacity is restricted, EMR seamlessly provisions `m5.xlarge` or `c5.2xlarge` instead, maintaining pipeline SLA.

---

## 3. Metadata Persistence: AWS Glue Data Catalog

When EMR clusters terminate, the local Hive Metastore (stored on the master node in Derby or MySQL) is destroyed, causing data schema metadata loss.

**Decision:** We integrated Spark with the **AWS Glue Data Catalog** as the external metastore (configured in [hive_on_emr.py](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/src/hive_on_emr.py)). 
- **Benefits**:
  - Eliminates the need to maintain self-hosted metastore databases (e.g. PostgreSQL RDS).
  - Schema definitions and partitions are persisted permanently.
  - Out-of-the-box integration with Athena, Redshift Spectrum, and QuickSight.

---

## 4. Bootstrapping vs. Runtime Installation

Installing Python libraries at runtime within Spark code (e.g. `spark.pip.install`) causes executor nodes to fetch packages concurrently, leading to rate limits, execution delays, and network overhead.

**Decision:** We implemented custom **Bootstrap Actions** ([install_dependencies.sh](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/configs/bootstrap_actions/install_dependencies.sh)). The script runs during instance provisioning before the Hadoop/Spark daemons initialize, ensuring all dependencies are compiled, cached locally, and standard across all primary, core, and task nodes.

---

## 5. Output Committer: EmrOptimizedSparkSqlParquetOutputCommitter

Standard Hadoop output committers write files to temporary directories (`_temporary/`) and rename them recursively upon task completion. In object stores like S3, "rename" is implemented as a copy-then-delete action, which is extremely expensive for large datasets.

**Decision:** We configured the **EMR-Optimized Parquet Committer** in [s3_data_patterns.py](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/src/s3_data_patterns.py). This writes files directly to their final S3 destinations during task execution, skipping the staging/renaming step and accelerating write performance by up to 40%.

---

## 6. Output Partitioning and File Sizing (128MB to 512MB)

Having many small files (e.g., < 10MB) in S3 degrades downstream query engines (Athena, Snowflake) due to extensive GET requests and metadata listing limits. Conversely, having single multi-gigabyte files limits read parallelism.

**Decision:** We designed a dynamic partition scaling utility in [s3_data_patterns.py](file:///d:/engineering-projects/production-data-engineering-projects/projects/16_emr/src/s3_data_patterns.py#L42) to estimate total data volume and automatically `repartition`/`coalesce` data to write Parquet files targeting **128MB - 256MB** each.
