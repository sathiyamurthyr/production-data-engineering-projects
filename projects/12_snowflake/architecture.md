# System Architecture: Snowflake Cloud Data Warehousing

This document presents the detailed architectural design of Snowflake's multi-cluster shared-data cloud warehouse architecture, micro-partition layout, zero-copy cloning, time travel mechanics, streams & tasks execution engine, declarative dynamic tables, and enterprise governance framework.

---

## 1. High-Level 3-Layer Architecture Overview

Snowflake decouples compute, storage, and cloud management into three independent layers. This architecture guarantees that storage scales independently of compute, eliminating traditional resource contention.

```mermaid
flowchart TD
    subgraph CS["Cloud Services Layer (Brain)"]
        CS1["Authentication & Access Control (RBAC)"]
        CS2["Infrastructure & Warehouse Management"]
        CS3["Query Parser, Optimizer & Query Cache"]
        CS4["Metadata Catalog & Transaction Manager"]
    end

    subgraph VW["Virtual Warehouse / Compute Layer (Muscle)"]
        VW1["ETL Warehouse (Medium: 4 Nodes)"]
        VW2["Analytics Warehouse (Large: Multi-Cluster 1-5)"]
        VW3["Dev & Ad-hoc Warehouse (X-Small: 1 Node)"]
    end

    subgraph ST["Centralized Cloud Storage Layer (Memory)"]
        ST1["AWS S3 / Azure Blob / GCS Storage"]
        ST2["Immutable Compressed Micro-Partitions (50MB - 150MB)"]
        ST3["Columnar Storage & Statistics (Min/Max/Nulls)"]
    end

    CS --> VW
    VW --> ST
    CS --> ST
```

### Layer Details:
1. **Cloud Services Layer**: Coordinates all account operations—authentication, role-based access control, query parsing, transaction management, micro-partition metadata tracking, and automatic metadata caching.
2. **Virtual Warehouse (Compute) Layer**: Consists of MPP (Massively Parallel Processing) compute clusters allocated on demand. Warehouses pull micro-partitions from storage into local SSD caches for rapid processing.
3. **Centralized Storage Layer**: Object storage (S3/Azure Blob/GCS) storing all data as immutable columnar micro-partitions.

---

## 2. Micro-Partitioning & Pruning Engine

Data in Snowflake tables is automatically partitioned into contiguous, immutable micro-partitions (50MB to 150MB uncompressed).

```mermaid
flowchart LR
    subgraph QueryFilter["Incoming Query: WHERE date = '2026-07-01' AND category = 'Electronics'"]
        Q["Query Optimizer"]
    end

    subgraph MetadataCatalog["Cloud Services Metadata Catalog"]
        M1["MP_01: Date [2026-06-25 - 2026-06-30] -> PRUNED"]
        M2["MP_02: Date [2026-07-01 - 2026-07-01], Category ['Apparel'] -> PRUNED"]
        M3["MP_03: Date [2026-07-01 - 2026-07-02], Category ['Electronics'] -> MATCHED"]
    end

    subgraph ComputeExecution["Virtual Warehouse SSD Cache"]
        EX["Read MP_03 Only (Skips 66% of Data)"]
    end

    QueryFilter --> MetadataCatalog
    MetadataCatalog -->|Pruned Filter| ComputeExecution
```

### Key Properties:
- **Automatic Partitioning**: No manual partition maintenance or path specification needed.
- **Columnar Storage**: Columns within micro-partitions are stored separately and compressed using algorithm selection (LZ4, ZSTD).
- **Partition Metadata**: Min/max ranges, distinct counts, and null counts stored in Cloud Services allow 95%+ partition pruning prior to reading data blocks.

---

## 3. Zero-Copy Cloning Architecture

Zero-copy cloning duplicates tables, schemas, or entire databases instantly by creating new metadata references pointing to existing immutable micro-partitions.

```mermaid
flowchart TD
    subgraph SourceTable["Production Table: FACT_SALES"]
        P1["Micro-Partition 001"]
        P2["Micro-Partition 002"]
        P3["Micro-Partition 003"]
    end

    subgraph ZeroCopyClone["CLONE Command executed"]
        C_META["Cloned Table: FACT_SALES_DEV"]
    end

    subgraph PartitionState["Micro-Partition Allocation"]
        C_META -->|Metadata Pointer| P1
        C_META -->|Metadata Pointer| P2
        C_META -->|Metadata Pointer| P3
    end

    subgraph Mutation["Update on Cloned Table"]
        P4["New Micro-Partition 004 (Modified Row)"]
        C_META -.->|Updated Metadata Pointer| P4
    end
```

### Operational Characteristics:
- **Zero Cost at Creation**: Takes milliseconds to execute regardless of dataset size; incurs zero additional storage costs initially.
- **Divergent State**: Modifications to the clone write new micro-partitions without altering the source table partitions.

---

## 4. Time Travel & Fail-Safe Lifecycle

Snowflake provides automatic data protection across table lifecycles through Time Travel and Fail-Safe periods.

```mermaid
timeline
    title Micro-Partition Storage Lifecycle
    Active Data : Current live micro-partitions accessible to active queries
    Time Travel (0 - 90 Days) : Historical versions accessible via AT / BEFORE queries, UNDROP, and CLONE AT
    Fail-Safe (7 Days Non-Configurable) : Emergency recovery period accessible ONLY by Snowflake Support
    Purged Storage : Micro-partition blocks deleted from cloud object storage
```

### Table Type Comparison Matrix:

| Feature / Metric | Permanent Tables | Transient Tables | Temporary Tables |
| :--- | :--- | :--- | :--- |
| **Default Scope** | Account-wide persistent | Account-wide persistent | Session-only lifetime |
| **Max Time Travel** | Up to 90 Days | 1 Day max | 1 Day max |
| **Fail-Safe Period** | 7 Days (Non-configurable) | 0 Days (No Fail-Safe) | 0 Days (No Fail-Safe) |
| **Fail-Safe Cost** | Yes | No | No |
| **Primary Use Case** | Production Fact/Dim Tables | High-churn Staging Tables | Ephemeral Script Scratchpads |

---

## 5. Streams & Tasks CDC Processing Pipeline

Change Data Capture (CDC) pipelines combine Streams to record row deltas and Tasks to automate execution.

```mermaid
flowchart LR
    subgraph Landing["Stage Landing Zone"]
        FILE["RAW_SALES.CSV"]
    end

    subgraph Staging["Staging Layer"]
        STG["STG_SALES Table"]
        STR["STG_SALES_STREAM (CDC Tracking Offset)"]
    end

    subgraph TaskDAG["Task Orchestration Engine"]
        T1["Task 1: PROCESS_SALES_STREAM_TASK\n(WHEN SYSTEM$STREAM_HAS_DATA)"]
        T2["Task 2: REFRESH_SUMMARY_TASK\n(AFTER Task 1)"]
    end

    subgraph GoldLayer["Production Gold Layer"]
        FACT["FACT_SALES (Target Fact Table)"]
        SUMM["HOURLY_SALES_SUMMARY"]
    end

    FILE -->|COPY INTO| STG
    STG --> STR
    STR --> T1
    T1 -->|Incremental MERGE| FACT
    FACT --> T2
    T2 -->|Aggregate Rollup| SUMM
```

---

## 6. Declarative Continuous Pipelines with Dynamic Tables

Dynamic Tables automate complex data transformation DAGs declaratively based on target lag parameters.

```mermaid
flowchart TD
    RAW["STG_SALES Table"] --> DT1
    RAW2["STG_CUSTOMERS Table"] --> DT1

    subgraph DynamicTables["Snowflake Managed Refresh Engine"]
        DT1["DT_DAILY_CATEGORY_METRICS\n(TARGET_LAG = '5 minutes')"]
        DT2["DT_CUSTOMER_SALES_360\n(TARGET_LAG = 'DOWNSTREAM')"]
    end

    DT1 --> DT2
    DT2 --> BI["BI Dashboards & Analytical Reports"]
```

---

## 7. Role-Based Access Control (RBAC) & Governance Architecture

Snowflake security decouples privileges into Access Roles and Functional Roles, combined with row/column policies.

```mermaid
flowchart TD
    subgraph SystemRoles["System-Defined Roles"]
        AA["ACCOUNTADMIN"]
        SA["SECURITYADMIN"]
        UA["USERADMIN"]
        SYS["SYSADMIN"]
    end

    subgraph FunctionalRoles["Functional Roles (Job Functions)"]
        FR_DE["FR_SENIOR_DATA_ENGINEER"]
        FR_BI["FR_BI_ANALYST"]
    end

    subgraph AccessRoles["Access Roles (Object Privileges)"]
        AR_RW["AR_DATA_ENG_READWRITE"]
        AR_RO["AR_BI_ANALYST_READONLY"]
    end

    subgraph SecurityPolicies["Row & Column Security Policies"]
        MP["EMAIL_MASKING_POLICY (Column Level)"]
        RP["REGIONAL_STORE_POLICY (Row Level)"]
    end

    AA --> SA --> UA --> SYS
    SYS --> FR_DE
    SYS --> FR_BI
    FR_DE --> AR_RW
    FR_BI --> AR_RO
    AR_RW --> MP
    AR_RW --> RP
```
