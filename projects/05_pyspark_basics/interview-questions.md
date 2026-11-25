# Project 05 Interview Questions: PySpark Core & Distributed DataFrames

A curated compilation of 30 enterprise-grade PySpark Data Engineering interview questions with detailed, technical answers.

---

## Category 1: Architecture & Core Concepts

### Q1: What is the difference between SparkContext, SQLContext, and SparkSession?
**Answer**:
- **SparkContext**: The original entry point (Spark 1.x) for Spark Core functionality. Used to create RDDs, accumulators, and broadcast variables.
- **SQLContext**: Entry point (Spark 1.x) for Spark SQL and DataFrames.
- **SparkSession**: Introduced in Spark 2.0 as a unified entry point that subsumes SparkContext, SQLContext, and HiveContext. In PySpark 3.x, `spark.sparkContext` accesses the underlying core context.

### Q2: Explain Lazy Evaluation in PySpark and why it is beneficial.
**Answer**:
Transformations in PySpark (e.g. `map`, `filter`, `select`, `join`) are lazy — Spark builds a logical execution plan (DAG) instead of executing computation immediately. Execution is triggered only when an **Action** (e.g. `count()`, `show()`, `collect()`, `write`) is called.
*Benefits*:
1. Enables the Catalyst Optimizer to analyze the entire DAG, reordering operations, pushing down filters, and eliminating redundant computations.
2. Avoids unnecessary intermediate I/O passes over data.

### Q3: What is the difference between Narrow and Wide Transformations?
**Answer**:
- **Narrow Transformation**: Each input partition contributes to at most one output partition (e.g. `map()`, `filter()`, `withColumn()`, `select()`). No network shuffle is required; execution occurs pipelined within the same worker thread.
- **Wide Transformation**: Multiple input partitions contribute to an output partition (e.g. `groupBy()`, `join()`, `distinct()`, `repartition()`). Requires a **Shuffle** operation to transfer data across executor nodes over the network.

---

## Category 2: Execution Engine & Optimizations

### Q4: Explain how the Catalyst Query Optimizer works in PySpark.
**Answer**:
Catalyst converts high-level DataFrame code into optimized JVM bytecode through 4 key phases:
1. **Analysis**: Resolves table/column names and types against the Catalog.
2. **Logical Optimization**: Applies rule-based optimizations (constant folding, predicate pushdown, projection pruning).
3. **Physical Planning**: Generates multiple physical execution strategies and estimates cost to select the optimal physical plan.
4. **Code Generation**: Uses Whole-Stage Code Generation (Tungsten) to emit optimized Java bytecode.

### Q5: What is the difference between `repartition()` and `coalesce()`?
**Answer**:
- `repartition(N)`: Reshuffles all data across the cluster to construct $N$ evenly sized partitions. Can increase or decrease partition count. Triggers a full network shuffle.
- `coalesce(N)`: Decreases partition count by merging adjacent partitions on existing nodes without triggering a network shuffle. Cannot increase partition count.

### Q6: What is Adaptive Query Execution (AQE) in Spark 3.x?
**Answer**:
AQE re-optimizes query plans at runtime based on actual stage statistics collected during execution.
*Key Features*:
1. **Dynamic Coalescing**: Automatically merges small shuffle partitions into larger partitions.
2. **Dynamic Join Switch**: Converts Sort-Merge Join to Broadcast Hash Join if runtime dataset size falls below broadcast threshold.
3. **Dynamic Skew Join Optimization**: Automatically splits skewed shuffle partitions into smaller sub-partitions.

---

## Category 3: Joins & Skew Management

### Q7: Explain Broadcast Hash Join (BHJ) and its performance advantages.
**Answer**:
BHJ copies a small DataFrame (default <10 MB, configured via `spark.sql.autoBroadcastJoinThreshold`) to the memory of all worker executors.
*Advantage*: Eliminates the network shuffle of the large DataFrame entirely, replacing a costly $O(N + M)$ shuffle join with local hash lookups on worker nodes.

### Q8: How do you handle severe key skew during a join in PySpark?
**Answer**:
1. Enable AQE Skew Join (`spark.sql.adaptive.skewJoin.enabled=true`).
2. **Salting**: Append random salt integers (e.g. `0..K-1`) to the join key of the skewed table, and explode the lookup table with an array of `0..K-1` salt values. This distributes identical skewed keys across $K$ separate join tasks.
3. Filter out NULL or dummy keys prior to joining.

### Q9: What is the difference between `left_semi` and `left_anti` joins?
**Answer**:
- `left_semi`: Returns rows from the left DataFrame that have a match in the right DataFrame. Returns ONLY left DataFrame columns and deduplicates multiple right matches.
- `left_anti`: Returns rows from the left DataFrame that DO NOT have a match in the right DataFrame.

---

## Category 4: Memory Management & Tuning

### Q10: What is the difference between `cache()` and `persist()`?
**Answer**:
- `cache()`: Shorthand for `persist(StorageLevel.MEMORY_AND_DISK_DESER)` (or MEMORY_ONLY in Python).
- `persist()`: Allows specifying custom storage levels: `MEMORY_ONLY`, `MEMORY_AND_DISK`, `MEMORY_ONLY_SER`, `DISK_ONLY`, and replicated levels (e.g. `MEMORY_AND_DISK_2`).

### Q11: How do you diagnose and fix Executor Out-Of-Memory (OOM) errors?
**Answer**:
1. **Check for Data Skew**: Inspect Spark UI task execution times for long-tail stragglers.
2. **Increase Shuffle Partitions**: Set `spark.sql.shuffle.partitions` to a higher number to reduce data volume per partition.
3. **Increase Executor Memory / Overhead**: Adjust `--executor-memory` or `spark.executor.memoryOverhead`.
4. **Avoid Large Broadcasts**: If broadcast table exceeds executor memory, disable auto-broadcast or increase heap size.

---

## Category 5: Window Functions & Aggregations

### Q12: Explain the differences between `row_number()`, `rank()`, and `dense_rank()`.
**Answer**:
When ordering ties occur:
- `row_number()`: Assigns sequential integers without ties (1, 2, 3, 4, 5).
- `rank()`: Assigns identical rank for ties, skipping subsequent numbers (1, 2, 2, 4, 5).
- `dense_rank()`: Assigns identical rank for ties WITHOUT skipping numbers (1, 2, 2, 3, 4).

### Q13: What is the difference between `ROLLUP` and `CUBE` in PySpark aggregations?
**Answer**:
- `ROLLUP(A, B, C)`: Generates hierarchical sub-totals along the column hierarchy: `(A, B, C)`, `(A, B)`, `(A)`, `()`.
- `CUBE(A, B, C)`: Generates all $2^N$ combinations of dimensions: `(A, B, C)`, `(A, B)`, `(A, C)`, `(B, C)`, `(A)`, `(B)`, `(C)`, `()`.

---

## Category 6: UDFs & PyArrow Integration

### Q14: Why are standard Python UDFs slow in PySpark, and how do Pandas UDFs solve this?
**Answer**:
Standard Python UDFs require row-by-row serialization from JVM to Python processes via IPC sockets, incurring massive serialization overhead and blocking Catalyst optimizations.
**Pandas UDFs** use Apache Arrow's shared in-memory columnar format, transferring batches of data with zero-copy deserialization directly to Pandas/NumPy C-extensions, executing up to 100x faster.


---

## Category 7: Execution, Partitioning & Storage Formats

### Q15: What is the difference between `spark.sql.files.maxPartitionBytes` and `spark.sql.shuffle.partitions`?
**Answer**:
- `spark.sql.files.maxPartitionBytes` (default 128 MB) controls how large input split partitions are when **reading** files from storage (Stage 1).
- `spark.sql.shuffle.partitions` (default 200) controls the number of partitions created **after a wide shuffle** (`groupBy`, `join`).

### Q16: Why is Parquet + Snappy the default analytical storage format in PySpark over CSV or JSON?
**Answer**:
Parquet is columnar, self-describing (embedded schema), supports dictionary/RLE encoding, and enables **projection pruning** (read only queried columns) and **predicate pushdown** (skip row groups using min/max stats). Snappy offers fast compression/decompression CPU speeds ideal for Spark executors.

### Q17: How does Predicate Pushdown work in PySpark, and what breaks it?
**Answer**:
Predicate pushdown moves `filter()` conditions down into the Parquet/ORC/JDBC reader so irrelevant row groups or DB pages are never read into memory. Wrapping a filter column in a Python UDF or type-casting expression (e.g., `F.year(col) == 2026` on a string date) can prevent pushdown unless rewritten as range predicates.

### Q18: Explain `spark.sql.autoBroadcastJoinThreshold` and when to disable or raise it.
**Answer**:
It sets the max byte size (default 10 MB) for a table to be broadcast automatically to all executors. Raise it (e.g., to 50–100 MB) when executors have ample memory and dimension joins dominate; set it to `-1` if Spark's size estimator miscalculates a compressed Parquet table's in-memory size and causes driver/executor OOMs.

### Q19: What is the difference between `collect()`, `take(N)`, and `toLocalIterator()`?
**Answer**:
- `collect()` pulls **every partition** into Driver RAM—dangerous on large datasets (Driver OOM).
- `take(N)` pulls only the first $N$ rows sequentially.
- `toLocalIterator()` streams one partition at a time to the Driver, bounding Driver memory to a single partition.

### Q20: How do you avoid Python UDFs altogether using Spark SQL built-in higher-order functions?
**Answer**:
Use native Catalyst functions (`F.transform`, `F.filter`, `F.aggregate`, `F.when`, `F.regexp_extract`, `F.expr`) which execute inside JVM/Tungsten without JVM-to-Python serialization overhead.

### Q21: Explain Dynamic Partition Overwrite mode in Spark.
**Answer**:
Setting `spark.sql.sources.partitionOverwriteMode=dynamic` ensures `.write.mode("overwrite").partitionBy("dt")` overwrites **only the date partitions present in the current DataFrame**, rather than wiping the entire target table directory.

### Q22: What causes `FetchFailedException` during a Spark shuffle, and how do you fix it?
**Answer**:
An executor died (often OOM or Spot termination) or network timeout occurred while downstream tasks fetched shuffle blocks. Fix by fixing data skew, increasing `spark.executor.memoryOverhead`, enabling External Shuffle Service (`spark.shuffle.service.enabled=true`), or raising `spark.network.timeout`.

### Q23: What is the difference between `spark.memory.fraction` and `spark.memory.storageFraction`?
**Answer**:
In Spark's Unified Memory Manager, `spark.memory.fraction` (default 0.6) reserves 60% of JVM heap for Execution + Storage combined (40% remains for user objects/metadata). `spark.memory.storageFraction` (default 0.5) sets the immune portion of that unified pool for cached data before Execution can evict Storage blocks.

### Q24: How do you deduplicate massive streaming/batch datasets deterministically in PySpark?
**Answer**:
Use a Window function (`F.row_number().over(Window.partitionBy("pk").orderBy(F.col("updated_at").desc())) == 1`) instead of `dropDuplicates()` when you need deterministic "latest record wins" tie-breaking.

### Q25: Explain how `explode()` vs `posexplode()` work on nested arrays/structs, and their null behavior.
**Answer**:
`explode()` flattens each array element into its own row and drops `NULL`/empty arrays; `explode_outer()` preserves parent rows with `NULL`. `posexplode()` additionally outputs the zero-based array index (`pos`) alongside each element.

### Q26: How does Speculative Execution (`spark.speculation=true`) mitigate straggler tasks?
**Answer**:
If one task runs dramatically slower than the median task in a stage (e.g., degraded host disk/CPU), Spark launches a duplicate speculative attempt on another executor and takes whichever finishes first—useful on shared clusters, though unsafe with non-idempotent external sinks.

### Q27: What is the Small Files Problem in PySpark, and how do you fix it before writing?
**Answer**:
Writing thousands of partitions with a few KB each creates huge NameNode/S3 listing overhead. Fix via AQE partition coalescing, `.coalesce(N)` / `.repartition(N, "partition_col")`, or `maxRecordsPerFile` option on `.write`.

### Q28: How do you pass configuration and secrets safely to `spark-submit` jobs?
**Answer**:
Pass non-sensitive runtime flags via `--conf` or mounted YAML configs (`--files`), and retrieve secrets dynamically inside the driver/job from AWS Secrets Manager, Azure Key Vault, or Databricks Secret Scopes—never in plaintext `spark-submit` CLI flags (which appear in Spark UI Environment tab).

### Q29: Compare `DataFrame.cache()` vs persisting intermediate Parquet checkpoints for complex multi-branch DAGs.
**Answer**:
`cache()` keeps lineage in executor memory and recomputes lost partitions on executor failure; writing an intermediate Parquet/Delta staging table breaks massive DAG lineage (preventing Catalyst/Driver stack issues) and provides crash recovery at the cost of disk I/O.

### Q30: How do you unit-test PySpark transformations fast in CI without a multi-node cluster?
**Answer**:
Create a session-scoped `local[2]` `SparkSession` pytest fixture with `spark.sql.shuffle.partitions=2` and `spark.ui.enabled=false`, feed small deterministic DataFrames, and compare outputs with sorted rows or `assertDataFrameEqual`.
