# 05. Palantir Foundry, Ontology & Contour — Interview Q&A

---

## Part A: Foundry Platform, Ontology & Core Tools

### Q1: What is the Ontology in Palantir Foundry, and why is it important?
**Answer:**
The Foundry Ontology is the semantic "digital twin" of an organization sitting on top of physical datasets and models. It maps raw tables into business-meaningful **Object Types**, **Properties**, **Link Types**, **Action Types**, and **Use Cases**:
- **Object Type:** Real-world entity or event (e.g., `Customer`, `Transaction`, `Merchant`).
- **Property:** Attribute on an Object Type (e.g., `amount`, `risk_rating`).
- **Link Type:** Directed semantic relationship between Object Types (e.g., `Customer -> PLACED -> Order`).
- **Action Type:** Governed write-back rule allowing operational users/apps to modify objects with validation and audit trails.
- **Importance:** Decouples physical storage from consumption, enforces object-level ACLs & lineage, and powers no-code/low-code operational apps (**Object Explorer**, **Quiver**, **Workshop**) alongside code transforms.

---

### Q2: Compare Foundry's core tools: **Code Repositories (Contour/Transforms)**, **Pipeline Builder**, **Fusion**, **Object Explorer**, **Quiver**, and **Workshop**.
**Answer:**
| Tool | Primary Purpose | Best For |
|---|---|---|
| **Code Repositories / Transforms** | Git-backed Python, PySpark, and SQL pipelines (`@transform`, `@incremental`) | Production ETL/ELT, API ingestion, complex joins, unit testing |
| **Pipeline Builder** | Low-/no-code visual DAG pipeline authoring | Rapid, schema-safe batch/incremental transformations |
| **Contour** | Exploratory visual analysis over any dataset (with expression/board logic) | Drilling down into tabular datasets, filtering, charts, PDF exports |
| **Fusion** | Spreadsheet-like low-code business interface | Business-user tabular modeling and integration with Foundry datasets |
| **Object Explorer** | Search & explore Ontology Objects and linked object sets | Investigating entities, filtering, bulk Actions (write-back) |
| **Quiver** | Visual & time-series analytics strictly over **Ontology Objects** | Linked object drill-downs, time-series charts, embeddable dashboards |
| **Workshop** | Interactive operational app builder over the Ontology | Custom multi-step UI workflows, embedding Quiver + Actions write-back |

---

### Q3: Explain Foundry Dataset, Transform, Vertex, `@incremental`, and `@external_systems`.
**Answer:**
- **Dataset:** A versioned, immutable collection of tabular data (Parquet/CSV backed) with branch isolation (`master`, feature branches) and full transaction history.
- **Transform (`@transform`):** A deterministic unit of processing logic mapping declared input datasets to output datasets.
- **Vertex:** An individual processing step/node in a pipeline DAG (read, filter, join, write).
- **`@incremental`:** Decorator enabling partition/transaction-aware incremental reads (`inputs.df("added")`) and incremental appends instead of reprocessing full history on every build.
- **`@external_systems`:** Securely injects configured external Source credentials/clients (REST APIs, JDBC, S3) into Python transforms without hardcoding secrets.

---

### Q4: Compare **Data Health** vs. **Data Lineage** in Foundry.
**Answer:**
| Aspect | **Data Health** | **Data Lineage** |
|---|---|---|
| **Definition** | Monitors quality, freshness, schema, and completeness checks | Traces end-to-end data flow from origin to downstream apps |
| **Questions Answered** | *"Is this dataset accurate, timely, and non-empty?"* | *"Where did this KPI come from, and what breaks if I change it?"* |
| **Output** | Build check alerts, health status badges, failure notifications | Interactive dependency graph across transforms, Ontology & apps |

---

## Part B: Technical Troubleshooting & PySpark/API in Foundry

### Q5: What does `_corrupt_record` mean, and why can all Spark DataFrame rows become `NULL` after a POST REST API call?
**Answer:**
- **`_corrupt_record`** appears when `spark.read.json` encounters JSON records that fail parsing or violate the explicit `StructType` schema.
- **All-NULL rows after API POST:** Usually caused by passing raw unparsed strings instead of serialized JSON objects into `sc.parallelize([json.dumps(item) for item in data_list])`, or a schema mismatch (case sensitivity / nested wrapper like `{"data": [...]}` not unwrapped before `read.json()`).
- **Fix:** Inspect `data_list[0]`, unwrap the payload array, verify column names/types match the `StructType`, and filter `_corrupt_record IS NOT NULL` into an error dataset.

---

### Q6: You try to partition by `transactionID` and get an `AnalysisException: cannot resolve 'transactionID'`. Why?
**Answer:**
1. The API JSON had a different casing/key (`transaction_id` vs `transactionID`) or failed JSON parsing into `_corrupt_record` so the expected column wasn't projected.
2. **Fix:** Run `df.printSchema()`, inspect `data_list[0]`, align the schema/select expression, and verify the column exists before `.repartition()` or `.partitionBy()`.

---

### Q7: How do you handle Schema Drift and Schema Evolution in Foundry pipelines?
**Answer:**
1. Define explicit `StructType` schemas for critical financial fields (`transaction_id`, `amount`) with nullable optional fields.
2. Enable Schema Management Policies / `mergeSchema=true` only for safe additive columns, or capture unexpected fields into a JSON `extra_attributes` / `_rescued_data` column.
3. Add **Data Health** schema-check gates that alert on unexpected column renames (e.g., `amount` → `txn_amount`) before downstream Ontology syncs break.

---

### Q8: How do you design an end-to-end Pipeline in Foundry (Step-by-Step)?
**Answer:**
1. **Ingestion Layer:** Connect JDBC/S3/REST APIs via **Data Connections** + `@external_systems`, writing raw immutable payloads into Bronze datasets.
2. **Transform & Cleansing Layer:** Use **Code Repositories** (PySpark) / **Pipeline Builder** with `@incremental`, deduplicating on `(transactionID, transactionDate)`, casting amounts (`DoubleType`), parsing timestamps (`to_timestamp`), and routing `_corrupt_record` rows to a quarantine dataset.
3. **Ontology Mapping:** Map cleansed Silver/Gold datasets to Ontology Object Types, Link Types, and Action Types.
4. **Governance & Security:** Apply Marking/Organization ACLs, column masking for PII (`accountNumber`, `IFSC`), and Egress policies.
5. **Monitoring & Scheduling:** Configure Data Health checks (freshness, null/schema assertions), build schedules, and Data Lineage reviews.

---

## Part C: Scenario-Based & System Design Q&As

### Q9: Scenario — An external REST API intermittently returns malformed JSON, HTTP 429/500 errors, or duplicate transactions. How do you build a resilient ingestion pipeline?
**Answer:**
1. **API Resilience:** Wrap HTTP calls inside `@external_systems` with exponential backoff retries (handling `429`/`5xx`, failing fast on `400`/`401`) and structured logging (`logging` / `ctx.log`).
2. **Schema & Corrupt Record Isolation:** Parse payloads with an explicit `StructType` + `_corrupt_record` in `PERMISSIVE` mode, routing malformed rows to a dedicated DLQ/error dataset while letting valid rows proceed.
3. **Deduplication:** Deduplicate deterministically using `Window.partitionBy("transactionID", "transactionDate").orderBy(F.col("ingested_at").desc())` (row number = 1) or `dropDuplicates(["transactionID", "transactionDate"])`, plus a SHA-256 row hash for change tracking.

---

### Q10: Scenario — Credit/debit fields arrive as strings (sometimes `"-"` or commas `"1,250.50"`). How do you clean and cast them safely?
**Answer:**
```python
from pyspark.sql import functions as F

cleaned_df = df.withColumn(
    "amount_clean",
    F.when(F.trim(F.col("amount")).isin("", "-", "N/A", "null"), F.lit(None))
    .otherwise(F.regexp_replace(F.trim(F.col("amount")), ",", ""))
    .cast("double")
)
```
Then add a Data Health check flagging unexpected spikes in `amount_clean IS NULL`.

---

### Q11: Scenario — How would you partition a large financial transaction dataset in Foundry, and avoid skew?
**Answer:**
- Choose **low-to-medium cardinality** filter keys such as `transactionDate` (or `transactionMonth`) and optionally `service`—never high-cardinality `transactionID` (which creates millions of tiny files).
- Before writing, verify partition skew (`groupBy(key).count()`), and use `repartition(N, "transactionDate")` or `coalesce()` to target 128–256 MB Parquet files.

---

### Q12: Scenario — How do you secure PII (`accountNumber`, `IFSC`) while allowing authorized compliance audits?
**Answer:**
1. Separate raw restricted ingestion datasets into a privileged **Marking / Project folder** accessible only to compliance/platform admins.
2. In the Silver → Gold / Ontology transform, apply deterministic **HMAC-SHA256 tokenization** or partial masking (`XXXX1234`) for general analysts and BI apps.
3. Expose unmasked views/objects only via strict **RBAC/Markings** and audit all access through Foundry's security & lineage logs.

---

### Q13: System Design — How do you structure a pipeline joining real-time payment API data with a historical ledger for fraud detection?
**Answer:**
1. **Streaming / Micro-Batch Ingestion:** Ingest live payment events into a partitioned Bronze dataset (with checkpoints/incremental watermarks).
2. **Historical Feature Enrichment:** Maintain pre-aggregated customer/merchant velocity & baseline stats in an incrementally updated Gold ledger table.
3. **Stream-Static / Incremental Join:** Join incoming payment events with broadcast/partition-pruned historical ledger profiles, apply deterministic fraud rules + ML scoring, materialize alerts into an Ontology `FraudAlert` Object Type, and wire an **Action Type** in **Workshop** for analyst review/write-back.

---

### Q14: How do you unit-test Foundry transforms and debug slowness?
**Answer:**
- **Testing:** Separate pure PySpark transform logic from Foundry I/O wrappers so unit tests run locally with `pytest` + a local `SparkSession` fixture over edge-case DataFrames (nulls, duplicates, malformed JSON), plus branch builds in Foundry CI.
- **Debugging Slowness:** Check Foundry's **Lineage / Build Metrics** and Spark DAG (`Jobs`/`Stages` tabs) for wide shuffles, `explain(True)` physical plans, skewed partition sizes, missing broadcast hints, or repeated re-computation (fix by persisting/materializing intermediate datasets).

---

## Part D: Behavioral Questions (STAR Method Framework)

### Q15: Tell me about a time a production pipeline failed due to unexpected upstream schema/API changes.
**Answer (STAR Template):**
- **Situation:** An upstream payment API renamed/altered a numeric field (`"-"` instead of `0.0`), causing downstream nightly ledger aggregation to fail.
- **Task:** Restore the SLA quickly without losing valid transactions and prevent recurrence.
- **Action:** Isolated corrupt records via `_corrupt_record` into an error dataset, added defensive string-to-double sanitization, and added automated **Data Health** schema/null assertions + Slack alerts at the Bronze boundary.
- **Result:** Pipeline recovered within SLA, zero valid transactions were lost, and subsequent upstream drift triggered early warnings before hitting Gold/Ontology.

---

### Q16: Describe resolving inconsistent financial data across multiple APIs with non-technical stakeholders.
**Answer (STAR Template):**
- **Situation:** Wallet and UPI APIs reported slightly different settlement totals due to rounding and fee-deduction timing.
- **Task:** Reconcile discrepancies and align finance stakeholders on one source of truth.
- **Action:** Built automated reconciliation checks comparing transaction-level rounding, timestamps, and status codes; flagged mismatches in a summary report; and explained findings to finance without jargon using labeled dashboards and Lineage views.
- **Result:** Upstream API rounding bugs were fixed, reconciliation gaps dropped to zero, and finance gained full confidence in the Ontology metrics.

---

### Q17: How do you handle vague requirements when integrating unknown external APIs, or balance competing priorities?
**Answer:**
- **Ambiguity:** Start with API discovery (sample `POST`/`GET` responses, pagination, rate limits, error codes), document an explicit data contract (`StructType` + SLA + PII fields), build a small vertical Bronze → Silver prototype on a feature branch, and validate sample outputs with domain stakeholders before scaling.
- **Competing Priorities:** Triage by **blast radius & SLA impact**—fix P0/P1 production pipeline integrity/data-correctness bugs first, communicate transparent ETAs for lower-priority dashboard optimizations, and convert recurring manual fixes into automated guardrails afterward.
