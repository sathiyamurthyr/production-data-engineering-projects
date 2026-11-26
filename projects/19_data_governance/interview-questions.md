# Interview Questions: Data Governance, RBAC & Lineage

This document contains curated, high-yield interview questions and professional answers regarding Data Governance, security, lineage, and compliance in Data Engineering.

---

## 1. How do you handle GDPR "Right to be Forgotten" (RTBF) requests in a modern Lakehouse architecture (e.g., Delta Lake or Apache Iceberg)?

### Answer
In traditional cloud storage (S3/GCS with raw CSV/Parquet), deleting a single user's record requires rewriting the entire data partition or file, which is extremely expensive and computationally slow.

In a modern **Lakehouse (Delta Lake / Iceberg)**, we handle RTBF using two primary approaches:

1. **Delete & Rewrite (Physical Erasure)**:
   We execute an ACID-compliant `DELETE` operation:
   ```sql
   DELETE FROM customers_silver WHERE customer_id = 'CUST_1001';
   ```
   To ensure the data is physically purged and not just logically marked as deleted in older file versions, we must run `VACUUM` with a zero retention period:
   ```sql
   VACUUM customers_silver RETAIN 0 HOURS;
   ```
2. **Crypto-Grred (Cryptographic Erasure)**:
   Instead of deleting rows, we encrypt each user's PII columns using a unique cryptographic key associated with that `customer_id`. The keys are stored in a secure key store (e.g. AWS KMS). When a user submits an RTBF request, we simply delete their unique key from the key store. The raw data remains, but it is rendered unreadable, undecryptable gibberish, fulfilling compliance requirements instantly without rewriting files.

---

## 2. What is the difference between a Metadata Catalog and a Business Glossary, and how do they interact?

### Answer
- **Metadata Catalog (Physical Layer)**: Stores information about physical schemas, database names, table locations, column datatypes, partition keys, and file formats (e.g., what columns are in `prod_dw.sales.orders`). It is usually populated automatically by crawlers.
- **Business Glossary (Logical Layer)**: Stores human-friendly business terms, definitions, categorization rules, and ownership information (e.g., defining what "Gross Revenue" means and who owns it). It is maintained by data stewards.

### Integration
They are mapped together via **semantic tagging**. For example, the physical column `cust_name` in the metadata catalog is linked to the Business Glossary term `Customer Name`, which carries classification rules (e.g. `sensitivity_level="RESTRICTED"`). This ensures classification policies flow automatically from glossary terms to physical data assets.

---

## 3. How do you track data lineage in a distributed execution framework like Apache Spark?

### Answer
Capturing data lineage in distributed Spark environments can be achieved through three primary patterns:

1. **Query Plan Parsing (Post-hoc/Active)**:
   We can parse Spark's logical and physical plans using Spark listeners. Tools like **Spline** or **OpenLineage** hook into Spark's `QueryExecutionListener` and extract inputs, transformations, and output targets to generate graph edges.
2. **dbt (Analytics Layer Lineage)**:
   For SQL transformations, **dbt** parses `ref()` statements in SELECT queries to build dependency models and compile lineage graphs.
3. **Execution Framework Hooking (Airflow/Dagster)**:
   We declare input and output datasets on task nodes inside orchestrators (e.g., Airflow inlets/outlets). This tracks lineage at the table level during runtime.

---

## 4. Explain the difference between RBAC and ABAC, and how they apply to column-level dynamic data masking.

### Answer
- **Role-Based Access Control (RBAC)**: Grants permissions based on a user's role (e.g. "DATA_ANALYST can read tables").
- **Attribute-Based Access Control (ABAC)**: Grants permissions based on attributes of the user, asset, and environment (e.g., "A user in the Finance department can read assets tagged as CONFIDENTIAL between 9 AM and 5 PM").

### Column-level Masking Application
A hybrid approach is typical. RBAC is used to define user capabilities (e.g., user is a `DATA_ANALYST` which has permission `read_masked_pii`). ABAC is used to check asset metadata (e.g., column is tagged `sensitivity_level="RESTRICTED"`).
During query compilation, the system evaluates the policy: if the column is `RESTRICTED` (ABAC) and the user only has `read_masked_pii` (RBAC), the execution plan dynamically modifies the query:
```sql
-- Original Query
SELECT ssn FROM users;

-- Compiled Query at runtime
SELECT mask_ssn(ssn) AS ssn FROM users;
```

---

## 5. What are the performance implications of dynamic data masking during query execution, and how do you optimize it?

### Answer
Dynamic data masking introduces CPU overhead because every row returned must pass through masking functions (e.g. SHA-256 hashing or regular expression redaction).

### Optimization Strategies
1. **Push-down Masking**: Apply masking after filtering (`WHERE` clauses) so only the final returned records are masked, avoiding execution over millions of scanned rows.
2. **Database View Materialization**: For read-heavy, low-latency applications, expose pre-masked materialized views or separate restricted tables, avoiding runtime calculations.
3. **Hardware Acceleration**: Use optimized database-level cryptographic builtins (e.g., SHA2 on Snowflake or Databricks) rather than custom UDFs.


---

## 6. What is the difference between Data Classification and Data Tagging, and how do they drive automated governance?
### Answer
- **Classification** identifies what sensitive information exists inside an asset (e.g., `PII_EMAIL`, `PCI_CARD`, `PHI`) via regex, ML classifiers, or column heuristics.
- **Tagging** attaches standardized governance labels (`sensitivity=RESTRICTED`, `retention_days=365`) onto catalog tables/columns so policy engines automatically apply masking, access restrictions, and retention TTLs without manual per-table rules.

---

## 7. How do OpenLineage and OpenMetadata work together in an enterprise governance stack?
### Answer
**OpenLineage** defines an open event standard emitted at runtime by Spark, Airflow, dbt, and Flink (`RunEvent` with inputs, outputs, and column-level transformations). **OpenMetadata** (or DataHub/Unity Catalog) ingests those events to render interactive end-to-end lineage graphs, impact analysis, and ownership alerts.

---

## 8. Explain Column-Level Lineage vs. Table-Level Lineage and why column-level matters for PII compliance.
### Answer
Table-level lineage only shows that `bronze.users -> gold.revenue_mart`. **Column-level lineage** proves that `bronze.users.ssn` was transformed via `SHA2()` (not copied raw) into `gold.revenue_mart.customer_hash`—giving compliance auditors verifiable proof that PII never propagated unmasked downstream.

---

## 9. How do you enforce Least Privilege Access Control in a Data Lakehouse without creating role explosion?
### Answer
Combine **RBAC** for broad domain roles (`finance_analyst`, `data_engineer`) with **ABAC (Tag-Based Policies)** on catalog classifications (`sensitivity=PII`). Instead of creating 500 table-specific roles, a single policy rule (*"Mask any column tagged `PII` unless caller has `pii_unmasked` attribute"*) scales across thousands of tables automatically.

---

## 10. What is Data Minimization and Retention Governance (`TTL`), and how do you automate it?
### Answer
Regulations like GDPR/CCPA prohibit keeping personal data indefinitely. Define explicit retention policies per asset class (e.g., raw clickstream logs purged after 90 days, financial ledgers retained 7 years), and run scheduled automated `DELETE` + `VACUUM` / S3 Lifecycle rules verified by compliance audit logs.

---

## 11. Compare Tokenization, Format-Preserving Encryption (FPE), and Deterministic Hashing (`HMAC`) for PII anonymization.
### Answer
- **HMAC-SHA256 (with secret salt):** Irreversible, deterministic (preserves `JOIN` and `COUNT(DISTINCT)` capability), fast, but cannot be unmasked later.
- **Format-Preserving Encryption (FPE):** Reversible with the key while keeping original string shape (e.g., 16-digit card format) so legacy schemas don't break.
- **Tokenization (Vault-backed):** Replaces sensitive values with random opaque tokens mapped in an isolated secure vault—strongest isolation for PCI/HIPAA.

---

## 12. Why is unsalted `SHA-256(email)` or `MD5(phone)` unsafe for anonymizing PII?
### Answer
Emails and 10-digit phone numbers have low entropy and predictable formats. An attacker with a rainbow table or GPU can brute-force all 10-billion phone numbers in minutes. Always use **HMAC-SHA256 with a rotated secret key/pepper** stored in KMS/Vault.

---

## 13. How do Data Owners vs. Data Stewards vs. Platform Admins divide responsibilities in Data Mesh / Governance?
### Answer
- **Data Owner:** Accountable business/domain lead who approves access requests and defines SLAs/sensitivity for a domain's data products.
- **Data Steward:** Curates business glossary definitions, verifies classification tags, and resolves quality/compliance issues.
- **Platform Admin:** Manages IAM/Unity Catalog infrastructure, KMS keys, audit logging pipelines, and policy engine guardrails.

---

## 14. How do you audit "who accessed what sensitive data and when" across SQL warehouses and Spark?
### Answer
Stream warehouse/catalog audit logs (Snowflake `ACCESS_HISTORY`, Databricks `system.access.audit`, AWS CloudTrail S3 Data Events) into a tamper-evident central audit log table, indexing `(principal, asset_uri, columns_accessed, timestamp, policy_applied)` for SIEM alerting and SOC2/GDPR audits.

---

## 15. How do you prevent accidental PII leakage into non-production (`dev`/`staging`) environments?
### Answer
Never clone raw production tables directly into `dev`/`qa`. Automate **synthetic data generation** or **de-identified staging pipelines** (applying deterministic masking/tokenization + row sampling) inside an isolated prod-to-nonprod promotion job.

---

## 16. How do Row-Level Security (RLS) policies work for multi-tenant data platforms?
### Answer
Attach a dynamic row filter predicate using session context (e.g., `WHERE tenant_id = CURRENT_TENANT()` or `IS_MEMBER(region_group)`). Even if an analyst runs `SELECT * FROM orders`, the engine injects the predicate at query compile time—never trusting client-supplied `tenant_id` parameters.

---

## 17. What happens to GDPR Right-to-Erasure when PII was already copied into backups, Kafka logs, or vector embeddings?
### Answer
- **Kafka:** Rely on short topic retention (`retention.ms`, e.g., 7 days) or **crypto-shredding** (encrypt message PII per `user_id` key and delete the key).
- **Backups / Time Travel:** Document backup TTL windows, use crypto-shredding for long-term archives, and enforce `VACUUM` cycles on Delta/Iceberg tables.
- **Vector Stores / RAG:** Redact PII *before* embedding and delete vectors by `doc_id` / `user_id` metadata on erasure requests.

---

## 18. How do you handle Data Discovery and PII detection on unstructured text and semi-structured JSON columns?
### Answer
Run automated scanners combining compiled regex patterns (email, SSN, credit card, API keys), Luhn/checksum validation (to reduce credit-card false positives), and NER models over sampled JSON/text payloads, writing confidence scores into the catalog metadata store.

---

## 19. How do you govern AI/LLM training and RAG data access inside an enterprise data platform?
### Answer
Apply the same catalog RBAC/ABAC governance to AI pipelines: filter unauthorized documents *before* vector retrieval (`acl_group` pre-filtering), sanitize PII/secrets prior to embedding, and log dataset lineage linking every model/vector index back to approved source tables.

---

## 20. How do you measure the ROI and adoption of a Data Governance program?
### Answer
Track concrete engineering metrics rather than slide decks: % of critical tables with owners & automated classification tags, reduction in access-request approval lead time via self-service RBAC, zero unmasked PII incidents in `dev`/BI, and % of pipelines emitting automated OpenLineage events.
