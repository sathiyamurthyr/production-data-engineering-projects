-- =============================================================================
-- Module 06: Running Totals and Moving Averages
-- =============================================================================
-- File        : m06_running_totals_moving_avg.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Running totals (cumulative sums) and moving averages (rolling averages) are foundational
-- patterns in analytical engineering and stream processing.
-- They allow calculating continuous aggregates without expensive self-joins or procedurals.
--
-- Key Window Patterns:
--   • Cumulative Sum      : SUM(val) OVER (PARTITION BY ... ORDER BY ... ROWS UNBOUNDED PRECEDING)
--   • Rolling Moving Avg  : AVG(val) OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN N PRECEDING AND CURRENT ROW)
--   • YTD Cumulative Reset: Reset accumulation on year boundary using PARTITION BY year

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Executive Dashboards  : Cumulative Year-To-Date (YTD) Revenue Tracking
-- • FinTech / Banking     : Real-time Account Balance Calculation from ledger events
-- • E-Commerce Analytics  : 7-day and 30-day moving average order volume to smooth weekend seasonality
-- • SRE / DevOps          : Rolling average latency tracking for SLA alerts

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ledger_transactions (
    txn_id        INTEGER PRIMARY KEY,
    account_id    INTEGER NOT NULL,
    txn_date      TEXT NOT NULL,
    txn_amount    REAL NOT NULL,
    txn_type      TEXT NOT NULL  -- 'CREDIT' or 'DEBIT'
);

INSERT INTO ledger_transactions (txn_id, account_id, txn_date, txn_amount, txn_type)
VALUES
    (1,  1001, '2024-01-01',  500.00, 'CREDIT'),
    (2,  1001, '2024-01-02', -150.00, 'DEBIT'),
    (3,  1001, '2024-01-03',  200.00, 'CREDIT'),
    (4,  1001, '2024-01-04',  -50.00, 'DEBIT'),
    (5,  1001, '2024-01-05',  300.00, 'CREDIT'),
    (6,  1001, '2024-01-06', -100.00, 'DEBIT'),
    (7,  1001, '2024-01-07',  400.00, 'CREDIT'),
    (8,  1002, '2024-01-01', 1000.00, 'CREDIT'),
    (9,  1002, '2024-01-02', -300.00, 'DEBIT'),
    (10, 1002, '2024-01-03', -200.00, 'DEBIT')
ON CONFLICT(txn_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Running Account Balance (Cumulative Sum per Account)
-- =============================================================================

SELECT
    txn_id,
    account_id,
    txn_date,
    txn_type,
    txn_amount,
    -- Running balance calculation
    SUM(txn_amount) OVER (
        PARTITION BY account_id
        ORDER BY txn_date, txn_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance,
    -- Maximum balance seen up to this transaction
    MAX(txn_amount) OVER (
        PARTITION BY account_id
        ORDER BY txn_date, txn_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS peak_single_credit
FROM ledger_transactions
ORDER BY account_id, txn_date, txn_id;

-- =============================================================================
-- QUERY 2: 3-Day Rolling Moving Average & Moving Standard Deviation
-- =============================================================================

SELECT
    account_id,
    txn_date,
    txn_amount,
    -- 3-transaction moving average
    ROUND(AVG(txn_amount) OVER (
        PARTITION BY account_id
        ORDER BY txn_date, txn_id
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_3txn,
    -- Running total count of transactions
    COUNT(txn_id) OVER (
        PARTITION BY account_id
        ORDER BY txn_date, txn_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_txn_count
FROM ledger_transactions
WHERE account_id = 1001
ORDER BY txn_date, txn_id;

-- =============================================================================
-- QUERY 3: Year-to-Date (YTD) Cumulative Total Resetting by Year
-- =============================================================================

WITH dated_txns AS (
    SELECT
        account_id,
        txn_date,
        SUBSTR(txn_date, 1, 4) AS txn_year,
        txn_amount
    FROM ledger_transactions
)
SELECT
    account_id,
    txn_date,
    txn_year,
    txn_amount,
    SUM(txn_amount) OVER (
        PARTITION BY account_id, txn_year
        ORDER BY txn_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS ytd_running_total
FROM dated_txns
ORDER BY account_id, txn_date;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Indexing `(account_id, txn_date, txn_id)` is vital for index-only scans during window sorting.
-- 2. ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW is highly optimized in modern query planners.
-- 3. Avoid subqueries for running totals when window functions can accomplish it in O(N log N) time.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Always include a unique tie-breaker column (e.g., txn_id) in ORDER BY to guarantee deterministic running totals.
-- TIP 2: Use window aliases (WINDOW w AS (...)) when computing multiple aggregates over the same window.
-- TIP 3: Pre-aggregate high-frequency transaction data into daily metrics before calculating moving averages for reporting.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Non-deterministic ordering in ORDER BY leading to unstable running balance values when multiple events occur on the same date.
-- MISTAKE 2: Forgetting PARTITION BY when querying across multiple accounts or customers.
-- MISTAKE 3: Using self-joins (`t1 JOIN t2 ON t2.date <= t1.date`) which result in O(N^2) complexity instead of O(N).

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: How do you handle tie-breakers in running totals to avoid non-deterministic output?
--     A: Include a unique primary key column (e.g. order_id, txn_id) as the secondary sort column in the window ORDER BY.
-- Q2: How does a self-join running total compare with a window function running total in terms of complexity?
--     A: Self-join is O(N^2) time and memory; Window function is O(N log N) time and O(1) memory per partition.
-- Q3: How do you reset a running total every month or year in SQL?
--     A: Include the year or month component in the PARTITION BY clause: `PARTITION BY account_id, strftime('%Y', txn_date)`.
-- Q4: Can you calculate moving averages over physical time intervals (e.g. 7 days) if dates have missing gaps?
--     A: Yes, by using RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW (in Postgres/Snowflake) or pre-filling date gaps with a date spine.
-- Q5: What is the effect of NULL values in running total calculations?
--     A: Aggregate functions like SUM() ignore NULLs, but if all values in the window frame are NULL, the function returns NULL. Wrap with COALESCE if necessary.
