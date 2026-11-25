# Architectural Decision Records (ADRs): Azure Data Factory

> **Data Engineering Diaries** | Key Infrastructure & Architectural Design Decisions

---

## ADR 001: Choosing Azure Data Factory vs Apache Airflow vs Databricks Workflows

### Context
We required an enterprise orchestration engine to integrate 90+ hybrid data sources, perform raw file ingestion into ADLS Gen2, and orchestrate transformation pipelines across Azure SQL, Snowflake, and Databricks.

### Options Considered
1. **Azure Data Factory (ADF):** Native Azure managed serverless ETL/ELT orchestrator with code-free and SDK capabilities.
2. **Apache Airflow (MWAA / Managed Airflow):** Open-source code-first Python DAG orchestrator.
3. **Databricks Workflows:** Spark-centric task orchestrator built into Databricks workspace.

### Decision
We chose **Azure Data Factory** as the primary orchestrator for external data ingestion and cross-system control flow, while leveraging **Databricks Workflows** for heavy Spark-native ETL jobs triggered by ADF.

### Comparison Matrix

| Criteria | Azure Data Factory (ADF) | Apache Airflow | Databricks Workflows |
|---|---|---|---|
| **Native Connectors** | 90+ Enterprise Connectors | Community Providers (Python) | Limited (Spark/DBFS based) |
| **Code-Free ETL** | Yes (Mapping Data Flows) | No (Python DAGs only) | No (Notebooks/Python) |
| **Self-Hosted / On-Prem** | Native via Self-Hosted IR | Requires Hybrid Celery Exec | Complex |
| **Security & Identity** | Native Azure SAMI / Key Vault | Secret Managers (AWS/Vault) | Databricks Secrets |
| **Cost Model** | Pay-per-activity / DIU-hour | Dedicated VM/Cluster hours | DBU compute consumption |

---

## ADR 002: Integration Runtime Topology — Managed VNet IR vs Azure IR vs Self-Hosted IR

### Context
Data sources span public cloud services, isolated Azure VNets without public IPs, and on-premise relational databases. We needed to define our Integration Runtime architecture.

### Decision
- **Managed VNet Azure IR:** Selected for all cloud-to-cloud operations. Disables public IP connectivity and routes traffic via Azure Managed Private Endpoints.
- **Self-Hosted Integration Runtime (SHIR):** Deployed on an HA cluster of Azure VMs with ExpressRoute/VPN for on-premise database ingestion.

### Rationale
- Managed VNet IR provides zero-trust security without requiring manual network configuration or public IP whitelisting.
- SHIR handles hybrid on-premise firewall traversal without opening inbound ports.

---

## ADR 003: Transformation Engine — Mapping Data Flows vs Managed Azure Databricks

### Context
We evaluated whether to use ADF Mapping Data Flows (compiled Spark) or Azure Databricks PySpark notebooks for complex transformations.

### Decision
- **ADF Mapping Data Flows:** Used for low-to-medium complexity ETL, standardized cleansing, and column mappings where non-developer analysts maintain pipelines.
- **Azure Databricks PySpark Activities:** Used for complex machine learning feature engineering, advanced Delta Lake manipulations (SCD Type 2), and petabyte-scale transformations.

### Rationale
Mapping Data Flows abstract Spark cluster management, reducing operational overhead for standard tabular transformations while allowing Databricks to handle custom, high-code analytical workloads.

---

## ADR 004: Credential Management — System-Assigned Managed Identity & Key Vault

### Context
Credential security is mandatory. Hardcoded passwords, connection strings, or service principal secrets stored in deployment scripts create key leakage risks.

### Decision
Mandate **System-Assigned Managed Identity (SAMI)** for all Azure-to-Azure authentication and **Azure Key Vault Linked Services** for non-Azure databases (Snowflake, REST APIs).

### Rationale
- Managed Identities eliminate secret lifecycle management. Azure handles key generation and automatic 90-day rotation.
- Key Vault secret references in ADF ensure credentials are fetched dynamically at activity execution time and never exposed in pipeline logs (`secureInput` / `secureOutput` flags enabled).

---

## ADR 005: Trigger Strategy — Tumbling Window Triggers for Stateful Pipelines

### Context
Data pipelines often need to process historical data partitions in strict chronological order and automatically backfill missed execution windows during downtime.

### Decision
Adopt **Tumbling Window Triggers** for time-series and incremental partition loads, reserving **Schedule Triggers** only for stateless snapshot refreshes.

### Rationale
- Tumbling Window triggers maintain state for every time slice.
- They support self-dependencies (Window N waits for Window N-1 to succeed).
- In the event of system outages, Tumbling Windows automatically generate and execute backfill runs in sequential order.
