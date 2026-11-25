# 🙋 Data Quality Engineering: Interview Questions & Answers

This document lists over 25 comprehensive interview questions and answers related to **Data Quality (DQ) Engineering** and **Observability** patterns in production pipelines.

---

## Section 1: Data Quality Fundamentals & Strategy

### Q1: What is Data Quality Engineering, and how does it differ from traditional software testing?
**Answer**: Software testing focuses on validating *code behavior* (e.g. verifying that a feature works as expected under specific inputs). Data Quality Engineering focuses on validating the *data itself* as it flows through pipelines (e.g., verifying completeness, accuracy, timeliness). Code can be correct, but the data flowing through it can be dirty, malformed, late, or anomalous due to upstream changes.

### Q2: What are the six primary dimensions of Data Quality? Describe each briefly.
**Answer**:
1. **Completeness**: Are there missing values or missing rows? (e.g. `NullCheckRule`)
2. **Uniqueness**: Are there duplicate records? (e.g. `PrimaryKeyUniquenessRule`)
3. **Validity**: Does the data conform to a specific format, regex, or value range? (e.g. `EmailFormatRule`)
4. **Consistency**: Is the data consistent across tables and columns? (e.g. referential integrity, cross-column math)
5. **Timeliness**: Is the data fresh and has it arrived on schedule? (e.g. `FreshnessRule`)
6. **Accuracy**: Does the data represent the real-world truth? (e.g. statistical outlier checks)

### Q3: What is the "Quarantine Pattern" in data ingestion pipelines, and why is it used?
**Answer**: The quarantine pattern routes records that fail critical validation checks (e.g. invalid primary key, schema drift) into a separate, isolated location (a "quarantine" table or directory) instead of failing the entire batch or letting bad data proceed. This keeps pipelines running for clean records, prevents database crashes, and creates a log of bad records for investigation and remediation.

### Q4: Why is it a bad practice to double-penalize records during completeness and validity checks?
**Answer**: If a column value is missing (null), it should be caught by a completeness check. If a validity formatting check (like regex or email format) also flags that null value as invalid, the same missing cell registers as two separate failures. This skews metrics and leads to alert fatigue. Validity rules should only evaluate *non-null* entries.

### Q5: How do you handle schema drift in automated pipelines?
**Answer**: Schema drift occurs when upstream sources add, remove, or change data types without notifying the data team. To handle it:
1. Implement a **Schema Profiler** at the ingestion gate.
2. Compare columns and types against a baseline schema.
3. If columns are missing or types are incompatible, block the pipeline (severity: `CRITICAL`) or log a warning and alert (severity: `WARNING`), routing bad records to quarantine.
4. Auto-promote schema additions when safe, or implement schema evolutionary strategies using Delta Lake or Iceberg.

---

## Section 2: Observability, Metrics & Alerting

### Q6: What is the difference between Data Quality Validation and Data Observability?
**Answer**: Data Quality validation is *active* and *gatekeeper-based* (running rules to reject or accept data). Data Observability is *passive* and *end-to-end* (monitoring pipeline health, data volume, schema changes, and lineage over time without blocking the pipeline). Observability focuses on answering *why* something broke, while validation blocks bad data at specific checkpoints.

### Q7: Explain "Alert Fatigue" and how your framework design mitigates it.
**Answer**: Alert fatigue occurs when too many non-actionable alerts are dispatched, leading engineers to ignore notifications. Our framework mitigates this by using severity levels:
- `INFO` / `WARNING`: Logged locally, recorded in metrics DB for trend analysis, but no instant alerts are sent.
- `ERROR` / `CRITICAL`: Instant alerts are sent to Slack or pager systems because they require immediate action (blocked pipeline, quarantined data).

### Q8: What is "Timeliness Validation" and how do you calculate latency and freshness?
**Answer**: Timeliness ensures data is available when needed.
- **Freshness**: Calculated as `current_timestamp - max(record_timestamp)`. It checks how recently the dataset was updated.
- **Latency (Ingestion delay)**: Calculated as `processing_timestamp - event_timestamp`. It checks how long it took for an event to travel from the source to the pipeline.

### Q9: How do you track data quality trends over time?
**Answer**: By writing metadata reports (execution status, row counts, pass rates) into a persistent operational database (like our SQLite tracker) at the end of every pipeline run. Data engineers can query this database to create reports showing if pass rates are declining or if certain rules fail frequently.

---

## Section 3: Technology & Tooling (Great Expectations, dbt, etc.)

### Q10: What are Great Expectations and what are its core concepts?
**Answer**: Great Expectations is an open-source library for validating data. Key concepts:
- **Expectations**: Declarative assertions about data (e.g. `expect_column_values_to_be_unique`).
- **ExpectationSuite**: A collection of Expectations.
- **Validation Operator / Runner**: Executes a suite against a dataset.
- **Data Docs**: Auto-generated HTML validation reports.

### Q11: How does Great Expectations validation compare to dbt tests?
**Answer**: 
- **dbt tests** are SQL-based, run against data already loaded in the warehouse, and evaluate data *at rest*.
- **Great Expectations** runs in Python/Spark, can validate data *in flight* (before writing to the warehouse), and provides more complex validation rules and statistical checks out of the box.

### Q12: How would you scale data quality validation to datasets containing hundreds of millions of rows?
**Answer**: Use **distributed compute engines** like Apache Spark. Pandas loads data into single-node RAM, which causes Out of Memory errors for large datasets. Tools like Great Expectations or custom rule engines can run on Spark DataFrames, distributing the validation logic across a cluster.

### Q13: What is "statistical profiling" in data quality?
**Answer**: Statistical profiling computes statistical properties of columns (mean, median, standard deviation, skewness, kurtosis) to check for anomalies. For example, if a column's values suddenly exceed three standard deviations from the historical mean (Z-Score > 3.0), they are flagged as outliers.

### Q14: How does referential integrity validation work in file-based storage systems (like S3/GCS)?
**Answer**: Unlike databases, object stores do not enforce foreign keys. Referential integrity is validated by loading the parent and child datasets into memory (or using a temporary query engine like Athena/DuckDB) and checking if child key values exist in the parent key set:
```python
invalid_rows = child_df[~child_df["parent_id"].isin(parent_df["id"])]
```
If `invalid_rows` is not empty, the rule fails.

### Q15: How can data quality issues be remediated automatically?
**Answer**: While critical failures need human intervention, simple issues can use automated remediation:
- Trimming whitespaces.
- Replacing nulls in non-critical fields with defaults.
- Parsing dates with multiple formats into a standardized ISO-8601 string.
- Standardizing country codes using lookup mappings (e.g., changing "US" to "USA").


---

## Section 4: Advanced Data Contracts, Lineage & Production Operations

### Q16: What is a Data Contract, and how does it shift data quality "left" to producers?
**Answer**: A Data Contract is a versioned YAML/JSON/Protobuf agreement between an upstream producer (microservice/API team) and downstream data consumers specifying column types, nullability, enum values, freshness SLAs, and PII tags. Enforcing contracts in producer CI/CD prevents breaking schema changes before bad data ever lands in Bronze.

### Q17: Explain the Write-Audit-Publish (WAP) pattern in data lakehouses.
**Answer**: Instead of writing directly to a live Gold table and checking quality afterward, WAP writes new data to an isolated branch/staging snapshot (e.g., Iceberg branch or Delta staging table), runs the full DQ assertion suite (`NullCheckRule`, `RowCountRule`, uniqueness), and **only publishes/fast-forwards** the pointer to production if every `CRITICAL` check passes.

### Q18: How do you handle seasonality when setting anomaly detection thresholds for row-count checks?
**Answer**: Static `min_rows` / `max_rows` rules break on Black Friday spikes or quiet Sunday traffic. Use day-of-week-aware rolling baselines (e.g., comparing Monday's count against the trailing 4–8 Mondays using IQR or seasonal Z-score bounds) to eliminate false-positive weekend alerts.

### Q19: What is the difference between hard-fail (`CRITICAL`) vs. soft-quarantine (`ERROR`) vs. warn (`WARNING`) actions?
**Answer**:
- **`CRITICAL` (Circuit Breaker):** Halts the pipeline before publishing (e.g., 0 rows extracted, missing primary key column).
- **`ERROR` (Quarantine):** Splits bad rows to a DLQ/quarantine sink while letting clean rows proceed (`partition_data()`).
- **`WARNING`:** Records telemetry and trends without blocking delivery (e.g., optional phone format mismatch).

### Q20: How do you test custom Data Quality rules themselves to avoid silent false-positives/negatives?
**Answer**: Treat DQ rules as production code—write `pytest` suites feeding edge-case DataFrames (all-nulls, empty DataFrames, duplicate keys, unicode strings, future timestamps) into `QualityEngine` and asserting exact pass/fail counts and quarantine splits.

### Q21: How do you prevent silent data duplication if a DQ-validated pipeline retries mid-load?
**Answer**: Pair DQ validation with idempotent loads (`MERGE INTO`, `replaceWhere`, or deterministic `run_id` partitioning) and log DQ execution metrics keyed by `(dataset_name, batch_id)` so retries don't double-count failures.

### Q22: Compare Great Expectations, Soda Core, and dbt Tests in a modern stack.
**Answer**:
- **Great Expectations:** Rich Python/Spark expectation library with auto-generated Data Docs, strong for Python/Spark ingestion gates.
- **Soda Core:** Declarative SodaCL YAML checks with fast SQL/Spark/Pandas runners and Soda Cloud observability.
- **dbt Tests:** Lightweight SQL `not_null`/`unique`/custom singular tests directly inside warehouse transformation DAGs.

### Q23: How do you validate PII leakage before data reaches analytical Gold marts?
**Answer**: Add regex/entropy scanners (checking for unmasked emails, SSNs, credit cards, API tokens) as mandatory `CRITICAL` rules on Silver-to-Gold promotion gates, blocking or redacting any leaked fields before BI tools query them.

### Q24: What metrics belong on a Data Quality Executive/Ops Dashboard?
**Answer**: Track 30-day rule pass rate %, quarantined row volume by rule type, freshness SLA compliance %, time-to-detect (TTD) & time-to-resolve (TTR), and top offending upstream source systems.

### Q25: How do you ensure Data Quality checks don't double pipeline compute costs on multi-terabyte tables?
**Answer**: Push checks down into the same single-pass Spark/SQL read where possible (computing `COUNT(*)`, `COUNT(col)`, `MIN/MAX`, and regex violations in one aggregation scan rather than 10 separate table scans), and scope checks incrementally to newly arrived partitions (`WHERE dt = '{{ ds }}'`).
