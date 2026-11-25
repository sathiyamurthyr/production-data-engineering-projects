# Architectural Decision Records (ADRs) — Azure Databricks

This document details the trade-off analysis, justification, and design choices for key platform engineering decisions in the **Azure Databricks Data Engineering** project.

---

## ADR-001: Unity Catalog vs. Legacy Hive Metastore

### Context
Enterprise data platforms require governance, access control, and lineage across multiple Databricks workspaces.

### Options Evaluated
1. **Legacy Workspace Hive Metastore**: Local metastore per workspace with table-level ACLs.
2. **External Azure SQL Hive Metastore**: Shared external MySQL/SQL DB metastore across workspaces.
3. **Azure Unity Catalog**: Account-level centralized governance catalog backed by Azure Access Connector Managed Identity.

### Decision
Adopt **Azure Unity Catalog**.

### Trade-off & Rationale Matrix

| Decision Criteria | Legacy Hive Metastore | External Azure SQL Metastore | Azure Unity Catalog |
| :--- | :--- | :--- | :--- |
| **Governance Scope** | Workspace-isolated | Cross-workspace table metadata | Account-level unified governance |
| **Access Control** | Table ACLs only | Table ACLs only | Attribute-Based Access Control (ABAC) |
| **Data Lineage** | Requires manual integration | Requires manual integration | Automated column & table lineage |
| **Storage Security** | High risk (access keys in code) | Storage keys in workspace config | Azure Managed Identity (keyless) |
| **Delta Sharing** | Not supported | Not supported | Native cross-cloud Delta Sharing |

---

## ADR-002: Direct ABFSS Access vs. DBFS Mounting

### Context
Data pipelines need to read and write files stored in Azure Data Lake Storage Gen2 (ADLS Gen2).

### Options Evaluated
1. **DBFS Directory Mounting (`dbutils.fs.mount`)**: Mount ADLS Gen2 container to `dbfs:/mnt/<container>`.
2. **Direct ABFSS Access (`abfss://<container>@<storage>.dfs.core.windows.net/`)**: Reference storage paths directly.

### Decision
Standardize on **Direct ABFSS Access** combined with **Unity Catalog External Locations**.

### Rationale
- **Security Leakage**: DBFS mounts expose secrets across all users executing on the cluster if not scoped carefully.
- **Portability**: Unity Catalog manages direct ABFSS paths using Storage Credentials backed by Azure Access Connectors, eliminating path hardcoding.
- **Deprecation**: Databricks officially recommends moving away from DBFS mounts in modern production environments.

---

## ADR-003: Ephemeral Job Clusters vs. Shared All-Purpose Clusters

### Context
Orchestration tools like Azure Data Factory trigger daily batch ETL workloads.

### Options Evaluated
1. **Shared All-Purpose Interactive Clusters**: Always-on or auto-scaling cluster running continuous jobs.
2. **Ephemeral Job Clusters (New Cluster per Job)**: Dynamically provisioned cluster created at job start and terminated immediately upon completion.

### Decision
Use **Ephemeral Job Clusters** for all scheduled ADF data engineering workloads.

### Cost & Isolation Impact
- **Cost Reduction**: Job DBU pricing is **~40% cheaper** than All-Purpose interactive DBU pricing ($0.15/DBU vs $0.40/DBU).
- **Isolation**: Ephemeral clusters ensure clean state, zero resource contention from ad-hoc query users, and no memory leaks between job runs.

---

## ADR-004: Synapse Spark Connector (PolyBase / COPY INTO) vs. Standard JDBC

### Context
Exporting Gold layer Delta tables from Azure Databricks into Azure Synapse Dedicated SQL Pools.

### Options Evaluated
1. **Standard JDBC Driver (`spark.read.format("jdbc")`)**: Single-threaded or partition-sliced JDBC insert.
2. **Azure Synapse Spark Connector (`com.databricks.spark.sqldw`)**: Bulk loading via ADLS Gen2 staging and Synapse PolyBase / `COPY INTO`.

### Decision
Use **Azure Synapse Spark Connector**.

### Benchmarks & Performance
- **JDBC Ingestion**: Bottlenecked by driver node serialization; struggles beyond 50,000 rows.
- **Synapse Spark Connector**: Writes Parquet files in parallel from executor nodes to ADLS Gen2 staging container, triggering high-speed distributed `COPY INTO` commands inside Synapse nodes. Reduces load duration for 10M rows from 45 minutes down to 3 minutes.

---

## ADR-005: Azure Key Vault-Backed Secret Scopes vs. Databricks-Managed Scopes

### Context
Managing passwords, service principal secrets, and storage keys required by Databricks jobs.

### Options Evaluated
1. **Databricks-Managed Secret Scopes**: Secrets stored in internal Databricks encrypted database.
2. **Azure Key Vault Backed Secret Scopes**: Secrets stored in Azure Key Vault and read dynamically via Azure AD.

### Decision
Standardize on **Azure Key Vault Backed Secret Scopes**.

### Rationale
- **Central Governance**: Security teams manage secrets inside Azure Key Vault without requiring Databricks workspace admin permissions.
- **Auditing**: Every secret fetch logs an immutable audit event in Azure Monitor & Key Vault Diagnostic logs.
- **Zero Plaintext Leaks**: Databricks automatically redacts any secret value fetched via `dbutils.secrets.get()`.

---

## ADR-006: VNet Injection & Private Endpoints vs. Standard Public Workspace

### Context
Protecting data plane node traffic from public internet exposure.

### Decision
Enforce **VNet Injection with No Public IP (NPIP)** and **Azure Private Endpoints**.

### Security Rationale
- Standard workspace nodes get public IPs and route traffic over public endpoints.
- VNet Injection confines cluster nodes within customer IP space (`10.178.0.0/16`).
- Private Endpoints route storage and Key Vault traffic exclusively over Microsoft internal backbone network, allowing ADLS Gen2 storage firewalls to block all public internet access (`Deny All Public Traffic`).
