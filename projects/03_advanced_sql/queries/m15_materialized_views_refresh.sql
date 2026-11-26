-- =============================================================================
-- Module 15: Materialized Views and Refresh Strategies
-- =============================================================================
-- File        : m15_materialized_views_refresh.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite (via table caching simulation) | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Materialized Views physically store the calculated result set of a query on disk.
-- Unlike standard Virtual Views (which execute their underlying query on every access), Materialized Views trade storage space for fast read query latency.
--
-- Refresh Mechanics:
--   1. Full Refresh        : Truncates and rebuilds the entire materialized table.
--   2. Concurrent Refresh  : Updates records in-place without acquiring exclusive read locks (requires UNIQUE index).
--   3. Incremental Refresh : Delta-loads only records modified since the last refresh watermark.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Executive Dashboards  : Caching complex multi-join KPI aggregates for instant BI dashboard loading
-- • Data Lakehouse Layers : Materializing Gold-layer analytical aggregates from Silver-layer Delta tables
-- • Microservices APIs     : Pre-computing product search filter counts to avoid overloading transaction databases

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders_raw (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    order_date   TEXT NOT NULL,
    amount       REAL NOT NULL,
    status       TEXT NOT NULL
);

INSERT INTO orders_raw (order_id, customer_id, order_date, amount, status)
VALUES
    (1, 101, '2024-01-15', 500.00, 'COMPLETED'),
    (2, 101, '2024-01-16', 300.00, 'COMPLETED'),
    (3, 102, '2024-01-16', 450.00, 'COMPLETED'),
    (4, 103, '2024-01-17', 200.00, 'REFUNDED'),
    (5, 102, '2024-01-18', 600.00, 'COMPLETED')
ON CONFLICT(order_id) DO NOTHING;

-- Simulated Materialized Table Caching Strategy for SQLite/PostgreSQL
CREATE TABLE IF NOT EXISTS mv_customer_sales_summary (
    customer_id        INTEGER PRIMARY KEY,
    total_orders       INTEGER NOT NULL,
    completed_revenue  REAL NOT NULL,
    last_order_date    TEXT NOT NULL,
    refreshed_at       TEXT NOT NULL
);

-- =============================================================================
-- QUERY 1: Populate / Full Refresh Materialized View
-- =============================================================================

DELETE FROM mv_customer_sales_summary;

INSERT INTO mv_customer_sales_summary (customer_id, total_orders, completed_revenue, last_order_date, refreshed_at)
SELECT
    customer_id,
    COUNT(order_id) AS total_orders,
    SUM(CASE WHEN status = 'COMPLETED' THEN amount ELSE 0.0 END) AS completed_revenue,
    MAX(order_date) AS last_order_date,
    DATETIME('now') AS refreshed_at
FROM orders_raw
GROUP BY customer_id;

-- Query the cached summary view
SELECT * FROM mv_customer_sales_summary ORDER BY completed_revenue DESC;

-- Expected Output:
-- customer_id | total_orders | completed_revenue | last_order_date
-- 102         | 2            | 1050.0            | 2024-01-18
-- 101         | 2            | 800.0             | 2024-01-16
-- 103         | 1            | 0.0               | 2024-01-17

-- =============================================================================
-- QUERY 2: PostgreSQL Native Materialized View Syntax Reference
-- =============================================================================
/*
-- Create Materialized View
CREATE MATERIALIZED VIEW mv_daily_sales_pg AS
SELECT
    order_date,
    COUNT(*) AS total_orders,
    SUM(amount) AS total_revenue
FROM orders_raw
WHERE status = 'COMPLETED'
GROUP BY order_date;

-- Create Unique Index required for CONCURRENT refresh
CREATE UNIQUE INDEX idx_mv_daily_sales_date ON mv_daily_sales_pg(order_date);

-- Concurrent Refresh (non-blocking for concurrent SELECT queries)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_pg;
*/

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Standard `REFRESH MATERIALIZED VIEW` acquires an Exclusive Lock on the view, blocking concurrent SELECT queries until refresh completes.
-- 2. `REFRESH MATERIALIZED VIEW CONCURRENTLY` in PostgreSQL uses a temporary diff table and requires a UNIQUE index on the materialized view.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Add indexes directly to the Materialized View columns to speed up downstream BI queries.
-- TIP 2: Schedule background cron jobs or Airflow tasks to refresh heavy materialized views off-peak hours.
-- TIP 3: In Snowflake/Databricks, use Incremental Materialized Views (Dynamic Tables / Materialized Lakehouse Views) for automated zero-copy delta maintenance.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Expecting Materialized Views to update automatically on underlying table writes (standard SQL MVs require explicit REFRESH commands!).
-- MISTAKE 2: Running `REFRESH CONCURRENTLY` without defining a UNIQUE index on the materialized view columns.
-- MISTAKE 3: Materializing simple queries where standard indexing on the base table provides equivalent sub-millisecond response times.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the core difference between a Virtual View and a Materialized View?
--     A: Virtual View is stored SQL text executed on every access (zero extra storage); Materialized View stores pre-computed query results on disk for fast read response.
-- Q2: How does `REFRESH MATERIALIZED VIEW CONCURRENTLY` work in PostgreSQL?
--     A: It generates the new view dataset in a temporary table, compares differences against the existing view using a UNIQUE index, and applies IN-PLACE updates without locking read queries.
-- Q3: When should you avoid using Materialized Views?
--     A: When source tables update constantly with real-time requirements, or when the view refresh duration exceeds the reporting freshness threshold.
-- Q4: What is an Incremental Materialized View?
--     A: A materialized view that updates only the modified delta rows since the last watermark rather than recalculating the entire dataset from scratch.
-- Q5: How do indexes on Materialized Views work?
--     A: Materialized views behave like physical tables on disk; you can create B-tree, Hash, or GIN indexes directly on their columns to accelerate queries.
