-- =============================================================================
-- Module 13: Query Tuning and Execution Plan Optimization
-- =============================================================================
-- File        : m13_query_tuning_execution_plans.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Production query tuning focuses on reducing I/O, memory footprint, and CPU execution time.
--
-- Essential Optimization Vectors:
--   1. Execution Plan Inspection : Using EXPLAIN ANALYZE to identify sequential scans, nested loops, and hash spills.
--   2. SARGability (Search Argumentable) : Writing predicates so the query planner can utilize index range scans instead of full scans.
--   3. Subquery Unnesting        : Converting correlated scalar subqueries into Hash / Merge Joins.
--   4. Indexing Strategies       : Composite B-tree indexes, covering indexes, and partial indexes.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • High-Throughput APIs  : Reducing sub-second database response times for operational customer portals
-- • ETL Pipeline Tuning   : Reducing nightly data warehouse run times from hours to minutes
-- • Infrastructure Savings : Lowering Snowflake / Redshift compute warehouse sizing costs by 50%+

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS web_logs (
    log_id       INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL,
    url_path     TEXT NOT NULL,
    status_code  INTEGER NOT NULL,
    response_ms  REAL NOT NULL,
    created_at   TEXT NOT NULL
);

INSERT INTO web_logs (log_id, user_id, url_path, status_code, response_ms, created_at)
VALUES
    (1, 101, '/home',        200, 45.2, '2024-01-01 10:00:00'),
    (2, 101, '/checkout',    200, 120.5,'2024-01-01 10:05:00'),
    (3, 102, '/products',    500, 850.0,'2024-01-01 10:06:00'),
    (4, 103, '/cart',        200, 30.0, '2024-01-01 10:10:00'),
    (5, 102, '/home',        200, 50.0, '2024-01-01 10:12:00')
ON CONFLICT(log_id) DO NOTHING;

-- Index for optimized SARGable lookup
CREATE INDEX IF NOT EXISTS idx_web_logs_user_status
    ON web_logs(user_id, status_code);

CREATE INDEX IF NOT EXISTS idx_web_logs_created_at
    ON web_logs(created_at);

-- =============================================================================
-- QUERY 1: EXPLAIN Query Plan Inspection (SQLite / PostgreSQL Syntax)
-- =============================================================================

EXPLAIN QUERY PLAN
SELECT user_id, COUNT(*) AS error_count
FROM web_logs
WHERE status_code = 500
GROUP BY user_id;

-- =============================================================================
-- QUERY 2: Anti-Pattern vs SARGable Optimization
-- =============================================================================

-- ❌ ANTI-PATTERN: Wrapping indexed column in function (Forces Full Table Scan)
-- SELECT * FROM web_logs WHERE SUBSTR(created_at, 1, 10) = '2024-01-01';

-- ✅ SARGABLE OPTIMIZATION: Index Range Scan
SELECT log_id, user_id, url_path, created_at
FROM web_logs
WHERE created_at >= '2024-01-01 00:00:00'
  AND created_at <  '2024-01-02 00:00:00';

-- =============================================================================
-- QUERY 3: Converting Correlated Scalar Subquery to Optimized JOIN
-- =============================================================================

-- ❌ ANTI-PATTERN: Correlated Subquery evaluated O(N) times
-- SELECT l1.user_id, l1.url_path, l1.response_ms
-- FROM web_logs l1
-- WHERE l1.response_ms = (
--     SELECT MAX(l2.response_ms) FROM web_logs l2 WHERE l2.user_id = l1.user_id
-- );

-- ✅ OPTIMIZED: CTE with ROW_NUMBER() evaluated in single O(N log N) pass
WITH ranked_logs AS (
    SELECT
        user_id,
        url_path,
        response_ms,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY response_ms DESC
        ) AS rn
    FROM web_logs
)
SELECT user_id, url_path, response_ms
FROM ranked_logs
WHERE rn = 1
ORDER BY user_id;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. `EXPLAIN ANALYZE` executes the query and reports actual buffer page hits, execution time, and row estimates vs actuals.
-- 2. Composite indexes should place equality columns first, followed by range filter columns (`(status_code, created_at)`).
-- 3. Avoid SELECT *; retrieving unneeded text columns wastes buffer cache and network I/O.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Create Partial Indexes for high-cardinality flags (`CREATE INDEX idx_errors ON web_logs(created_at) WHERE status_code >= 500;`).
-- TIP 2: Update table statistics regularly (`ANALYZE web_logs;`) so the query optimizer selects optimal Hash Join vs Nested Loop strategies.
-- TIP 3: Eliminate `DISTINCT` when `GROUP BY` or proper JOIN conditions already ensure row uniqueness.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Applying functions or arithmetic calculations to indexed columns on the left side of WHERE clauses (`WHERE amount * 1.1 > 100`).
-- MISTAKE 2: Over-indexing tables (degrades INSERT/UPDATE throughput due to index maintenance overhead).
-- MISTAKE 3: Trusting estimated query costs without checking actual timing execution via `EXPLAIN ANALYZE`.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What does "SARGable" stand for in SQL query tuning?
--     A: Search Argumentable. It means a predicate can leverage index tree structures directly (e.g. `col >= val` rather than `FUNC(col) = val`).
-- Q2: What is the difference between a Sequential Scan, Index Scan, and Index Only Scan?
--     A: Sequential Scan reads all table pages; Index Scan uses B-Tree index pointers to read heap pages; Index Only Scan satisfies the query entirely from index memory pages without touching table data files.
-- Q3: When is a Hash Join preferred over a Nested Loop Join by the query planner?
--     A: Hash Join is preferred when joining large, unindexed datasets where one side can fit into memory (WorkMem). Nested Loop is preferred for small datasets with indexed join keys.
-- Q4: Why can `SELECT *` degrade query performance even if row counts are small?
--     A: Prevents the query engine from performing Index-Only Scans, forces wide row deserialization, and increases network bandwidth consumption.
-- Q5: What is a Covering Index?
--     A: An index that includes all columns requested by a query (either in key columns or `INCLUDE` clause), eliminating heap lookup operations.
