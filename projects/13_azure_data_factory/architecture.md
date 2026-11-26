# Architecture Design: Azure Data Factory Ingestion & Integration Platform

> **Data Engineering Diaries** | Cloud-Native Enterprise Data Architecture with Azure Data Factory (ADF)

---

## 1. Executive Summary

Azure Data Factory (ADF) serves as the core orchestration and data movement engine for modern cloud data platforms on Microsoft Azure. It unifies hybrid data sources across on-premise systems, multi-cloud platforms (AWS, GCP, Snowflake), and SaaS applications into a centralized, governed Data Lakehouse ecosystem.

This document outlines the production architecture, security posture, Integration Runtime topology, CI/CD pipeline, and operational monitoring strategy for building scalable ADF data integration solutions.

---

## 2. Platform Architecture Diagram

```mermaid
graph TB
    subgraph Sources["1. Ingestion Sources"]
        S1["On-Prem SQL Server / Oracle"]
        S2["Azure SQL Database"]
        S3["REST APIs / Webhooks"]
        S4["AWS S3 / GCP Storage"]
        S5["SaaS (Salesforce, SAP)"]
    end

    subgraph Security["Security & Identity Layer"]
        KV["Azure Key Vault<br/>(Secret Store)"]
        MI["Managed Identity<br/>(SAMI / UAMI)"]
        PE["Private Endpoints<br/>(Azure Private Link)"]
    end

    subgraph ADF["2. Azure Data Factory Platform"]
        subgraph IR["Integration Runtime (Compute)"]
            IR1["Managed VNet Azure IR<br/>(Cloud Data Movement)"]
            IR2["Self-Hosted IR (SHIR)<br/>(On-Prem / Private VNet)"]
            IR3["Azure-SSIS IR<br/>(Legacy Package Execution)"]
        end

        subgraph Orchestration["Orchestration Engine"]
            LS["Linked Services<br/>(Key Vault Secret References)"]
            DS["Parameterized Datasets<br/>(Parquet, CSV, Relational)"]
            PL["Pipelines<br/>(Control Flow & Activities)"]
            MDF["Mapping Data Flows<br/>(Managed Spark Transformations)"]
        end

        subgraph Triggers["Trigger Engine"]
            T1["Schedule Trigger"]
            T2["Tumbling Window (Stateful)"]
            T3["Storage Event (Blob Created)"]
        end
    end

    subgraph Storage["3. Lakehouse Medallion Storage Layer"]
        B1["ADLS Gen2 - Bronze Layer<br/>(Raw landing / CSV & JSON)"]
        B2["ADLS Gen2 - Silver Layer<br/>(Cleansed / Parquet & Delta)"]
        B3["ADLS Gen2 - Gold Layer<br/>(Curated / Star Schema)"]
    end

    subgraph Analytics["4. Serving & Analytics Layer"]
        DW1["Azure Synapse Analytics"]
        DW2["Snowflake Data Warehouse"]
        PBI["Power BI Reports"]
    end

    subgraph Ops["5. Monitoring & Operations"]
        MON["Azure Monitor"]
        LA["Log Analytics Workspace"]
        ALERT["Alerting & Logic Apps"]
    end

    S1 --> IR2 --> LS
    S2 & S3 & S4 & S5 --> IR1 --> LS
    KV & MI & PE -.- ADF

    LS --> DS --> PL
    PL --> MDF
    T1 & T2 & T3 --> PL

    PL --> B1
    MDF --> B2 --> B3
    B3 --> DW1 & DW2 --> PBI

    PL & MDF -.- MON --> LA --> ALERT
```

---

## 3. Core Architectural Components

### 3.1 Integration Runtime (IR) Selection Strategy

The Integration Runtime is the compute infrastructure providing the execution environment for ADF activities.

| IR Type | Deploy Environment | Connectivity | Primary Use Case | Cost Model |
|---|---|---|---|---|
| **Azure IR (Standard)** | Fully Managed Cloud | Public Internet | Cloud-to-Cloud data copy & pipeline control activities | Pay-per-DIU-hour |
| **Azure IR (Managed VNet)** | Isolated VNet | Private Endpoints | Secure cloud ingestion without exposing public endpoints | Pay-per-DIU + VNet runtime |
| **Self-Hosted IR (SHIR)** | On-Prem VM / IaaS VM | On-Prem Network / ExpressRoute | Ingesting legacy databases (Oracle, DB2, SQL Server) behind corporate firewalls | Self-managed VM compute cost |
| **Azure-SSIS IR** | Managed VM Cluster | VNet Integration | Migrating legacy SQL Server Integration Services (SSIS) packages to Azure | Hourly cluster node pricing |

---

## 4. Medallion Storage Integration Pattern

ADF pipelines orchestrate data movement through the enterprise **Medallion Architecture**:

```mermaid
flowchart LR
    A["Raw Source Data"] -->|Copy Activity| B["Bronze Zone<br/>(Raw Landing / Immuta)"]
    B -->|Mapping Data Flow| C["Silver Zone<br/>(Cleansed / Deduplicated / Parquet)"]
    C -->|Databricks / Data Flow| D["Gold Zone<br/>(Aggregated Data Mart / Star Schema)"]
    D -->|Sink Copy| E["Enterprise DW<br/>(Synapse / Snowflake)"]
```

1. **Bronze Layer (Raw Landing):**
   - Ingested as-is from source systems.
   - Storage format: Raw CSV, JSON, ORC, Binary.
   - Folder structure: `/bronze/{source_system}/{table_name}/yyyy/MM/dd/`.
2. **Silver Layer (Cleansed & Standardized):**
   - Data cleansing, data type enforcement, null checks, deduplication.
   - Storage format: Compressed Parquet or Delta Lake format.
   - Managed via ADF Mapping Data Flows or Azure Databricks activities.
3. **Gold Layer (Curated Analytical Layer):**
   - Business aggregations, dimensional modeling (Fact and Dimension tables), KPI calculations.
   - Served directly to Power BI or loaded into Snowflake / Synapse Analytics.

---

## 5. Security & Network Topology

```mermaid
graph TD
    subgraph VNet["Azure Virtual Network (Isolated)"]
        subgraph SubnetADF["ADF Managed VNet"]
            MIR["Managed Integration Runtime"]
            MDF_Spark["Managed Data Flow Spark Cluster"]
        end

        subgraph SubnetStorage["Storage Subnet"]
            PE_ADLS["Private Endpoint (dfs.core.windows.net)"]
        end

        subgraph SubnetKV["Key Vault Subnet"]
            PE_KV["Private Endpoint (vault.azure.net)"]
        end

        subgraph SubnetSQL["Database Subnet"]
            PE_SQL["Private Endpoint (database.windows.net)"]
        end
    end

    MIR --> PE_ADLS & PE_KV & PE_SQL
    MDF_Spark --> PE_ADLS
```

### Security Best Practices
- **Zero Secrets in Code:** All database passwords, API tokens, and connection strings are stored in Azure Key Vault. Linked services reference Key Vault secrets using `@activity()` or native secret pointers.
- **System-Assigned Managed Identity (SAMI):** ADF authenticates to ADLS Gen2, Azure SQL, and Azure Key Vault via SAMI, avoiding service principal secret expiration issues.
- **Network Isolation:** Public network access is disabled (`publicNetworkAccess: Disabled`). Data movement flows strictly across Managed Private Endpoints over the Microsoft backbone network.

---

## 6. CI/CD Architecture & Deployment Pipeline

```mermaid
gitGraph
    commit id: "Initial Commit"
    branch feature/copy-pipeline
    checkout feature/copy-pipeline
    commit id: "Add Copy Pipeline"
    commit id: "Add Datasets"
    checkout main
    merge feature/copy-pipeline id: "Merge PR"
    commit id: "ADF Build Task (npm)"
    branch release/prod
    checkout release/prod
    commit id: "Deploy ARM Template to Prod"
```

1. **Development:** Engineers build and test pipelines in ADF Git-integrated dev instances using feature branches.
2. **Pull Request & Merge:** Merging to the `main` branch triggers the **ADF Build Task** (`@microsoft/azure-data-factory-utilities` npm package) to validate and generate ARM templates (`ARMTemplateForFactory.json`).
3. **Automated Deployment:** Azure DevOps or GitHub Actions deploys the generated ARM template to Staging and Production environments using environment-specific parameter overrides (`ARMTemplateParametersForFactory.json`).

---

## 7. Monitoring & Operational Governance

- **Diagnostic Logs:** Configured to push all `PipelineRuns`, `ActivityRuns`, and `TriggerRuns` to an Azure Log Analytics Workspace.
- **Operational Alerts:** Azure Monitor Alert rules fire webhooks to Azure Logic Apps on pipeline failure, delivering formatted Slack/Teams notifications and PagerDuty incidents.
- **SLA Enforcement:** Pipeline and activity-level `timeout` properties abort hanging executions to ensure SLAs are met.
