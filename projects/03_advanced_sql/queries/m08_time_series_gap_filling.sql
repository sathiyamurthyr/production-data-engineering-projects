-- =============================================================================
-- Module 08: Time Series Gap Filling and Interpolation
-- =============================================================================
-- File        : m08_time_series_gap_filling.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Real-world time series data (telemetry, transactions, clickstreams) often has missing dates or timestamps.
-- Missing data causes reporting errors in moving averages and time-series charts.
--
-- Essential Patterns:
--   1. Date Spine Generation : Generate a continuous list of dates using recursive CTEs or calendar dimensions.
--   2. Zero Filling         : LEFT JOIN date spine with actuals and use `COALESCE(sales, 0)`.
--   3. LOCF (Last Observation Carried Forward) : Carry forward the last non-null value into missing periods.
--   4. Linear Interpolation : Calculate intermediate missing values based on adjacent known datapoints.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • E-Commerce Dashboards : Continuous daily sales charts without missing weekend dates
-- • Financial Reporting   : Asset price carry-forward over weekends and market holidays (LOCF)
-- • IoT Sensors           : Filling missing temperature / pressure readings via linear interpolation
-- • Product Analytics     : Daily Active Users (DAU) retention reporting over uninterrupted calendar spines

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS product_daily_sales (
    sale_date    TEXT NOT NULL,
    product_id   INTEGER NOT NULL,
    units_sold   INTEGER NOT NULL,
    unit_price   REAL NOT NULL,
    PRIMARY KEY (sale_date, product_id)
);

INSERT INTO product_daily_sales (sale_date, product_id, units_sold, unit_price)
VALUES
    ('2024-01-01', 501, 10, 100.00),
    ('2024-01-02', 501, 15, 100.00),
    -- Gap: 2024-01-03 missing
    ('2024-01-04', 501, 20, 105.00),
    -- Gap: 2024-01-05 missing
    -- Gap: 2024-01-06 missing
    ('2024-01-07', 501, 30, 110.00)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: Continuous Date Spine & Zero-Filling Missing Days
-- =============================================================================

WITH RECURSIVE date_spine(spine_date) AS (
    SELECT '2024-01-01'
    UNION ALL
    SELECT DATE(spine_date, '+1 day')
    FROM date_spine
    WHERE spine_date < '2024-01-07'
)
SELECT
    ds.spine_date,
    501 AS product_id,
    COALESCE(pds.units_sold, 0) AS units_sold,
    COALESCE(pds.units_sold * pds.unit_price, 0.0) AS daily_revenue
FROM date_spine ds
LEFT JOIN product_daily_sales pds
    ON ds.spine_date = pds.sale_date
   AND pds.product_id = 501
ORDER BY ds.spine_date;

-- Expected Output:
-- spine_date | product_id | units_sold | daily_revenue
-- 2024-01-01 | 501        | 10         | 1000.0
-- 2024-01-02 | 501        | 15         | 1500.0
-- 2024-01-03 | 501        | 0          | 0.0
-- 2024-01-04 | 501        | 20         | 2100.0
-- 2024-01-05 | 501        | 0          | 0.0
-- 2024-01-06 | 501        | 0          | 0.0
-- 2024-01-07 | 501        | 30         | 3300.0

-- =============================================================================
-- QUERY 2: Last Observation Carried Forward (LOCF) for Prices
-- =============================================================================

WITH RECURSIVE date_spine(spine_date) AS (
    SELECT '2024-01-01'
    UNION ALL
    SELECT DATE(spine_date, '+1 day')
    FROM date_spine
    WHERE spine_date < '2024-01-07'
),
raw_filled AS (
    SELECT
        ds.spine_date,
        pds.unit_price,
        -- Create a grouping key whenever price is NOT NULL
        COUNT(pds.unit_price) OVER (ORDER BY ds.spine_date) AS value_partition
    FROM date_spine ds
    LEFT JOIN product_daily_sales pds
        ON ds.spine_date = pds.sale_date
       AND pds.product_id = 501
)
SELECT
    spine_date,
    unit_price AS actual_price,
    -- LOCF: Carry forward the first non-null price in the partition group
    FIRST_VALUE(unit_price) OVER (
        PARTITION BY value_partition
        ORDER BY spine_date
    ) AS locf_unit_price
FROM raw_filled
ORDER BY spine_date;

-- Expected Output:
-- spine_date | actual_price | locf_unit_price
-- 2024-01-01 | 100.0        | 100.0
-- 2024-01-02 | 100.0        | 100.0
-- 2024-01-03 | NULL         | 100.0
-- 2024-01-04 | 105.0        | 105.0
-- 2024-01-05 | NULL         | 105.0
-- 2024-01-06 | NULL         | 105.0
-- 2024-01-07 | 110.0        | 110.0

-- =============================================================================
-- QUERY 3: Linear Interpolation for Missing Units Sold
-- =============================================================================
-- Linear Formula: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)

WITH RECURSIVE date_spine(spine_date) AS (
    SELECT '2024-01-01'
    UNION ALL
    SELECT DATE(spine_date, '+1 day')
    FROM date_spine
    WHERE spine_date < '2024-01-07'
),
spine_joined AS (
    SELECT
        ds.spine_date,
        pds.units_sold,
        JULIANDAY(ds.spine_date) AS x
    FROM date_spine ds
    LEFT JOIN product_daily_sales pds
        ON ds.spine_date = pds.sale_date AND pds.product_id = 501
),
bounds AS (
    SELECT
        spine_date,
        units_sold,
        x,
        -- Previous known point (x1, y1)
        MAX(CASE WHEN units_sold IS NOT NULL THEN x END) OVER (ORDER BY x ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS x1,
        MAX(CASE WHEN units_sold IS NOT NULL THEN units_sold END) OVER (ORDER BY x ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS y1,
        -- Next known point (x2, y2)
        MIN(CASE WHEN units_sold IS NOT NULL THEN x END) OVER (ORDER BY x ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS x2,
        MIN(CASE WHEN units_sold IS NOT NULL THEN units_sold END) OVER (ORDER BY x ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS y2
    FROM spine_joined
)
SELECT
    spine_date,
    units_sold AS raw_units,
    CASE
        WHEN units_sold IS NOT NULL THEN CAST(units_sold AS REAL)
        WHEN x1 IS NULL OR x2 IS NULL OR x1 = x2 THEN y1
        ELSE ROUND(y1 + (x - x1) * (y2 - y1) / (x2 - x1), 2)
    END AS interpolated_units
FROM bounds
ORDER BY spine_date;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. In high-volume data warehouses (Snowflake, BigQuery), maintain a permanent `dim_calendar` table rather than using recursive CTEs.
-- 2. `COUNT(column) OVER (ORDER BY ...)` trick for LOCF is an O(N) operation compared to costly subquery lookups.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Filter the date spine to the min/max dates of the actual dataset to prevent unnecessary outer joins.
-- TIP 2: Materialize calendar tables with holiday flags, fiscal quarters, and weekend indicators for fast dashboard joins.
-- TIP 3: In Snowflake or Databricks, use built-in functions like `IGFF / IGNORES NULLS` with `LAG()` / `LEAD()`.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Outer joining date spine on single table when multiple products exist without cross joining product dimension first (causes dropped product combinations).
-- MISTAKE 2: Dividing by zero in interpolation when x2 = x1.
-- MISTAKE 3: Using `COALESCE(val, 0)` for price fields where carrying forward the last known price (LOCF) is business requirement.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is LOCF in time-series analysis and how do you write it in ANSI SQL?
--     A: Last Observation Carried Forward. In PostgreSQL/Snowflake, use `LAG(val IGNORE NULLS)` or `COUNT(val) OVER ()` grouping combined with `FIRST_VALUE()`.
-- Q2: How do you handle missing dates across 1,000 products simultaneously?
--     A: CROSS JOIN the Product dimension with the Date Spine, then LEFT JOIN the transactional sales data.
-- Q3: Why is a recursive CTE not ideal for date spines spanning 50 years?
--     A: Recursive CTE execution exceeds maximum recursion depth limits. A physical `dim_date` dimension table is standard practice.
-- Q4: What is the difference between zero-filling and linear interpolation?
--     A: Zero-filling replaces missing values with 0 (appropriate for discrete events like sales counts); interpolation computes smooth estimated values based on surrounding trend points (appropriate for continuous metrics like temperature or prices).
-- Q5: How do you write a portable date spine generator in SQLite vs PostgreSQL?
--     A: In SQLite: `WITH RECURSIVE date_spine(d) AS (SELECT '2024-01-01' UNION ALL SELECT DATE(d, '+1 day') ...)`
--        In PostgreSQL: `SELECT generate_series('2024-01-01'::date, '2024-01-31'::date, '1 day'::interval)`.
