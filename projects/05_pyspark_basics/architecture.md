# Project 05 Architecture: PySpark Core & Distributed DataFrames

## 1. System Architecture Overview

PySpark operates on a master-worker architecture comprising a single **Driver Program** and multiple distributed **Executors** managed by a Cluster Manager (Local, YARN, Kubernetes, or Databricks Runtime).

```mermaid
flowchart TD
    subgraph Driver ["Spark Driver Node"]
        SC["SparkContext / SparkSession"]
        DAG["DAGScheduler"]
        TS["TaskScheduler"]
        CATALOG["Session Catalog / Metastore"]
        
        SC --> DAG
        DAG --> TS
    end

    subgraph CM ["Cluster Manager (YARN / K8s / Standalone)"]
        ALLOC["Resource Allocator"]
    end

    subgraph Executors ["Worker Executor Nodes"]
        subgraph Exec1 ["Executor 1"]
            E1_MEM["Execution Memory (60%)"]
            E1_STOR["Storage Memory (40%)"]
            E1_T1["Task Thread 1"]
            E1_T2["Task Thread 2"]
        end

        subgraph Exec2 ["Executor 2"]
            E2_MEM["Execution Memory (60%)"]
            E2_STOR["Storage Memory (40%)"]
            E2_T1["Task Thread 1"]
            E2_T2["Task Thread 2"]
        end
    end

    Driver --> CM
    CM --> Exec1
    CM --> Exec2
    TS -->|Tasks| Exec1
    TS -->|Tasks| Exec2
```

---

## 2. Catalyst Query Optimizer & Tungsten Engine

All PySpark DataFrame operations benefit from two core internals:

### Catalyst Optimizer Flow
1. **Unresolved Logical Plan**: Generated directly from PySpark SQL or DataFrame API calls.
2. **Analyzed Logical Plan**: Column names and types are resolved against the catalog.
3. **Optimized Logical Plan**: Pushes filters down (`filterPushdown`), prunes unused columns, and collapses adjacent projections.
4. **Physical Plans**: Generates multiple physical execution strategies (e.g. BroadcastHashJoin vs SortMergeJoin).
5. **Cost Model Evaluation**: Selects the optimal physical plan based on data statistics.
6. **Code Generation (Tungsten)**: Generates bytecode for memory-efficient execution without JVM object overhead.

```mermaid
flowchart LR
    A["Unresolved Plan"] -->|Catalog Resolution| B["Analyzed Plan"]
    B -->|Logical Optimizations| C["Optimized Plan"]
    C -->|Physical Planning| D["Physical Plans"]
    D -->|Cost Model| E["Selected Physical Plan"]
    E -->|Code Generation| F["Java Bytecode Execution"]
```

---

## 3. Data Processing DAG & Execution Stages

The pipeline constructed in `src/etl_pipeline.py` executes as a Directed Acyclic Graph (DAG) divided into stages by shuffle boundaries:

```mermaid
flowchart TD
    subgraph Stage1 ["Stage 1: Extract & Filter (Narrow Transformations)"]
        S1_READ["Read CSV / JSON with StructType"]
        S1_QUAL["Quality Audit & Range Check"]
        S1_TRANS["Filter & Derived Monetary Metrics"]
        
        S1_READ --> S1_QUAL --> S1_TRANS
    end

    subgraph Shuffle1 ["Network Shuffle Boundary"]
        SHUFFLE["Hash Partitioning on Join/Group Keys"]
    end

    subgraph Stage2 ["Stage 2: Join & Aggregations (Wide Transformations)"]
        S2_BHJ["Broadcast Hash Join with Product Catalog"]
        S2_AGG["GroupBy & Rollup Metrics"]
        S2_WIN["Window Function (Ranking & Moving Avg)"]
        
        S2_BHJ --> S2_AGG --> S2_WIN
    end

    subgraph Stage3 ["Stage 3: Output Sink Write"]
        S3_WRITE["Parquet Writer (Partitioned by Category)"]
    end

    Stage1 --> Shuffle1
    Shuffle1 --> Stage2
    Stage2 --> Stage3
```

---

## 4. Memory Layout Breakdown

Each executor process allocates memory according to the Unified Memory Manager model (`spark.memory.fraction` = 0.6 default):

| Memory Segment | Configuration Flag | Purpose |
|---|---|---|
| **Reserved Memory** | Hardcoded (300 MB) | System framework internal allocation |
| **User Memory** | `1 - spark.memory.fraction` (40%) | User data structures, UDF variables, custom Python objects |
| **Execution Memory** | Part of `spark.memory.fraction` | Shuffle buffers, hash tables for joins, sort buffers |
| **Storage Memory** | Part of `spark.memory.fraction` | Cached DataFrames (`persist`), broadcast variables |
| **Off-Heap Memory** | `spark.memory.offHeap.size` | Arrow buffers, Tungsten off-heap native memory allocations |
