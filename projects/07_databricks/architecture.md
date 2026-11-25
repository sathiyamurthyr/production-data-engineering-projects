# Databricks Enterprise Lakehouse Architecture & Security Model

## 1. Executive Platform Architecture

Databricks operates on a decoupled architecture separating the **Control Plane** (managed by Databricks) from the **Data Plane** (running inside the customer's cloud account, e.g. AWS, Azure, GCP).

```mermaid
flowchart TB
    subgraph ControlPlane["Databricks Control Plane (Managed by Databricks)"]
        UI["Web UI & Workspace"]
        JobsService["Jobs & Workflow Service"]
        Metastore["Unity Catalog Service"]
        ClusterMgr["Cluster Manager"]
    end

    subgraph DataPlane["Customer Data Plane (AWS / Azure / GCP)"]
        subgraph ComputePool["Compute Clusters & Serverless"]
            Driver["Spark Driver Node"]
            Worker1["Photon Worker Node 1"]
            Worker2["Photon Worker Node 2"]
            Worker3["Photon Worker Node 3"]
        end
        
        subgraph Storage["Cloud Storage (S3 / ADLS Gen2 / GCS)"]
            Bronze["Bronze Storage (Raw JSON/CSV)"]
            Silver["Silver Storage (Cleaned Parquet/Delta)"]
            Gold["Gold Storage (Business Data Marts)"]
        end
    end

    UI --> ControlPlane
    JobsService --> Driver
    ClusterMgr --> ComputePool
    Metastore --> ComputePool

    Driver <-->|gRPC / RPC| Worker1
    Driver <-->|gRPC / RPC| Worker2
    Driver <-->|gRPC / RPC| Worker3

    Worker1 <-->|Direct Direct Parquet Read/Write| Storage
    Worker2 <-->|Direct Direct Parquet Read/Write| Storage
    Worker3 <-->|Direct Direct Parquet Read/Write| Storage
```

---

## 2. Decoupled Control Plane vs. Data Plane

| Architecture Component | Hosted Location | Key Responsibilities | Security Boundaries |
| :--- | :--- | :--- | :--- |
| **Control Plane** | Databricks Cloud Account | Notebook UI, REST APIs, job scheduler, query history, access control rules, metastore index | No raw data stored here; only metadata and control plane logs. |
| **Data Plane** | Customer Cloud Account | Spark driver/workers, serverless SQL warehouses, local SSD caches, memory processing | Data never leaves customer network boundary except for UI previews. |
| **Unity Catalog** | Centralized Service | Enterprise RBAC, Lineage tracking, Dynamic data masking, Audit logs | Central governance hub for multi-workspace deployments. |

---

## 3. Remote Connectivity: Databricks Connect v2 Architecture

Databricks Connect v2 uses the open-source **Spark Connect** protocol based on **gRPC** and **Apache Arrow**.

```mermaid
sequenceDiagram
    autonumber
    participant LocalIDE as Local IDE / CI Runner
    participant ClientSDK as Databricks Connect (Python Client)
    participant ControlPlane as Databricks Control Plane
    participant Driver as Databricks Spark Driver
    participant CloudStorage as S3 / ADLS Storage

    LocalIDE->>ClientSDK: PySpark DataFrame Code Execution
    ClientSDK->>ControlPlane: Authenticate via OAuth M2M / PAT
    ControlPlane-->>ClientSDK: Token Validated & Cluster Endpoint Returned
    ClientSDK->>Driver: Transmit Unresolved Logical Plan (gRPC + Arrow)
    Driver->>Driver: Catalyst Optimizer & Photon Plan Compilation
    Driver->>CloudStorage: Execute Distributed Read/Write
    CloudStorage-->>Driver: Data Partitions Returned
    Driver-->>ClientSDK: Stream Arrow RecordBatches (Results)
    ClientSDK-->>LocalIDE: DataFrame Display / Assertions Passed
```

---

## 4. Unity Catalog Governance & Network Security

- **Storage Credentials**: Encapsulate cloud IAM roles (AWS IAM Role / Azure Managed Identity) so users never handle raw storage keys.
- **External Locations**: Bind cloud storage URIs (e.g. `s3://company-gold/`) to specific storage credentials.
- **Single-User / Shared Security Modes**:
  - `SINGLE_USER`: Dedicated cluster for single developer with full Python/R support.
  - `USER_ISOLATION` / `SHARED`: Multi-tenant cluster enforcing Unity Catalog SQL and Python access controls between users.
