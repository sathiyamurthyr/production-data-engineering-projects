-- =============================================================================
-- Module 11: Advanced Slowly Changing Dimension Type 2 (SCD Type 2)
-- =============================================================================
-- File        : m11_scd_type2_implementation.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Slowly Changing Dimension Type 2 (SCD2) tracks historical changes in dimension attributes over time by creating new record versions.
--
-- Core SCD Type 2 Attributes:
--   • Business Key (Natural Key) : Permanent entity identifier (e.g. employee_id)
--   • Surrogate Key             : Unique primary key for each historical version (e.g. dim_employee_sk)
--   • Effective Range           : `valid_from` and `valid_to` timestamps
--   • Current Version Indicator : `is_current` boolean flag (1 = active version, 0 = historic version)

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • HR Analytics          : Tracking employee salary changes, manager changes, and department transfers over time
-- • Customer Data Warehouse: Preserving historical address and tier status for historical revenue attribution
-- • Product Master Data   : Tracking price changes and category re-classifications across fiscal years

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_employee_scd2 (
    employee_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    department    TEXT NOT NULL,
    salary        REAL NOT NULL,
    valid_from    TEXT NOT NULL,
    valid_to      TEXT NOT NULL,
    is_current    INTEGER NOT NULL  -- 1 = True, 0 = False
);

-- Initial Population (Version 1 for Employee 101)
INSERT INTO dim_employee_scd2 (employee_id, employee_name, department, salary, valid_from, valid_to, is_current)
VALUES
    (101, 'Alice Smith', 'Engineering', 90000.00, '2024-01-01 00:00:00', '9999-12-31 23:59:59', 1),
    (102, 'Bob Jones',   'Sales',       75000.00, '2024-01-01 00:00:00', '9999-12-31 23:59:59', 1)
ON CONFLICT DO NOTHING;

-- Staging table with updated record for Alice (Department transfer & raise)
CREATE TABLE IF NOT EXISTS staging_employee_updates (
    employee_id   INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department    TEXT NOT NULL,
    salary        REAL NOT NULL,
    effective_ts  TEXT NOT NULL
);

INSERT INTO staging_employee_updates (employee_id, employee_name, department, salary, effective_ts)
VALUES
    (101, 'Alice Smith', 'Product Tech', 110000.00, '2024-06-01 00:00:00')
ON CONFLICT(employee_id) DO NOTHING;

-- =============================================================================
-- STEP 1: Invalidate Current Active Version for Changed Employees
-- =============================================================================

UPDATE dim_employee_scd2
SET
    valid_to   = (
        SELECT effective_ts
        FROM staging_employee_updates s
        WHERE s.employee_id = dim_employee_scd2.employee_id
    ),
    is_current = 0
WHERE is_current = 1
  AND employee_id IN (
      SELECT s.employee_id
      FROM staging_employee_updates s
      JOIN dim_employee_scd2 d ON s.employee_id = d.employee_id AND d.is_current = 1
      WHERE s.department <> d.department OR s.salary <> d.salary
  );

-- =============================================================================
-- STEP 2: Insert New Version (Version 2) into SCD2 Dimension Table
-- =============================================================================

INSERT INTO dim_employee_scd2 (employee_id, employee_name, department, salary, valid_from, valid_to, is_current)
SELECT
    s.employee_id,
    s.employee_name,
    s.department,
    s.salary,
    s.effective_ts AS valid_from,
    '9999-12-31 23:59:59' AS valid_to,
    1 AS is_current
FROM staging_employee_updates s
JOIN dim_employee_scd2 d ON s.employee_id = d.employee_id
WHERE d.is_current = 0 AND d.valid_to = s.effective_ts;

-- =============================================================================
-- QUERY 3: Point-in-Time Historical Dimension Querying
-- =============================================================================
-- Query: What was Alice's department and salary on '2024-03-15'?

SELECT
    employee_id,
    employee_name,
    department,
    salary,
    valid_from,
    valid_to
FROM dim_employee_scd2
WHERE employee_id = 101
  AND '2024-03-15 00:00:00' BETWEEN valid_from AND valid_to;

-- Query: What is Alice's current department and salary today?
SELECT
    employee_id,
    employee_name,
    department,
    salary
FROM dim_employee_scd2
WHERE employee_id = 101
  AND is_current = 1;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Indexing `(employee_id, is_current)` is essential to ensure step 1 updates perform index lookup rather than full table scans.
-- 2. Indexing `(employee_id, valid_from, valid_to)` speeds up Point-in-Time point queries in DW queries.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Use high sentinel dates like `'9999-12-31 23:59:59'` instead of NULL for `valid_to` to allow simpler `BETWEEN` indexing.
-- TIP 2: Wrap invalidation and insertion inside an explicit database transaction block (`BEGIN TRANSACTION ... COMMIT`).
-- TIP 3: Use dbt `snapshot` features or Delta Lake `SCD Type 2` merge patterns in production platforms.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Overlapping effective ranges (`valid_to` of v1 equal to `valid_from` of v2 causes double counting in strict `BETWEEN` queries). Subtract 1 second/microsecond if using discrete bounds.
-- MISTAKE 2: Updating surrogate keys of historical versions instead of inserting a new surrogate key.
-- MISTAKE 3: Forgetting to filter `is_current = 1` in standard operational reporting queries.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the difference between SCD Type 1, SCD Type 2, and SCD Type 3?
--     A: Type 1 overwrites old data (no history); Type 2 inserts new rows with validity dates (full history); Type 3 adds a "previous_value" column to store prior state (partial history).
-- Q2: Why is a Surrogate Key mandatory in an SCD Type 2 dimension?
--     A: Because the Natural Key (employee_id) repeats across multiple historical rows. The Surrogate Key serves as the unique Primary Key.
-- Q3: How do you join a Fact table to an SCD Type 2 Dimension table?
--     A: Join Fact to Dimension on `Fact.employee_id = Dim.employee_id AND Fact.event_timestamp BETWEEN Dim.valid_from AND Dim.valid_to` (or join pre-resolved Surrogate Keys).
-- Q4: What is the advantage of using `'9999-12-31'` as valid_to instead of NULL?
--     A: Enables standard `BETWEEN valid_from AND valid_to` predicate filtering without needing complex `OR valid_to IS NULL` logic that degrades index usage.
-- Q5: How do you handle out-of-order historical event ingestion in SCD Type 2 tables?
--     A: Insert the historical version, re-calculate and adjust `valid_from` and `valid_to` bounds for adjacent records using window functions (`LEAD/LAG`).
