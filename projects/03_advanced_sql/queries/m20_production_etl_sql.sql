-- =============================================================================
-- Module 20: Production ETL Pipeline in SQL — Staging, Validation, Upsert, and Audit
-- =============================================================================
-- File        : m20_production_etl_sql.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Production SQL ETL pipelines combine staging ingestion, data quality validation, deduplication, atomic upserts, and pipeline execution logging into an enterprise pattern.
--
-- Pipeline Architectural Layers:
--   1. Audit Execution Log : Records job start/end timestamps, processed row counts, status ('SUCCESS'/'FAILED'), and error logs.
--   2. Data Quality Check  : Rejects records violating business constraints (NULL checks, non-negative bounds).
--   3. Deduplication CTE   : Isolates the latest valid record version per primary key using `ROW_NUMBER()`.
--   4. Production Target   : Idempotently upserts clean records into the production target table.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Enterprise ETL Pipelines : Scheduled batch sync between landing bucket staging tables and DW production analytical tables
-- • Audit & Governance       : SLA tracking and data lineage logging for compliance auditing
-- • Reliable Data Engineering: Guaranteed idempotent retries (pipeline can be re-run safely without duplicate rows)

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS etl_pipeline_audit_log (
    job_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name  TEXT NOT NULL,
    start_time     TEXT NOT NULL,
    end_time       TEXT,
    rows_processed INTEGER DEFAULT 0,
    status         TEXT NOT NULL, -- 'RUNNING', 'SUCCESS', 'FAILED'
    error_message  TEXT
);

CREATE TABLE IF NOT EXISTS stg_raw_transactions (
    raw_id         INTEGER PRIMARY KEY,
    txn_id         INTEGER NOT NULL,
    customer_id    INTEGER,
    amount         REAL,
    txn_timestamp  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prod_transactions (
    txn_id         INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL,
    amount         REAL NOT NULL,
    txn_timestamp  TEXT NOT NULL,
    loaded_at      TEXT NOT NULL
);

-- Seed Staging Table (Contains 1 valid row, 1 update row for txn 101, 1 invalid row with NULL customer)
INSERT INTO stg_raw_transactions (raw_id, txn_id, customer_id, amount, txn_timestamp)
VALUES
    (1, 101, 1001, 150.00, '2024-01-01 10:00:00'),
    (2, 101, 1001, 175.00, '2024-01-01 10:05:00'), -- Newer update for 101
    (3, 102, NULL, 200.00, '2024-01-01 10:10:00'), -- INVALID (NULL customer)
    (4, 103, 1002, 500.00, '2024-01-01 10:15:00')  -- Valid row
ON CONFLICT(raw_id) DO NOTHING;

-- =============================================================================
-- STEP 1: Start Pipeline Execution & Register Audit Log Entry
-- =============================================================================

INSERT INTO etl_pipeline_audit_log (pipeline_name, start_time, status)
VALUES ('SYNC_RAW_TO_PROD_TRANSACTIONS', DATETIME('now'), 'RUNNING');

-- =============================================================================
-- STEP 2: Execute Data Quality Filter, Deduplication, and Idempotent Target Load
-- =============================================================================

WITH valid_cleaned_data AS (
    SELECT
        txn_id,
        customer_id,
        amount,
        txn_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY txn_id
            ORDER BY txn_timestamp DESC, raw_id DESC
        ) AS rn
    FROM stg_raw_transactions
    WHERE customer_id IS NOT NULL  -- Quality Check 1: Mandatory non-null key
      AND amount IS NOT NULL       -- Quality Check 2: Mandatory non-null amount
      AND amount > 0               -- Quality Check 3: Non-negative amount
),
deduped_staging AS (
    SELECT txn_id, customer_id, amount, txn_timestamp
    FROM valid_cleaned_data
    WHERE rn = 1
)
INSERT INTO prod_transactions (txn_id, customer_id, amount, txn_timestamp, loaded_at)
SELECT
    txn_id,
    customer_id,
    amount,
    txn_timestamp,
    DATETIME('now') AS loaded_at
FROM deduped_staging
ON CONFLICT(txn_id) DO UPDATE SET
    customer_id   = EXCLUDED.customer_id,
    amount        = EXCLUDED.amount,
    txn_timestamp = EXCLUDED.txn_timestamp,
    loaded_at     = EXCLUDED.loaded_at
WHERE EXCLUDED.txn_timestamp >= prod_transactions.txn_timestamp;

-- =============================================================================
-- STEP 3: Complete Pipeline Execution Audit Log
-- =============================================================================

UPDATE etl_pipeline_audit_log
SET
    end_time       = DATETIME('now'),
    rows_processed = (SELECT COUNT(*) FROM prod_transactions),
    status         = 'SUCCESS'
WHERE pipeline_name = 'SYNC_RAW_TO_PROD_TRANSACTIONS'
  AND status = 'RUNNING';

-- Verify Target Production State
SELECT * FROM prod_transactions ORDER BY txn_id;

-- Expected Output:
-- txn_id | customer_id | amount | txn_timestamp       | loaded_at
-- 101    | 1001        | 175.0  | 2024-01-01 10:05:00 | <current_ts>
-- 103    | 1002        | 500.0  | 2024-01-01 10:15:00 | <current_ts>

-- Verify Audit Log State
SELECT * FROM etl_pipeline_audit_log ORDER BY job_id DESC;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Deduplicating via window function in a CTE evaluates in memory in a single pass before hitting the disk load phase.
-- 2. Audit logs provide operational observability to calculate historical pipeline SLA execution duration trends.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Always isolate raw staging ingestion from downstream production loading.
-- TIP 2: Wrap the entire pipeline execution inside an explicit transaction block (`BEGIN TRANSACTION ... COMMIT`) to ensure atomicity.
-- TIP 3: Log invalid quarantined records into an `etl_quarantine_records` table for data quality debugging.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Loading raw unvalidated data directly into production gold tables.
-- MISTAKE 2: Leaving pipeline audit logs stuck in 'RUNNING' status when unhandled SQL exceptions occur.
-- MISTAKE 3: Writing non-idempotent ETL scripts that duplicate rows when re-run after a pipeline crash.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What makes an ETL pipeline "Idempotent"?
--     A: An idempotent pipeline produces identical, clean target states regardless of how many times it is executed with the same input dataset.
-- Q2: Why is a Quarantine table essential in production data engineering pipelines?
--     A: It captures bad or corrupt records failing validation checks, allowing downstream processing of good records to proceed without halting the entire job.
-- Q3: What metadata should be captured in a production Pipeline Audit Log?
--     A: Pipeline Name, Execution Job ID, Start Timestamp, End Timestamp, Input Row Count, Target Insert/Update Count, Quarantine Count, Execution Status, and Error Stack Traces.
-- Q4: How do you handle pipeline failures mid-execution to prevent partial data writes?
--     A: Wrap the ETL operations in an atomic transaction (`BEGIN TRANSACTION ... COMMIT / ROLLBACK`), ensuring either all target mutations succeed or none take effect.
-- Q5: What is the Medallion Architecture (Bronze -> Silver -> Gold)?
--     A: Bronze = Raw appended ingestion, Silver = Cleaned, deduplicated, and validated data, Gold = Aggregated, business-level dimensional star schemas for BI consumption.
