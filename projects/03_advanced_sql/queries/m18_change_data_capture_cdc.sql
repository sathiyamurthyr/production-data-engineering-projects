-- =============================================================================
-- Module 18: Change Data Capture (CDC) Stream Processing
-- =============================================================================
-- File        : m18_change_data_capture_cdc.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Change Data Capture (CDC) streams (Debezium, Fivetran, Kafka Connect) capture transactional row-level changes from source databases.
--
-- CDC Event Payload Attributes:
--   • Operation Type (`cdc_op`) : 'I' (Insert), 'U' (Update), 'D' (Delete)
--   • Sequence Number / LSN     : `lsn_id` or `cdc_timestamp` ensuring strict temporal ordering
--   • Record State              : Row column values as of the event moment

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Real-time Data Warehousing: Synchronizing Postgres OLTP changes into Snowflake/Databricks Bronze lakehouse tables
-- • Audit Trail Preservation : Maintaining 100% append-only historical log of all database mutations
-- • Operational Replicas      : Building real-time read replicas without running expensive full-table queries

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cdc_orders_stream (
    cdc_id        INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL,
    customer_id   INTEGER NOT NULL,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL,
    cdc_op        TEXT NOT NULL, -- 'I', 'U', 'D'
    lsn_seq       INTEGER NOT NULL,
    cdc_timestamp TEXT NOT NULL
);

INSERT INTO cdc_orders_stream (cdc_id, order_id, customer_id, amount, status, cdc_op, lsn_seq, cdc_timestamp)
VALUES
    (1, 501, 10, 100.00, 'PENDING',   'I', 1001, '2024-01-01 10:00:00'),
    (2, 501, 10, 100.00, 'PROCESSING','U', 1002, '2024-01-01 10:05:00'),
    (3, 501, 10, 100.00, 'SHIPPED',   'U', 1003, '2024-01-01 10:10:00'),
    (4, 502, 20, 250.00, 'PENDING',   'I', 1004, '2024-01-01 10:15:00'),
    (5, 502, 20, 250.00, 'CANCELLED', 'U', 1005, '2024-01-01 10:20:00'),
    (6, 502, 20, 250.00, 'CANCELLED', 'D', 1006, '2024-01-01 10:25:00') -- Deleted
ON CONFLICT(cdc_id) DO NOTHING;

-- Target Snapshot Table
CREATE TABLE IF NOT EXISTS orders_current_snapshot (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL,
    last_updated  TEXT NOT NULL
);

-- =============================================================================
-- QUERY 1: Extract Latest Non-Deleted Snapshot View from Raw CDC Log
-- =============================================================================

WITH ranked_cdc AS (
    SELECT
        order_id,
        customer_id,
        amount,
        status,
        cdc_op,
        cdc_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY lsn_seq DESC, cdc_timestamp DESC
        ) AS rn
    FROM cdc_orders_stream
)
SELECT
    order_id,
    customer_id,
    amount,
    status,
    cdc_timestamp AS last_updated
FROM ranked_cdc
WHERE rn = 1
  AND cdc_op <> 'D' -- Filter out deleted records
ORDER BY order_id;

-- Expected Output:
-- order_id | customer_id | amount | status  | last_updated
-- 501      | 10          | 100.0  | SHIPPED | 2024-01-01 10:10:00
-- (Order 502 is excluded because its latest cdc_op is 'D')

-- =============================================================================
-- QUERY 2: Materialize CDC Stream into Target Snapshot Table (ETL Ingestion)
-- =============================================================================

DELETE FROM orders_current_snapshot;

INSERT INTO orders_current_snapshot (order_id, customer_id, amount, status, last_updated)
WITH ranked_cdc AS (
    SELECT
        order_id,
        customer_id,
        amount,
        status,
        cdc_op,
        cdc_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY lsn_seq DESC
        ) AS rn
    FROM cdc_orders_stream
)
SELECT
    order_id,
    customer_id,
    amount,
    status,
    cdc_timestamp
FROM ranked_cdc
WHERE rn = 1
  AND cdc_op <> 'D';

SELECT * FROM orders_current_snapshot ORDER BY order_id;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. `(order_id, lsn_seq DESC)` index is mandatory to avoid full table sorts on billion-row CDC stream tables.
-- 2. CDC events can arrive out-of-order over network streams; always rely on source `lsn_seq` or transactional `commit_timestamp` rather than ingestion arrival time.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Micro-batch CDC deduplication using window functions before running MERGE operations into target Delta/Iceberg tables.
-- TIP 2: Retain raw CDC streams in immutable partitioning formats (`year/month/day`) for audit compliance and replay capabilities.
-- TIP 3: Filter soft-deleted records (`cdc_op = 'D'`) early in staging CTEs to minimize target join overhead.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Relying on ingestion wall-clock time (`NOW()`) instead of source database commit sequence (`lsn_seq`) for ordering updates.
-- MISTAKE 2: Forgetting to handle operation 'D' (Deletes), causing deleted source records to remain active in target data warehouses.
-- MISTAKE 3: Updating target snapshot tables row-by-row instead of set-based batch deduplication via window functions.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is Change Data Capture (CDC) and how does it differ from traditional batch ETL?
--     A: CDC captures continuous row-level mutations (inserts/updates/deletes) directly from database transaction logs in near real-time, whereas batch ETL extracts periodic bulk snapshots.
-- Q2: How do you handle out-of-order events in a CDC pipeline using SQL?
--     A: Use window function `ROW_NUMBER() OVER (PARTITION BY primary_key ORDER BY lsn_sequence DESC)` to isolate the true latest state regardless of arrival order.
-- Q3: What are LSNs in CDC streams?
--     A: Log Sequence Numbers. Monotonically increasing 64-bit integers generated by source relational databases (Postgres WAL, MySQL Binlog) identifying the exact commit position of a transaction.
-- Q4: How do you process hard deletes ('D') in CDC data lake tables?
--     A: Maintain soft-delete flags (`is_deleted = TRUE`) or filter them out during target snapshot materialization CTEs.
-- Q5: What is the purpose of keeping raw CDC tables in Lakehouse storage?
--     A: Complete auditability, time-travel debugging, and the ability to replay state history from scratch whenever business logic changes.
