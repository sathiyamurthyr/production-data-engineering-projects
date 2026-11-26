# Amazon EMR Interview Questions & Answers

This document lists key data engineering interview questions focused on Amazon EMR, Spark execution, and data catalog integrations.

---

### Q1: Explain the differences between Primary, Core, and Task nodes in an EMR Cluster. Which node type is best suited for Spot instances and why?
**Answer:**
* **Primary (Master) Node**: Coordinates the cluster, executes the Spark Driver, and runs the YARN ResourceManager and HDFS NameNode. It must remain active for the cluster's lifetime.
* **Core Nodes**: Run YARN NodeManagers and HDFS DataNode daemons. They participate in computing and store data within HDFS.
* **Task Nodes**: Run YARN NodeManagers only. They handle distributed processing (executors) but do **not** store HDFS blocks.
* **Spot Suitability**: **Task Nodes** are ideal for Spot instances. Since they don't store HDFS data, their sudden termination (spot reclamation) does not degrade HDFS storage health or cause data block corruption. Spark simply retries the lost tasks on surviving nodes. Core nodes should stay on On-Demand instances to prevent HDFS data loss.

---

### Q2: What is EMRFS and how does it differ from standard HDFS? What are the benefits of using EMRFS?
**Answer:**
* **EMRFS (EMR File System)** is an implementation of HDFS that allows EMR clusters to read and write data directly from and to Amazon S3.
* **Comparison**:
  - **Standard HDFS** stores data locally on the EC2 instances' ephemeral or EBS storage. If the cluster terminates, the data is lost.
  - **EMRFS** persists data permanently in S3. This decouples storage and compute: you can shut down the EMR compute cluster completely and pay only for S3 storage.
* **Key Benefits**:
  - Significant cost reductions (S3 is cheaper than EBS).
  - Scalability: scale storage in S3 and compute in EMR independently.
  - Data shareability: S3 data can be read concurrently by other AWS services (Glue, Athena, Redshift, SageMaker).

---

### Q3: Describe how you size Spark executors on an EMR cluster. Show the calculation for a node with 16 vCores and 128 GB RAM.
**Answer:**
To size executors efficiently, follow this standard data engineering formula:
1. **System Overhead**: Reserve 1 vCore and 8 GB RAM per node for YARN and OS daemons, leaving 15 vCores and 120 GB RAM.
2. **Cores per Executor**: Target **5 cores per executor** to balance thread execution and write performance:
   $$\text{Executors per Node} = \frac{15 \text{ Cores}}{5 \text{ Cores/Executor}} = 3 \text{ Executors}$$
3. **Memory per Executor**: Distribute remaining RAM:
   $$\text{Total Memory per Executor} = \frac{120 \text{ GB}}{3} = 40 \text{ GB}$$
4. **Overhead Allocation**: Subtract 10% for Spark memory overhead:
   $$\text{Overhead} = 40 \text{ GB} \times 0.10 = 4 \text{ GB}$$
   $$\text{Executor Heap Memory} = 40 \text{ GB} - 4 \text{ GB} = 36 \text{ GB}$$
5. **Resulting Configurations**:
   `--executor-cores 5 --executor-memory 36g --conf spark.executor.memoryOverhead=4096m`

---

### Q4: How do you configure PySpark on EMR to connect to the AWS Glue Data Catalog as an external Hive Metastore?
**Answer:**
On EMR, you configure Spark to bind its catalog to Glue by setting the Glue client factory class in `spark-defaults` or programmatically during SparkSession creation:
```python
spark = (
    SparkSession.builder
    .appName("GlueCatalogIntegration")
    .enableHiveSupport()
    .config("hive.metastore.client.factory.class", "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory")
    .config("spark.sql.hive.metastore.sharedPrefixes", "com.amazonaws.services.securitytoken,com.amazonaws.services.glue,com.amazonaws.glue")
    .getOrCreate()
)
```
This maps Spark SQL commands (`CREATE TABLE`, `SELECT`, etc.) directly to tables registered in the AWS Glue Data Catalog, allowing schema persistence across ephemeral cluster runs.

---

### Q5: What is the difference between EMR Instance Groups and Instance Fleets? Why are Fleets preferred for Spot instances?
**Answer:**
* **Instance Groups**: You configure a single instance type for master, core, and task groups. If you request 20 `r5.xlarge` Spot instances and AWS has insufficient capacity for that specific type, the cluster allocation fails or hangs.
* **Instance Fleets**: You can define up to **30 different instance types** per fleet (e.g., `r5.xlarge`, `m5.xlarge`, `c5.2xlarge`) and set a target capacity unit.
* **Why Fleets are Preferred**: Fleets diversify your Spot request. If AWS runs out of `r5.xlarge` Spot capacity, EMR automatically fulfills the remaining capacity using another type from your fleet configurations (like `m5.xlarge`). This significantly improves Spot acquisition success.

---

### Q6: What is the "small files problem" in Spark and S3, and how do you resolve it programmatically in your code?
**Answer:**
* **Problem**: Spark parallel tasks write files concurrently. If a DataFrame has 200 partitions but only a few rows, writing to S3 results in 200 tiny files. This creates high HTTP GET/PUT call volumes, overloading S3 and slowing down downstream querying engines like Athena.
* **Resolution**:
  - Calculate target files based on record size and data volume (aiming for 128MB–256MB per Parquet file).
  - Use `coalesce(N)` (if reducing partitions without a full shuffle) or `repartition(N, columns)` (to distribute rows evenly by partition columns):
    ```python
    # Calculate N based on estimated total bytes / 128MB
    df_repartitioned = df.repartition(num_files, "country")
    df_repartitioned.write.partitionBy("country").parquet("s3://...")
    ```

---

### Q7: Explain EMR Serverless. When would you choose EMR Serverless over EMR on EC2?
**Answer:**
* **EMR Serverless** is a serverless execution engine for EMR. Instead of provisioning and maintaining EC2 instances, security groups, and scaling rules, you define an application (Spark/Hive) and submit job runs.
* **Choose EMR Serverless when**:
  - Workloads are transient, variable, or event-driven.
  - You want to eliminate EC2 infrastructure management and idle cluster costs.
  - You want fast startup times (EMR Serverless starts containers in seconds, compared to 5–10 minutes for EC2 cluster provisioning).
* **Choose EMR on EC2 when**:
  - You need deep OS-level access, custom system libraries, or complex third-party agents running on the nodes.
  - You run highly tuned, long-running, multi-tenant interactive Spark/Presto clusters (e.g. 24/7).

---

### Q8: What is "Graceful Decommissioning" in EMR, and how does it prevent data pipeline failure?
**Answer:**
* When EMR scales down (manually or via Auto Scaling / Managed Scaling), EC2 nodes are terminated. If a node running active Spark tasks or holding intermediate shuffle files is killed abruptly, the Spark job fails.
* **Graceful Decommissioning** (configured via `ScaleDownBehavior: TERMINATE_AT_TASK_COMPLETION`) forces YARN to stop scheduling new containers on decommissioning nodes but allows active containers to complete their tasks and transfer shuffle files to surviving nodes before the EC2 instance is terminated.

---

### Q9: What is the function of the EMRFS Direct Committer in Spark writes to S3?
**Answer:**
* Traditional Hadoop committers use a two-phase commit: write files to `_temporary/`, then rename directories when task completes. S3 is an object store, not a filesystem, so "rename" requires copying the object and deleting the old one.
* EMR provides the `EmrOptimizedSparkSqlParquetOutputCommitter` which writes tasks **directly** to their final S3 destinations, bypassing temporary staging and renaming, which increases Parquet write performance on S3 by up to 40%.

---

### Q10: How do you access Spark UI and debugging logs for steps running on Amazon EMR?
**Answer:**
1. **CloudWatch Logs**: EMR redirects stdout/stderr steps output to CloudWatch if log integration is enabled.
2. **S3 Log Directory**: EMR syncs YARN container and step logs to the configured S3 log URI (typically every 5 minutes).
3. **Spark History Server**: Accessible via the EMR console (using EMR Spark History Server integration) or by setting up an SSH tunnel to the Primary Node (port 18080).
4. **YARN ResourceManager UI**: Access via SSH tunnel on port 8088 to track running application memory allocation.


---

### Q11: How do you optimize EMR S3 listing and read performance on tables with hundreds of thousands of files?
**Answer:**
Enable **EMRFS S3 Select** where appropriate, use Parquet/ORC with explicit partition pruning, avoid `spark.read.parquet("s3://bucket/*/*")` globbing by registering partitions in the **Glue Data Catalog**, and compact tiny files into 128–256 MB Parquet objects.

---

### Q12: Compare EMR Managed Scaling vs. Legacy EMR Auto Scaling policies.
**Answer:**
Legacy Auto Scaling required manually writing CloudWatch alarm rules on YARN containers/memory pending thresholds. **EMR Managed Scaling** uses a built-in feedback loop tracking YARN demand, HDFS capacity, and Spot availability to resize Core and Task nodes automatically within min/max bounds every few seconds.

---

### Q13: What are EMR Bootstrap Actions vs. EMR Configurations (`classifications`)?
**Answer:**
- **EMR Configurations (`classifications`):** Declarative JSON settings applied to Hadoop/Spark/Hive config files (`spark-defaults`, `yarn-site`, `hive-site`) cleanly at provisioning time.
- **Bootstrap Actions:** Custom shell scripts executed on every EC2 node **before** Hadoop/Spark daemons start—used to install OS packages, custom Python wheels, or monitoring agents.

---

### Q14: How do you decide between transient (ephemeral) EMR clusters vs. a long-running shared EMR cluster?
**Answer:**
- **Transient (per-job) EMR clusters:** Orchestrated by Airflow/Step Functions (`create -> add_steps -> terminate`), providing strict workload isolation, zero idle cost, and independent Spark versions per pipeline.
- **Long-running clusters:** Better for interactive multi-user Zeppelin/Jupyter analytics or sub-minute jobs where 5-minute EC2 boot latency is unacceptable (though **EMR Serverless** or **EMR on EKS** often replaces long-running EC2 clusters today).

---

### Q15: How do you run Apache Iceberg or Delta Lake on Amazon EMR?
**Answer:**
On EMR 6.5+/7.x, include Iceberg or Delta libraries via EMR release classifications (`iceberg` / `delta` Spark SQL extensions) and bind the catalog to `GlueCatalog` (`org.apache.iceberg.aws.glue.GlueCatalog`) so ACID tables on S3 are immediately queryable from Athena, Redshift Spectrum, and Trino.

---

### Q16: Explain EMR on EKS and when it is better than EMR on EC2.
**Answer:**
EMR on EKS runs EMR-optimized Spark runtime containers directly on an existing **Amazon EKS (Kubernetes)** cluster. Choose it when your platform already runs Kubernetes, you need fast pod startup (~10–30s vs EC2 boot), or you want mixed Spark versions and strict container dependency isolation on shared compute nodes.

---

### Q17: How do you prevent YARN from killing Python/PyArrow executors when running memory-heavy Pandas UDFs on EMR?
**Answer:**
Pandas/PyArrow runs **outside the JVM heap** in off-heap Python worker processes, yet YARN kills containers exceeding total physical memory (`heap + overhead`). Increase `spark.executor.memoryOverhead` (and `spark.executor.pyspark.memory` if enforced) so YARN allocates enough off-heap headroom.

---

### Q18: How do you handle Spot Instance interruptions smoothly for long-running EMR Spark jobs?
**Answer:**
Use **Instance Fleets** with diversified instance types + `AllocationStrategy: capacity-optimized`, keep Primary and Core nodes On-Demand (or only Core with Managed Scaling), put Task nodes on Spot, and enable **Graceful Decommissioning** + Spark checkpointing for multi-hour stages.

---

### Q19: How do you secure data at rest and in transit on Amazon EMR?
**Answer:**
Attach an **EMR Security Configuration** enabling SSE-S3 / SSE-KMS encryption for EMRFS, LUKS encryption for local EBS/NVMe shuffle disks, TLS encryption for in-transit Spark/YARN shuffle (`spark.authenticate` + TLS), and IAM Roles for EMRFS (`SecurityConfiguration` / Lake Formation integration).

---

### Q20: What is `maximizeResourceAllocation` in EMR Spark configurations, and when should you disable it?
**Answer:**
Setting `"maximizeResourceAllocation": "true"` in `spark` classification automatically configures a single giant executor per Core/Task node using all available YARN vCores and RAM. Disable it when running concurrent Spark steps on the same cluster or when single-executor JVM heaps exceed ~48–64 GB (which triggers long GC pauses and poor HDFS/S3 I/O concurrency).
