# 03. PySpark & Spark Internals — Interview Q&A

---

## Part A: PySpark Coding & DataFrame Scenarios

### Q1: Pivot a DataFrame in PySpark (`City | month | subscribers` → `City | Jan | Feb | March`).
**Answer:**
```python
from pyspark.sql import functions as F

pivoted_df = (
    df.groupBy("City")
    .pivot("month", ["Jan", "Feb", "March"])  # Explicit list avoids an extra distinct scan
    .sum("subscribers")
)
```
> **Performance Tip:** Always pass the known pivot values list to `.pivot("col", [...])` in production so Spark skips an extra job to discover distinct pivot values.

---

### Q2: Write a PySpark RDD Word Count returning the Top 10 most frequent words.
**Corrected Code (fixing `lamda` → `lambda` and assigning `out`):**
```python
rdd = sc.textFile("/user/spark/words.txt")

top_10 = (
    rdd.flatMap(lambda line: line.lower().split(" "))
    .filter(lambda word: word != "")
    .map(lambda word: (word, 1))
    .reduceByKey(lambda a, b: a + b)
    .map(lambda pair: (pair[1], pair[0]))   # Swap to (count, word)
    .sortByKey(ascending=False)
    .take(10)
)

for count, word in top_10:
    print(f"{word}\t:\t{count}")
```

---

### Q3: How do you capture the source filename for every row read by Spark?
**Answer:** Use `input_file_name()` (or `_metadata.file_path` in Spark 3.3+ / Databricks):
```python
from pyspark.sql.functions import input_file_name

df = df.withColumn("filename", input_file_name())
```

---

### Q4: Calculate a Moving Average of Salary per Role (previous, current, next row).
**Answer:**
```python
from pyspark.sql import Window
from pyspark.sql import functions as F

window_spec = Window.partitionBy("Role").orderBy("EmpId").rowsBetween(-1, 1)
mov_avg_df = sample_data.withColumn("movingAverage", F.avg("Salary").over(window_spec))
```
- `rowsBetween(-1, 1)` includes previous (`-1`), current (`0`), and next (`1`) rows inside each `Role` partition.

---

### Q5: Convert `(cust_id, type, value)` rows into a map/dictionary column per customer (e.g., `{primary: 'cancer', secondary: 'blood test'}`).
**Answer:** Avoid slow Python UDFs (`converdict`)—use native Spark SQL `create_map` + `collect_list` + `map_from_entries`:
```python
from pyspark.sql import functions as F

result_df = (
    df.groupBy("cust_id")
    .agg(F.map_from_entries(F.collect_list(F.struct("type", "value"))).alias("testing"))
)
```
*(For a single row's two columns directly: `F.create_map(F.col("type"), F.col("value"))`.)*

---

### Q6: Explode an array column (`[a, b, c]`), filter array length > 5, and convert epoch long timestamps.
**Answer:**
```python
from pyspark.sql import functions as F

# 1. Explode array elements into individual rows
exploded_df = df.select(F.col("id"), F.explode(F.col("list_col")).alias("item"))

# 2. Filter strings longer than 5 chars (or array size > 5 with F.size())
long_items_df = exploded_df.filter(F.length(F.col("item")) > 5)

# 3. Convert Unix epoch (seconds or ms) to Timestamp
ts_df = df.withColumn("event_ts", F.from_unixtime(F.col("epoch_sec")).cast("timestamp"))
```

---

### Q7: Replace `NULL` values in a Spark DataFrame (`(id1, 50), (id2, null)` → `0` or `"Unknown"`).
**Answer:**
```python
# Fill NULLs across specific columns or types
cleaned_df = df.na.fill({"col2": 0})          # Numeric default
cleaned_df = df.fillna(0, subset=["col2"])    # Equivalent
```

---

### Q8: How do you handle malformed / corrupt records in Spark (`CSV` / `JSON`)?
**Answer:**
Use `PERMISSIVE` mode (default) paired with `columnNameOfCorruptRecord` or `badRecordsPath` to quarantine bad rows without failing valid rows:
```python
df = (
    spark.read.option("mode", "PERMISSIVE")
    .option("columnNameOfCorruptRecord", "_corrupt_record")
    .schema(expected_schema)
    .json("path/to/events.json")
)
bad_df = df.filter(F.col("_corrupt_record").isNotNull())
good_df = df.filter(F.col("_corrupt_record").isNull()).drop("_corrupt_record")
```

---

### Q9: PySpark Join Types Reference
**Answer:**
```python
df1.join(df2, df1["letter"] == df2["letter"], "inner")       # Matching rows only
df1.join(df2, "letter", "left")                              # All left + matched right
df1.join(df2, "letter", "right")                             # All right + matched left
df1.join(df2, "letter", "outer")                             # Full outer (nulls on unmatched)
df1.join(df2, "letter", "left_semi")                         # Left rows WITH match (left cols only)
df1.join(df2, "letter", "left_anti")                         # Left rows WITHOUT match
df1.crossJoin(df2)                                           # Cartesian product
df.alias("a").join(df.alias("b"), F.col("a.id") < F.col("b.id"))  # Self join
```

---

## Part B: Spark Internals, Partitioning & Tuning

### Q10: `coalesce()` vs `repartition()` — when do you use each?
**Answer:**
| Feature | `coalesce(N)` | `repartition(N)` |
|---|---|---|
| **Direction** | **Decrease** partitions only | **Increase or decrease** partitions |
| **Network Shuffle** | Avoids full shuffle (merges local partitions) | Triggers **full network shuffle** |
| **Partition Balance** | Can produce **unequal-sized** partitions | Produces **evenly sized** partitions |
| **Best Use Case** | Reducing files before `.write` (e.g., `coalesce(1)` for small outputs) | Increasing parallelism or balancing before `join` / `groupBy` |

---

### Q11: Explain Spark Architecture, `SparkContext` vs `SparkSession`, and Client vs Cluster Mode.
**Answer:**
- **Execution Flow:** User code builds transformations into a **Logical DAG** → Catalyst optimizes it into a **Physical Plan** divided into **Stages** (split at wide shuffles) → each Stage runs parallel **Tasks** (1 task per partition) on **Executors** managed by the Cluster Manager (YARN/K8s) and coordinated by the **Driver**.
- **`SparkContext` vs `SparkSession`:** `SparkContext` (1.x) is the low-level entry point for RDDs; `SparkSession` (2.0+) unifies `SparkContext`, `SQLContext`, and `HiveContext` (`spark.sparkContext` accesses the underlying context).
- **Cluster Mode vs Client Mode:**
  - **Cluster Mode:** Driver runs inside a worker node in the cluster (production scheduled jobs; client can disconnect).
  - **Client Mode:** Driver runs on the submitting gateway/edge machine (interactive debugging; close to cluster).

---

### Q12: How do you size Executors, Cores, and Memory for a 100 GB Spark job?
**Answer:**
1. **Partitions:** Default block/partition size = `128 MB`.
   $$100 \text{ GB} = 102,400 \text{ MB} \implies \frac{102,400}{128} = 800 \text{ partitions (cores needed for full parallelism)}$$
2. **Executors:** Target **4–5 cores per executor** (avoids HDFS/S3 I/O contention and giant GC heaps). At 4 cores/executor → $800 / 4 = 200$ executors (or scale down by 2x–4x for budget with longer runtime).
3. **Executor Memory:** Rule of thumb: ~4x partition size per core (~512 MB–4 GB/core depending on shuffle/cache), plus **10% `spark.executor.memoryOverhead`**. (Example `spark-submit`: `--num-executors 29 --executor-cores 5 --executor-memory 18g --driver-memory 6g`).
4. **Driver Memory:** Keep modest (4–8 GB) unless calling `.collect()` (avoid `.collect()` on large data!).

---

### Q13: Compare `reduceByKey()` vs `groupByKey()`, and `sortByKey()`.
**Answer:**
- **`reduceByKey()`** performs **map-side combining** on each partition *before* shuffling over the network—far faster and lower memory than `groupByKey()`.
- **`groupByKey()`** shuffles **all** raw key-value pairs across the network, risking executor OOM/disk spills.
- **`sortByKey()`** globally sorts `(K, V)` RDDs by key across partitions via range partitioning.

---

### Q14: What is RDD Lineage, and how does Spark recover lost partitions?
**Answer:**
Every RDD stores an immutable **lineage graph** of transformations (`map -> filter -> join`) from its source. If an executor crashes and loses a partition in memory, Spark replays only the lost partition's lineage dependencies from upstream data/shuffle files instead of replicating intermediate RAM blocks.

---

### Q15: When should you use `cache()` / `persist()` — **before** a Join or **after** a Join?
**Answer:**
- **Cache BEFORE a Join** when an input DataFrame is expensive to compute (e.g., multiple filters/aggregations) and is **reused in multiple downstream joins/branches**.
- **Cache AFTER a Join** when the joined result itself is reused across multiple downstream actions (e.g., writing to 3 separate Gold tables). Never cache a DataFrame that is only read once.

---

### Q16: Explain Broadcast Variables, Kryo Serialization, and Custom Partitioners.
**Answer:**
- **Broadcast Variables (`broadcast(df)`):** Ships a read-only small table (< 10–100 MB) once to each worker node, turning a shuffle join into a fast local hash lookup.
- **Kryo Serialization (`spark.serializer=org.apache.spark.serializer.KryoSerializer`):** Faster and more compact than Java serialization for RDD shuffles and custom classes.
- **Custom Partitioner:** On RDDs, `rdd.partitionBy(N, customPartitioner)` controls key placement to prevent skew or co-locate keys; on DataFrames, use `repartition(N, col)` or salting.

---

### Q17: Explain the Catalyst Optimizer and Parquet Metadata / Schema Storage.
**Answer:**
- **Catalyst Optimizer:** Transforms DataFrame/SQL plans through **Analysis** (catalog resolution) → **Logical Optimization** (predicate pushdown, constant folding, projection pruning) → **Physical Planning** (cost-based join choice) → **Whole-Stage CodeGen** (Tungsten Java bytecode).
- **Parquet Metadata & Schema:** Parquet is self-describing—the **Footer** at the end of every file stores the full schema, column encodings, and per-row-group **min/max statistics**, enabling Spark to skip reading irrelevant columns and row groups.

---

### Q18: What are all the tabs in the Spark UI, and how do you debug GC (Garbage Collection) issues?
**Answer:**
- **Spark UI Tabs:** `Jobs` (status & DAG visualization), `Stages` (tasks, duration, shuffle read/write), `Tasks` (per-task executor, duration, errors), `Storage` (cached RDD/DF memory & disk usage), `Executors` (cores, memory, **GC Time**, stderr/stdout logs), `SQL` (Catalyst physical plans), `Environment` (Spark configs/classpath), and `Streaming` / `Structured Streaming`.
- **Finding & Fixing GC Issues:**
  - Look at the **Executors Tab**: if `GC Time` exceeds ~10% of `Task Time`, executors are thrashing on heap.
  - **Fixes:** Reduce per-executor heap size (keep ≤ 32–48 GB, ~4–5 cores), switch from `collect()`/Python UDFs to native Catalyst ops, avoid `groupByKey()`, enable Kryo/off-heap (`spark.memory.offHeap.enabled=true`), or unpersist unused cached DataFrames.

---

### Q19: Compare Hive Partitioning vs. Spark Partitioning & Bucketing, and Speculative Execution.
**Answer:**
- **Hive/Disk Partitioning (`partitionBy`):** Physical folder layout on HDFS/S3 (`year=2026/month=11/`) for coarse query pruning.
- **Spark In-Memory Partitioning (`repartition`/`coalesce`):** Logical task parallelism inside executors.
- **Bucketing (`bucketBy(N, col)`):** Hash-distributes rows into $N$ fixed bucket files inside partitions so repeated joins/aggregations on `col` avoid shuffles.
- **Speculative Execution (`spark.speculation=true`):** Launches a duplicate attempt on another node when one task runs much slower than the stage median, taking whichever finishes first.
