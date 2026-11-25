# 🧠 Framework Design Decisions: Data Quality & Validation

This document outlines the architectural trade-offs, design patterns, and decisions made while building this Data Quality (DQ) Engineering framework.

---

## 1. Dynamic Rule Discovery via Decoupled Registry Pattern
* **Decision**: Implement a class decorator-driven `RuleRegistry` instead of hardcoded if/else class generation.
* **Rationale**: Coupling the YAML parser to individual class instantiations creates a maintenance bottleneck. If a developer creates a new rule class (e.g., `SSNFormatRule`), they would have to modify the parse logic in the engine. With the registry decorator `@RuleRegistry.register("ssn_format")`, rules register themselves automatically, satisfying the Open-Closed Principle (OCP).

---

## 2. Coexistence of Row-Level and Table-Level Rules
* **Decision**: Support both row-level rules (like `NullCheckRule`) and table-level rules (like `RowCountRule` and `FreshnessRule`) through a unified `evaluate()` signature returning a structured `RuleResult`.
* **Rationale**: Data quality dimensions are diverse. 
  - *Row-level validation* focuses on individual records, outputting specific row indices that failed (e.g. invalid phone number).
  - *Table-level validation* focuses on volume, shape, or timing constraints (e.g., "the dataset must have at least 1,000 rows").
  - **Unification**: For table-level rules, failures affect the whole batch. Thus, if a table-level rule fails, the framework treats the entire batch of rows as quarantined or failed, returning all row indices as failed.

---

## 3. Severity-Based Routing & Partitioning (Quarantine pattern)
* **Decision**: Introduce four severity levels (`CRITICAL`, `ERROR`, `WARNING`, `INFO`) and use them to route records.
* **Rationale**: Not all data quality failures are equal.
  - A malformed email or minor formatting issue (`WARNING`) should raise an alert but not stop the pipeline, as it would cause unnecessary pipeline downtime.
  - A missing primary key (`CRITICAL` or `ERROR`) makes joining impossible and must block the ingestion.
  - **Routing**: The `QualityEngine` gathers all unique row indices failing `CRITICAL` or `ERROR` rules, and partitions the DataFrame using a fast boolean index mask. Failed rows go to a quarantine bucket, while clean rows proceed to the Silver layer.

---

## 4. Double-Penalization Avoidance on Validity Checks
* **Decision**: Let null/missing values pass validity format checks (e.g., `EmailFormatRule` or `DateRangeRule`).
* **Rationale**: If a field is null, it should be caught and flagged by a `NullCheckRule` (Completeness dimension). If format rules also flag nulls, a single missing cell will register as two failures (Completeness and Validity). This skews quality metrics. Keeping format rules focused on *non-null* structure preserves metric accuracy.

---

## 5. Metadata Storage & Observability: Choosing SQLite
* **Decision**: Use SQLite for storing historical execution runs, pass rates, and failure frequencies.
* **Rationale**: Modern data pipelines require operational metadata logs. Storing runs in local flat JSON files makes time-series analysis difficult. SQLite provides a serverless, single-file relational database that can run locally, in Docker containers, or inside serverless Cloud Functions (e.g. AWS Lambda) without the infrastructure overhead of Postgres or MySQL, while still allowing full SQL query support for historical dashboards.

---

## 6. Great Expectations Fallback Emulation
* **Decision**: Implement a native emulation runner inside `GERunner` if the `great-expectations` module is missing.
* **Rationale**: Installing Great Expectations can be heavy and slow in lightweight serverless containers. Our fallback emulation matches the expectation names (`expect_column_values_to_not_be_null`, etc.) and evaluates them locally using pandas. This provides portability and ensures code running in low-dependency environments remains functional.
