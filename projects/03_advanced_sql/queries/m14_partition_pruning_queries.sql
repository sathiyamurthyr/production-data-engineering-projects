-- =============================================================================
-- Module 14: Partition Pruning and Partitioning Strategies
-- =============================================================================
-- File        : m14_partition_pruning_queries.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite (via CTE simulation) | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Partitioning divides large tables into smaller, manageable child physical tables or storage files (e.g. Parquet/ORC partitions).
--
-- Key Partition Concepts:
--   1. Partition Pruning : The query optimizer skips reading physical partitions/files that do not match WHERE predicates.
--   2. Range Partitioning: Divided by numerical or date ranges (e.g. `order_date BY MONTH`).
--   3. List Partitioning : Divided by discrete categories (e.g. `region IN ('US', 'EU')`).
--   4. Hash Partitioning : Distributed evenly across N buckets using a hash function over a key.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • High-Volume Event Logging : Partitioning clickstream tables by `event_date` to prune 99% of historical storage during daily queries
-- • Multi-Tenant Enterprise Data: List partitioning by `tenant_id` to isolate customer data access
-- • Data Archival & Lifecycle   : Instant drop of historical data via `DROP PARTITION` instead of slow row-by-row `DELETE`

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS partitioned_orders (
    order_id     INTEGER PRIMARY KEY,
    order_date   TEXT NOT NULL,
    country_code TEXT NOT NULL,
    total_amount REAL NOT NULL
);

INSERT INTO partitioned_orders (order_id, order_date, country_code, total_amount)
VALUES
    (101, '2024-01-15', 'US', 250.00),
    (102, '2024-01-20', 'US', 180.00),
    (103, '2024-02-10', 'CA', 320.00),
    (104, '2024-02-15', 'US', 150.00),
    (105, '2024-03-01', 'UK', 400.00)
ON CONFLICT(order_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Static Partition Pruning (Filtering by Partition Key)
-- =============================================================================
-- The query planner statically identifies the exact partition ('2024-01') at compile time.

SELECT
    order_id,
    order_date,
    country_code,
    total_amount
FROM partitioned_orders
WHERE order_date >= '2024-01-01'
  AND order_date <  '2024-02-01'
ORDER BY order_date;

-- Expected Output:
-- order_id | order_date | country_code | total_amount
-- 101      | 2024-01-15 | US           | 250.0
-- 102      | 2024-01-20 | US           | 180.0

-- =============================================================================
-- QUERY 2: Dynamic Partition Pruning via Subquery / Join
-- =============================================================================
-- The engine prunes partitions dynamically at runtime based on dimension table filter outputs.

WITH active_countries AS (
    SELECT 'US' AS country_code
)
SELECT
    o.order_id,
    o.order_date,
    o.country_code,
    o.total_amount
FROM partitioned_orders o
JOIN active_countries c ON o.country_code = c.country_code
WHERE o.order_date >= '2024-01-01'
ORDER BY o.order_id;

-- =============================================================================
-- QUERY 3: PostgreSQL Declarative Partitioning Syntax Reference
-- =============================================================================
/*
-- Master Partitioned Table
CREATE TABLE orders_pg (
    order_id     BIGINT NOT NULL,
    order_date   DATE NOT NULL,
    total_amount NUMERIC(12,2)
) PARTITION BY RANGE (order_date);

-- Child Partitions
CREATE TABLE orders_y2024m01 PARTITION OF orders_pg
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE orders_y2024m02 PARTITION OF orders_pg
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
*/

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Ensure `enable_partition_pruning = on` in PostgreSQL / query settings.
-- 2. Partitioning on high-cardinality columns (e.g. `user_id`) creates millions of small files/partitions ("Small File Problem"), degrading metastore performance.
-- 3. Optimal partition sizes in analytical data lakes (Delta Lake / Iceberg) range from 100 MB to 1 GB per partition file.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Avoid applying non-SARGable functions to partition key columns (`WHERE strftime('%Y', order_date) = '2024'` disables static pruning!).
-- TIP 2: Combine Partitioning with Clustering / Sorting Keys (e.g. Partition by Date, Cluster by Customer ID).
-- TIP 3: Drop entire partitions (`ALTER TABLE DROP PARTITION ...`) for fast retention pruning rather than running `DELETE WHERE date < ...`.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Over-partitioning by day when daily data volume is under 10 MB.
-- MISTAKE 2: Joining partitioned tables without including the partition key in the JOIN clause.
-- MISTAKE 3: Expecting indexes on partitioned tables to compensate for missing partition key filters in WHERE clauses.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is Partition Pruning and how does it improve query performance?
--     A: It is a query optimizer feature that evaluates `WHERE` predicates against table partition metadata, bypassing physical scans of unneeded files/child tables.
-- Q2: What is the "Small File Problem" in partitioned Data Lakes?
--     A: Over-partitioning (e.g. by hour or user_id) creates millions of tiny files. Metastore list operations and file open overhead degrade query latency significantly.
-- Q3: Difference between Static Partition Pruning and Dynamic Partition Pruning (DPP)?
--     A: Static pruning occurs at query compilation time using explicit literal filters; Dynamic pruning occurs at runtime when partition keys are matched against dynamic join results.
-- Q4: How do you instantly purge 3-year-old data from a 10 TB table?
--     A: Execute `ALTER TABLE orders DROP PARTITION p_2021;` which drops physical storage files instantaneously without generating transaction WAL logs.
-- Q5: Can a table be partitioned by multiple columns?
--     A: Yes, composite partitioning (e.g., Range Partitioning by `year_month` sub-partitioned by List `region`).
