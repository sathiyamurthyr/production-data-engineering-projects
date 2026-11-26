# Architectural Design Decisions: Snowflake Cloud Data Warehousing

This document outlines key technical decisions, architectural trade-offs, and design rationale chosen for the Snowflake Data Engineering framework.

---

## Decision 1: Virtual Warehouse Sizing & Multi-Cluster Scaling Strategy

### Options Evaluated:
1. **Single Large Warehouse (Fixed Scale-Up)**: Dedicated Large/X-Large warehouse running continuously.
2. **Multi-Cluster Auto-Scaling Warehouses (Scale-Out)**: Min 1, Max 5 cluster configuration with Standard vs Economy scaling policies.
3. **Dedicated Isolated Warehouses per Workload**: Separate warehouses for ETL (`ETL_WH`), Analytics (`ANALYTICS_WH`), and Development (`DEV_WH`).

### Selected Decision:
Option 3 combined with Option 2: Workload-isolated multi-cluster virtual warehouses.

### Rationale & Trade-offs:
- **Workload Isolation**: Prevents heavy batch ETL jobs from starving interactive BI queries of CPU and RAM.
- **Scale-Up vs Scale-Out**:
  - **Scale-Up (X-Small to Medium)** is used for `ETL_WH` to speed up memory-intensive single-query joins and avoid disk spilling.
  - **Scale-Out (Min 1, Max 5)** with `STANDARD` policy is used for `ANALYTICS_WH` to handle peak user concurrency without query queuing.
- **Auto-Suspend Timing**: Set `AUTO_SUSPEND = 60` seconds on all compute warehouses. Reducing timeout from 300s to 60s eliminates idle compute billing without increasing cold-start penalty.

---

## Decision 2: Stream-and-Task Pipelines vs Declarative Dynamic Tables

### Options Evaluated:
1. **Imperative Streams & Tasks**: Explicit Change Data Capture (CDC) streams and task DAGs executing `MERGE INTO` statements.
2. **Declarative Dynamic Tables**: Managed dynamic tables with configured `TARGET_LAG` (e.g. 5 minutes).
3. **Materialized Views**: Single-table automatic background aggregations.

### Selected Decision:
Hybrid Model: Declarative Dynamic Tables for continuous gold analytical layers; Streams & Tasks for complex conditional multi-target DML routines.

### Comparison & Decision Criteria Matrix:

| Evaluation Criteria | Streams & Tasks | Dynamic Tables | Materialized Views |
| :--- | :--- | :--- | :--- |
| **Pipeline Paradigm** | Imperative (Procedural SQL/DML) | Declarative (Target Query SELECT) | Declarative Aggregation |
| **Multi-Table JOIN Support** | Full support in MERGE | Full support in SELECT | None (Single Table Only) |
| **Window Functions & CTEs** | Full support | Full support | Not supported |
| **Target Lag Enforcement** | Schedule-based (Cron/Interval) | Automated by Snowflake Cloud Service | Real-time continuous |
| **Maintenance Overhead** | Requires DAG state management | Managed by Snowflake Engine | Managed by Cloud Service |
| **Primary Use Case** | Complex ETL with custom DML logic | Analytical rollups & Reporting tables | Simple single-table aggregates |

---

## Decision 3: Internal Stages vs External Storage Integrations

### Options Evaluated:
1. **Internal Named Stages (`CREATE STAGE my_internal_stage`)**: Storing data inside Snowflake-managed cloud storage.
2. **External Stages with Storage Integration**: Storing raw data in cloud data lake buckets (AWS S3) authenticated via IAM Roles.
3. **External Stages with AWS Key/Secret Credentials**: Direct authentication using hardcoded credentials.

### Selected Decision:
External Stages with Storage Integrations for enterprise data lakes; Internal Stages for local file staging.

### Rationale:
- **Security & Governance**: Storage Integrations create account-level trust relationships via IAM Roles, avoiding hardcoded cloud storage credentials in SQL scripts.
- **Data Lake Interoperability**: External stages allow existing ETL tools, AWS Glue, and Spark pipelines to write directly to S3 without duplicating data across platforms.

---

## Decision 4: Table Type Selection (Permanent vs Transient vs Temporary)

### Options Evaluated:
1. **Default Permanent Tables for All Layers**: 1-90 days Time Travel + 7 days Fail-Safe across all schemas.
2. **Workload-Specific Table Types**:
   - Staging layer: `TRANSIENT` tables (1 day Time Travel, 0 Fail-Safe).
   - Session scratchpads: `TEMPORARY` tables.
   - Core Analytical Marts: `PERMANENT` tables (30-90 days Time Travel + 7 days Fail-Safe).

### Selected Decision:
Option 2: Workload-specific table taxonomy.

### Rationale:
- **Cost Reduction**: High-churn staging tables (reloaded daily) incur huge Fail-Safe storage charges if created as Permanent tables. Declaring staging tables as `TRANSIENT` reduces storage costs by over 70%.
- **Disaster Recovery**: Core production dimension and fact tables remain `PERMANENT` to ensure complete data protection and point-in-time restoration capabilities.

---

## Decision 5: Role-Based Access Control (RBAC) Architecture & Security

### Options Evaluated:
1. **Single Layer Roles**: Directly granting object privileges (SELECT, INSERT) to functional roles (e.g. `DATA_ENGINEER`).
2. **Two-Layer Role Hierarchy (Access Roles + Functional Roles)**:
   - **Access Roles (AR)**: Own privileges on specific database objects (e.g. `AR_DATA_ENG_READWRITE`).
   - **Functional Roles (FR)**: Represent business job duties and inherit one or more Access Roles.
3. **Policy-Based Column/Row Security**: Attaching Dynamic Data Masking and Row Access Policies to sensitive tables.

### Selected Decision:
Option 2 combined with Option 3.

### Rationale:
- **Maintainability**: When new tables are added, privileges are granted once to Access Roles. Functional roles automatically inherit permissions without updating individual user grants.
- **Data Privacy Compliance (GDPR/HIPAA)**: Dynamic Data Masking obfuscates email and personal identifiers inline based on `CURRENT_ROLE()`, ensuring raw PII is visible only to authorized roles.
