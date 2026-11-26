-- =============================================================================
-- Module 05: Window Frame Specifications — ROWS, RANGE, and GROUPS
-- =============================================================================
-- File        : m05_window_frame_specs.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Window frame specifications define the exact subset of rows within a partition
-- over which aggregate window functions (SUM, AVG, MIN, MAX, COUNT, FIRST_VALUE) operate.
--
-- Frame Clause Syntax:
--   { ROWS | RANGE | GROUPS } BETWEEN frame_start AND frame_end
--
-- Frame Bounds:
--   UNBOUNDED PRECEDING : Start of partition
--   N PRECEDING         : N rows/values/groups before current
--   CURRENT ROW         : Current row/value/group
--   N FOLLOWING         : N rows/values/groups after current
--   UNBOUNDED FOLLOWING : End of partition
--
-- Differences:
--   ROWS   : Physical row offset (e.g. 2 rows before to current row)
--   RANGE  : Logical value offset (e.g. values within range of current value)
--   GROUPS : Peer group offset based on ORDER BY duplicates

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Financial Analytics : Moving averages over physical windows (3-day moving avg)
-- • E-Commerce           : Daily revenue trend smoothing with centered window frames
-- • IoT / Telemetry      : Sliding window aggregations over sensor readings
-- • Risk Management     : 7-day lookback rolling maximum drawdowns

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS daily_metrics (
    metric_id     INTEGER PRIMARY KEY,
    metric_date   TEXT NOT NULL,
    store_id      INTEGER NOT NULL,
    daily_revenue REAL NOT NULL,
    transaction_cnt INTEGER NOT NULL
);

INSERT INTO daily_metrics (metric_id, metric_date, store_id, daily_revenue, transaction_cnt)
VALUES
    (1,  '2024-01-01', 101, 1000.00, 50),
    (2,  '2024-01-02', 101, 1200.00, 55),
    (3,  '2024-01-03', 101,  800.00, 40),
    (4,  '2024-01-04', 101, 1500.00, 70),
    (5,  '2024-01-05', 101, 1300.00, 65),
    (6,  '2024-01-06', 101, 1700.00, 80),
    (7,  '2024-01-07', 101, 1100.00, 52),
    (8,  '2024-01-01', 102, 2000.00, 90),
    (9,  '2024-01-02', 102, 2200.00, 95),
    (10, '2024-01-03', 102, 2100.00, 88)
ON CONFLICT(metric_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: ROWS Frame — 3-Day Moving Average & 3-Day Running Sum
-- =============================================================================

SELECT
    metric_date,
    store_id,
    daily_revenue,
    -- 3-Day Moving Average (2 PRECEDING AND CURRENT ROW)
    ROUND(AVG(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_3d,

    -- 3-Day Rolling Sum
    SUM(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_sum_3d,

    -- Full cumulative sum from start of partition to current row
    SUM(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_revenue
FROM daily_metrics
WHERE store_id = 101
ORDER BY metric_date;

-- =============================================================================
-- QUERY 2: Centered Window Frame — 1 Preceding, Current Row, 1 Following
-- =============================================================================
-- Centered moving average smooths noise by looking both backward and forward.

SELECT
    metric_date,
    daily_revenue,
    ROUND(AVG(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ), 2) AS centered_avg_3d,
    MIN(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS window_min,
    MAX(daily_revenue) OVER (
        PARTITION BY store_id
        ORDER BY metric_date
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS window_max
FROM daily_metrics
WHERE store_id = 101
ORDER BY metric_date;

-- =============================================================================
-- QUERY 3: RANGE vs ROWS comparison with Duplicate Order Keys
-- =============================================================================
-- Demonstrates how RANGE treats peer rows (identical ORDER BY values) vs ROWS

SELECT
    metric_id,
    metric_date,
    daily_revenue,
    -- ROWS: Treats each physical row separately
    SUM(daily_revenue) OVER (
        ORDER BY daily_revenue
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS sum_rows,

    -- RANGE: Includes all peers with same daily_revenue in the sum frame
    SUM(daily_revenue) OVER (
        ORDER BY daily_revenue
        RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS sum_range
FROM daily_metrics
ORDER BY daily_revenue;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Default frame when ORDER BY is present is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
-- 2. Explicitly specifying ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW avoids RANGE peer evaluation overhead.
-- 3. Partition keys must be indexed (store_id, metric_date) for window function efficiency.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Prefer ROWS over RANGE for performance unless peer grouping logic is required.
-- TIP 2: Reuse WINDOW clauses (WINDOW w AS (...)) to simplify queries with multiple frames.
-- TIP 3: Keep window frames bounded (e.g. 7 PRECEDING) rather than UNBOUNDED to reduce memory footprints.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Assuming default frame includes all rows (it only includes up to CURRENT ROW when ORDER BY is set).
-- MISTAKE 2: Using RANGE with non-deterministic ordering without realizing peer aggregation occurs.
-- MISTAKE 3: Forgetting PARTITION BY when operating across multi-tenant data.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the default window frame when an ORDER BY clause is provided in OVER()?
--     A: RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
-- Q2: Difference between ROWS BETWEEN and RANGE BETWEEN?
--     A: ROWS counts physical rows; RANGE evaluates logical values/peers based on the ORDER BY expression.
-- Q3: How do you write a 7-day centered moving average window frame?
--     A: ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING.
-- Q4: Why is ROWS faster than RANGE in PostgreSQL/Snowflake?
--     A: ROWS doesn't need to inspect future rows for duplicate ORDER BY values (peers).
-- Q5: How do you get the total sum of partition across all rows regardless of current row index?
--     A: ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING (or omit ORDER BY).
