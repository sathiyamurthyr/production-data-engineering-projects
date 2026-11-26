-- =============================================================================
-- Module 10: Multi-Dimensional Aggregations — GROUPING SETS, ROLLUP, and CUBE
-- =============================================================================
-- File        : m10_grouping_sets_rollup_cube.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite (via UNION ALL emulation) | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- In OLAP reporting, dashboards require aggregations at multiple granularity levels:
--   • Subtotals per Product
--   • Subtotals per Region
--   • Grand Totals across all dimensions
--
-- Modern SQL provides specialized clause extensions for multi-dimensional aggregation:
--   1. GROUPING SETS : Explicitly defines exact dimension combinations to aggregate.
--   2. ROLLUP        : Generates hierarchical subtotals (e.g. Year -> Quarter -> Month -> Grand Total).
--   3. CUBE          : Generates all $2^N$ possible cross-tabulation combinations of N dimensions.
--   4. GROUPING()    : Returns 1 if column is aggregated (NULL due to subtotal) and 0 if actual value.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Executive Financial Reports : Revenue rolled up by Country, State, City, and Company Grand Total
-- • Sales Dashboards            : Matrix cross-tabulations of Sales by Category vs Sales Channel
-- • Supply Chain Analytics      : Inventory counts aggregated by Warehouse, Aisle, and Global Total

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS regional_sales (
    sales_id    INTEGER PRIMARY KEY,
    year        INTEGER NOT NULL,
    region      TEXT NOT NULL,
    category    TEXT NOT NULL,
    amount      REAL NOT NULL
);

INSERT INTO regional_sales (sales_id, year, region, category, amount)
VALUES
    (1, 2024, 'NORTH', 'ELECTRONICS', 50000.00),
    (2, 2024, 'NORTH', 'FURNITURE',   20000.00),
    (3, 2024, 'SOUTH', 'ELECTRONICS', 45000.00),
    (4, 2024, 'SOUTH', 'FURNITURE',   30000.00),
    (5, 2023, 'NORTH', 'ELECTRONICS', 40000.00),
    (6, 2023, 'SOUTH', 'FURNITURE',   25000.00)
ON CONFLICT(sales_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Portable Multi-Dimensional Rollup (UNION ALL Emulation for SQLite/ANSI)
-- =============================================================================
-- Demonstrates the mathematical equivalent of ROLLUP(year, region)

-- Granularity 1: Year + Region Detail
SELECT
    CAST(year AS TEXT) AS year_label,
    region,
    SUM(amount) AS total_amount,
    'DETAIL' AS aggregate_level
FROM regional_sales
GROUP BY year, region

UNION ALL

-- Granularity 2: Year Subtotal
SELECT
    CAST(year AS TEXT) AS year_label,
    'ALL REGIONS' AS region,
    SUM(amount) AS total_amount,
    'YEAR SUBTOTAL' AS aggregate_level
FROM regional_sales
GROUP BY year

UNION ALL

-- Granularity 3: Grand Total
SELECT
    'ALL YEARS' AS year_label,
    'ALL REGIONS' AS region,
    SUM(amount) AS total_amount,
    'GRAND TOTAL' AS aggregate_level
FROM regional_sales

ORDER BY year_label DESC, region;

-- Expected Output:
-- year_label | region      | total_amount | aggregate_level
-- 2024       | NORTH       | 70000.0      | DETAIL
-- 2024       | SOUTH       | 75000.0      | DETAIL
-- 2024       | ALL REGIONS | 145000.0     | YEAR SUBTOTAL
-- 2023       | NORTH       | 40000.0      | DETAIL
-- ...

-- =============================================================================
-- QUERY 2: Native GROUPING SETS Syntax (PostgreSQL / Snowflake / Databricks Reference)
-- =============================================================================
/*
SELECT
    year,
    region,
    category,
    SUM(amount) AS total_amount,
    GROUPING(year) AS is_year_aggregated,
    GROUPING(region) AS is_region_aggregated,
    GROUPING(category) AS is_category_aggregated
FROM regional_sales
GROUP BY GROUPING SETS (
    (year, region, category),  -- Level 1: Full detail
    (year, region),            -- Level 2: Subtotal per year & region
    (year),                    -- Level 3: Subtotal per year
    ()                         -- Level 4: Grand total across dataset
)
ORDER BY year NULLS LAST, region NULLS LAST, category NULLS LAST;
*/

-- =============================================================================
-- QUERY 3: Native ROLLUP and CUBE Syntax Reference
-- =============================================================================
/*
-- ROLLUP: Hierarchical tree rollup (year -> region -> category)
SELECT year, region, category, SUM(amount) AS total_amount
FROM regional_sales
GROUP BY ROLLUP (year, region, category);

-- CUBE: All 2^3 = 8 combinations of (year, region, category)
SELECT year, region, category, SUM(amount) AS total_amount
FROM regional_sales
GROUP BY CUBE (year, region, category);
*/

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. GROUPING SETS / ROLLUP / CUBE execute in a single table scan pass inside the database engine.
-- 2. Equivalent UNION ALL queries scan the base table N times (once per UNION block), adding N-fold execution cost.
-- 3. CUBE on N columns generates 2^N grouping combinations. Avoid CUBE on high-cardinality dimensions (>6 columns).

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Use `GROUPING(col)` to replace NULL values caused by subtotals with descriptive labels (`CASE WHEN GROUPING(region)=1 THEN 'All Regions' ELSE region END`).
-- TIP 2: Group smaller tables or pre-filtered CTEs prior to applying CUBE to limit memory footprint.
-- TIP 3: Leverage partial ROLLUP syntax: `GROUP BY year, ROLLUP(region, category)` to fix high-level dimensions while rolling up sub-dimensions.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Confusing NULL values present in raw source data with NULLs generated by ROLLUP / CUBE subtotals (use `GROUPING()` function to distinguish!).
-- MISTAKE 2: Running `CUBE(a, b, c, d, e, f, g, h)` which explodes into 256 grouping queries and causes out-of-memory errors.
-- MISTAKE 3: Using UNION ALL instead of GROUPING SETS in modern data warehouses like Snowflake/Databricks.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the difference between ROLLUP and CUBE in SQL?
--     A: ROLLUP generates hierarchical subtotals along a fixed prefix path (N+1 groupings); CUBE generates all combinations of subtotal levels (2^N groupings).
-- Q2: How does the `GROUPING()` function work?
--     A: `GROUPING(col)` returns 1 if the row represents a subtotal where `col` has been aggregated out, and 0 if `col` contains actual detail data.
-- Q3: Why is `GROUP BY GROUPING SETS ((a, b), (c))` more performant than UNION ALL?
--     A: The engine scans and reads the underlying dataset once, generating all requested grouping sets in memory during the aggregation pass.
-- Q4: How do you replace NULL subtotal labels cleanly without mislabeling actual NULL source values?
--     A: `CASE WHEN GROUPING(col) = 1 THEN 'All Values' ELSE col END`.
-- Q5: What is the number of grouping combinations generated by `ROLLUP(a, b, c)` vs `CUBE(a, b, c)`?
--     A: ROLLUP generates 3 + 1 = 4 combinations: (a,b,c), (a,b), (a), (). CUBE generates 2^3 = 8 combinations.
