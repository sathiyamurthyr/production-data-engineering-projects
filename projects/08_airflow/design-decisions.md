# Technical Design Decisions & Trade-Off Analysis

This document outlines key technical decisions, trade-offs, and architectural guidelines established for Apache Airflow pipeline orchestration in this project.

---

## 1. TaskFlow API vs. Traditional Operators

### Context
Airflow 2.0+ introduced the TaskFlow API (`@dag`, `@task`), transforming how tasks and data dependencies are defined compared to traditional operators (`PythonOperator`, `BashOperator`).

### Decision Matrix

| Dimension | TaskFlow API (`@task`) | Traditional Operators |
|---|---|---|
| **Code Verbosity** | Extremely concise; pure Python functions | Higher boilerplate (`PythonOperator(task_id=..., python_callable=...)`) |
| **XCom Data Passing** | Automatic via function arguments and return values | Explicit `xcom_push` and `xcom_pull` calls required |
| **Type Checking** | Full IDE autocompletion and static type check support | Weak typing; dictionary key lookups |
| **Dynamic Mapping** | Built-in `.expand()` syntax | Complex dynamic loop constructs required |

### Decision Standard
- **Use TaskFlow API** for all Python-based transformation, business logic, and dynamic mapping tasks.
- **Use Traditional Operators** for specialized external service integrations (e.g., `SQLExecuteQueryOperator`, `S3CreateObjectOperator`, `dbt` operators).

---

## 2. Event-Driven Datasets vs. Time-Based ExternalTaskSensor

### Context
Cross-DAG dependencies traditionally relied on `ExternalTaskSensor`, which polled the metadata DB for task status in an upstream DAG. Airflow 2.4+ introduced `Dataset` primitives.

### Decision Matrix

| Metric | `ExternalTaskSensor` | `Dataset` (Data-Aware Scheduling) |
|---|---|---|
| **Coupling** | Tightly coupled to exact upstream execution timestamps | Fully decoupled; triggers on dataset URI update events |
| **Resource Overhead** | High (occupies sensor slots or scheduler polling cycles) | Zero polling overhead; database trigger driven |
| **Schedule Flexibility** | Fragile if upstream cron schedule shifts by 5 minutes | Resilient; runs immediately when upstream data is produced |

### Decision Standard
- Adopt **Airflow Datasets** as the enterprise default for cross-DAG dependencies.
- Retain `ExternalTaskSensor` only when strict execution date alignment across legacy crons is mandatory.

---

## 3. CeleryExecutor vs. KubernetesExecutor

### Context
Choosing the right execution backend impacts cluster cost, scalability, and operational complexity.

### Decision
- **Primary Recommendation**: **CeleryExecutor** for standard enterprise workloads with predictable batch schedules. Provides rapid task startup times (< 1 second) and high task throughput per minute.
- **Hybrid Recommendation**: **CeleryKubernetesExecutor** when 80% of tasks are lightweight ETL scripts, but 20% are heavy ML/Spark tasks requiring custom Docker environments and dedicated GPU resources.

---

## 4. Custom Operators vs. Generic PythonOperator

### Context
Teams often write repetitive code inside `PythonOperator` functions across dozens of DAGs.

### Decision
- Standardize on **Custom Operators** (`CustomETLOperator`, `DataQualityOperator`) when logic is reused across 3 or more DAGs.
- **Benefits**:
  - Enforces uniform logging, retry policies, and metadata standards across teams.
  - Exposes custom UI color coding (`ui_color`) in the Airflow graph view for visual identification.
  - Supports clean `template_fields` Jinja rendering without manual parameter extraction.

---

## 5. XCom Management vs. Object Storage Staging

### Context
Passing data between tasks in Airflow.

### Decision Standard
- **STRICT RULE**: XCom payloads MUST NOT exceed **64 KB**.
- XCom is intended exclusively for metadata (e.g., file paths, row counts, execution status, S3 keys).
- For actual data payloads (DataFrames, JSON batches, CSV extracts), tasks write to **AWS S3** or **GCS** staging paths (`s3://bucket/staging/year=YYYY/month=MM/...`) and pass only the S3 URI string via XCom.
