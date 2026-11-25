# Capstone Platform Design Decisions

This document logs key architectural choices and design patterns implemented in the DataMart Global capstone platform.

---

## 1. Medallion Architecture
* **Decision:** Implement a three-layer Medallion structure (Bronze -> Silver -> Gold).
* **Rationale:** Decouples raw ingestion from cleaning and aggregations.
  * **Bronze:** Preserves raw event history, allowing for backfills.
  * **Silver:** Cleans, deduplicates, and standardizes data to provide a clean source of truth.
  * **Gold:** Computes business metrics, optimizing query performance for BI tools and downstream APIs.

## 2. Ingestion Fallback Engine
* **Decision:** Build a dual Spark/Pandas execution mode with a CSV/Parquet fallback.
* **Rationale:** Enables developers to run the entire pipeline locally without requiring a PySpark cluster. If Spark or PyArrow are unavailable, the platform automatically writes and reads standard CSV files while maintaining the same directory structures and data quality validations.

## 3. Airflow for Orchestration
* **Decision:** Use Apache Airflow to orchestrate the pipeline daily.
* **Rationale:** Provides dependency mapping, execution retries, SLA monitoring, and a centralized UI. Tasks are wrapped in PythonOperators that trigger modular ingestion, cleaning, and reporting jobs.

## 4. Operational Telemetry Logging
* **Decision:** Log pipeline durations, record counts, and data quality results to CSV files (`platform_costs.csv`, `pipeline_runs.csv`, `data_quality_runs.csv`) inside the storage directory.
* **Rationale:** Avoids the overhead of external database integrations for developer environments while keeping telemetry queryable via Pandas, DuckDB, or BI tools.

## 5. serving Layer via FastAPI
* **Decision:** Expose gold tables and marketing metrics through a FastAPI REST endpoint.
* **Rationale:** Provides low-latency JSON access for operational dashboards, web apps, and external callers. It reads directly from Gold storage to decouple analytic transformations from client-facing applications.
