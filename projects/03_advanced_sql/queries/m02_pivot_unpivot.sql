-- =============================================================================
-- Module 02: Pivot / Unpivot — Reshaping Data for Reporting
-- =============================================================================
-- File        : m02_pivot_unpivot.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- PIVOT transforms rows into columns (long → wide format).
-- UNPIVOT transforms columns into rows (wide → long format).
--
-- PostgreSQL does not have native PIVOT/UNPIVOT syntax, so we use:
--   PIVOT   → Conditional aggregation: SUM(CASE WHEN col='X' THEN val END)
--   UNPIVOT → UNION ALL or VALUES approach
-- Snowflake and Databricks SQL have native PIVOT and UNPIVOT keywords.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Finance reports: Monthly revenue per product shown as columns (Jan, Feb, Mar...)
-- • Marketing dashboards: Campaign performance across channels as separate columns
-- • HR analytics: Headcount by department and quarter
-- • Inventory: Stock levels across warehouse locations as column headers
-- • Unpivot: Normalizing wide Excel-exported data back to a queryable long format

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS monthly_sales (
    sale_id     SERIAL        PRIMARY KEY,
    product     VARCHAR(50)   NOT NULL,
    region      VARCHAR(30)   NOT NULL,
    sale_month  INT           NOT NULL,  -- 1-12
    sale_year   INT           NOT NULL,
    revenue     NUMERIC(12,2) NOT NULL
);

INSERT INTO monthly_sales (product, region, sale_month, sale_year, revenue)
VALUES
    ('Laptop',  'North', 1, 2024, 150000.00),
    ('Laptop',  'North', 2, 2024,  95000.00),
    ('Laptop',  'North', 3, 2024, 210000.00),
    ('Laptop',  'South', 1, 2024,  80000.00),
    ('Laptop',  'South', 2, 2024, 120000.00),
    ('Laptop',  'South', 3, 2024, 140000.00),
    ('Phone',   'North', 1, 2024, 200000.00),
    ('Phone',   'North', 2, 2024, 175000.00),
    ('Phone',   'North', 3, 2024, 230000.00),
    ('Phone',   'South', 1, 2024, 160000.00),
    ('Phone',   'South', 2, 2024, 195000.00),
    ('Phone',   'South', 3, 2024, 215000.00),
    ('Tablet',  'North', 1, 2024,  60000.00),
    ('Tablet',  'North', 2, 2024,  55000.00),
    ('Tablet',  'North', 3, 2024,  75000.00),
    ('Tablet',  'South', 1, 2024,  45000.00),
    ('Tablet',  'South', 2, 2024,  50000.00),
    ('Tablet',  'South', 3, 2024,  65000.00)
ON CONFLICT DO NOTHING;

-- Wide-format table for UNPIVOT examples
CREATE TABLE IF NOT EXISTS quarterly_budget (
    department      VARCHAR(50)   PRIMARY KEY,
    q1_budget       NUMERIC(12,2),
    q2_budget       NUMERIC(12,2),
    q3_budget       NUMERIC(12,2),
    q4_budget       NUMERIC(12,2)
);

INSERT INTO quarterly_budget (department, q1_budget, q2_budget, q3_budget, q4_budget)
VALUES
    ('Engineering',  500000.00, 550000.00, 480000.00, 620000.00),
    ('Marketing',    200000.00, 350000.00, 280000.00, 400000.00),
    ('Sales',        300000.00, 420000.00, 390000.00, 500000.00),
    ('HR',           100000.00, 110000.00,  95000.00, 120000.00)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: PIVOT — Monthly Revenue as Columns (ANSI SQL Conditional Aggregation)
-- =============================================================================
-- Transforms: (product, sale_month, revenue) → (product, Jan, Feb, Mar...)

SELECT
    product,
    region,
    SUM(CASE WHEN sale_month = 1 THEN revenue ELSE 0 END)  AS jan_revenue,
    SUM(CASE WHEN sale_month = 2 THEN revenue ELSE 0 END)  AS feb_revenue,
    SUM(CASE WHEN sale_month = 3 THEN revenue ELSE 0 END)  AS mar_revenue,
    SUM(CASE WHEN sale_month = 4 THEN revenue ELSE 0 END)  AS apr_revenue,
    SUM(CASE WHEN sale_month = 5 THEN revenue ELSE 0 END)  AS may_revenue,
    SUM(CASE WHEN sale_month = 6 THEN revenue ELSE 0 END)  AS jun_revenue,
    SUM(CASE WHEN sale_month = 7 THEN revenue ELSE 0 END)  AS jul_revenue,
    SUM(CASE WHEN sale_month = 8 THEN revenue ELSE 0 END)  AS aug_revenue,
    SUM(CASE WHEN sale_month = 9 THEN revenue ELSE 0 END)  AS sep_revenue,
    SUM(CASE WHEN sale_month = 10 THEN revenue ELSE 0 END) AS oct_revenue,
    SUM(CASE WHEN sale_month = 11 THEN revenue ELSE 0 END) AS nov_revenue,
    SUM(CASE WHEN sale_month = 12 THEN revenue ELSE 0 END) AS dec_revenue,
    SUM(revenue)                                            AS annual_total
FROM monthly_sales
WHERE sale_year = 2024
GROUP BY product, region
ORDER BY product, region;

-- Expected Output:
-- product | region | jan_revenue | feb_revenue | mar_revenue | annual_total
-- Laptop  | North  | 150000.00   | 95000.00    | 210000.00   | 455000.00
-- Laptop  | South  | 80000.00    | 120000.00   | 140000.00   | 340000.00

-- =============================================================================
-- QUERY 2: PIVOT — Cross-Region Product Summary (Regions as Columns)
-- =============================================================================

SELECT
    product,
    sale_month,
    SUM(CASE WHEN region = 'North' THEN revenue ELSE 0 END) AS north_revenue,
    SUM(CASE WHEN region = 'South' THEN revenue ELSE 0 END) AS south_revenue,
    SUM(CASE WHEN region = 'East'  THEN revenue ELSE 0 END) AS east_revenue,
    SUM(CASE WHEN region = 'West'  THEN revenue ELSE 0 END) AS west_revenue,
    SUM(revenue)                                             AS total_all_regions
FROM monthly_sales
WHERE sale_year = 2024
GROUP BY product, sale_month
ORDER BY product, sale_month;

-- =============================================================================
-- QUERY 3: PIVOT with Percentage Share
-- =============================================================================
-- Shows revenue AND its share of annual total per product

WITH annual_totals AS (
    SELECT
        product,
        SUM(revenue) AS annual_total
    FROM monthly_sales
    WHERE sale_year = 2024
    GROUP BY product
)

SELECT
    ms.product,
    SUM(CASE WHEN sale_month = 1 THEN revenue ELSE 0 END)  AS jan_rev,
    SUM(CASE WHEN sale_month = 2 THEN revenue ELSE 0 END)  AS feb_rev,
    SUM(CASE WHEN sale_month = 3 THEN revenue ELSE 0 END)  AS mar_rev,
    SUM(ms.revenue)                                         AS total_rev,
    at.annual_total,
    ROUND(
        100.0 * SUM(ms.revenue) / NULLIF(at.annual_total, 0), 2
    )                                                        AS region_pct_of_total
FROM monthly_sales ms
JOIN annual_totals at ON ms.product = at.product
WHERE ms.sale_year = 2024
GROUP BY ms.product, ms.region, at.annual_total
ORDER BY ms.product, ms.region;

-- =============================================================================
-- QUERY 4: UNPIVOT — Wide Budget Table Back to Long Format
-- =============================================================================
-- Transforms (department, q1_budget, q2_budget, q3_budget, q4_budget)
--         → (department, quarter, budget_amount)
-- Uses UNION ALL — the portable ANSI SQL approach

SELECT department, 'Q1' AS quarter, q1_budget AS budget FROM quarterly_budget
UNION ALL
SELECT department, 'Q2' AS quarter, q2_budget AS budget FROM quarterly_budget
UNION ALL
SELECT department, 'Q3' AS quarter, q3_budget AS budget FROM quarterly_budget
UNION ALL
SELECT department, 'Q4' AS quarter, q4_budget AS budget FROM quarterly_budget
ORDER BY department, quarter;

-- Expected Output:
-- department   | quarter | budget
-- Engineering  | Q1      | 500000.00
-- Engineering  | Q2      | 550000.00
-- Engineering  | Q3      | 480000.00
-- Engineering  | Q4      | 620000.00
-- HR           | Q1      | 100000.00
-- ...

-- =============================================================================
-- QUERY 5: UNPIVOT using VALUES clause (PostgreSQL-specific, more elegant)
-- =============================================================================

SELECT
    qb.department,
    unpivoted.quarter,
    unpivoted.budget
FROM quarterly_budget qb
CROSS JOIN LATERAL (
    VALUES
        ('Q1', qb.q1_budget),
        ('Q2', qb.q2_budget),
        ('Q3', qb.q3_budget),
        ('Q4', qb.q4_budget)
) AS unpivoted(quarter, budget)
ORDER BY qb.department, unpivoted.quarter;

-- =============================================================================
-- QUERY 6: Snowflake Native PIVOT Syntax (for reference)
-- =============================================================================
-- NOTE: This syntax works in Snowflake and is shown for comparison.
-- In PostgreSQL, use the conditional aggregation approach (Query 1 above).

/*
-- Snowflake PIVOT:
SELECT *
FROM (
    SELECT product, region, sale_month, revenue
    FROM monthly_sales
    WHERE sale_year = 2024
)
PIVOT (
    SUM(revenue)
    FOR sale_month IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
) AS pvt;

-- Snowflake UNPIVOT:
SELECT department, quarter, budget
FROM quarterly_budget
UNPIVOT (
    budget FOR quarter IN (q1_budget, q2_budget, q3_budget, q4_budget)
);
*/

-- =============================================================================
-- QUERY 7: Dynamic Pivot Headers via crosstab (PostgreSQL tablefunc extension)
-- =============================================================================
-- For truly dynamic pivots in PostgreSQL, use the tablefunc extension.
-- This is useful when the pivot column values are not known at query-write time.

-- Enable extension (run once by superuser):
-- CREATE EXTENSION IF NOT EXISTS tablefunc;

/*
-- PostgreSQL crosstab:
SELECT *
FROM crosstab(
    -- Source query: must return (row_id, category, value) exactly
    $$
    SELECT
        product,
        TO_CHAR(TO_DATE(sale_month::TEXT, 'MM'), 'Mon') AS month_name,
        SUM(revenue)::NUMERIC
    FROM monthly_sales
    WHERE sale_year = 2024
    GROUP BY product, sale_month
    ORDER BY product, sale_month
    $$,
    -- Category definition query:
    $$ SELECT m FROM generate_series(1,12) AS t(m)
       CROSS JOIN LATERAL (
           SELECT TO_CHAR(TO_DATE(t.m::TEXT, 'MM'), 'Mon')
       ) AS mn(m) $$
) AS ct(product TEXT, jan NUMERIC, feb NUMERIC, mar NUMERIC,
        apr NUMERIC, may NUMERIC, jun NUMERIC, jul NUMERIC,
        aug NUMERIC, sep NUMERIC, oct NUMERIC, nov NUMERIC, dec NUMERIC);
*/

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Conditional aggregation (CASE WHEN) requires a full table scan.
--    Ensure the base table is filtered with WHERE before aggregating.
-- 2. For wide pivots (100+ columns), consider generating the SQL dynamically
--    in Python/DBT instead of writing 100 CASE statements manually.
-- 3. Snowflake PIVOT is syntactic sugar — performance equivalent to CASE WHEN.
-- 4. UNPIVOT with UNION ALL multiplies query execution N times (N = # of columns).
--    LATERAL VALUES is more efficient as it avoids repeated scans.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Filter the CTE/subquery before pivoting — reduce rows processed
-- TIP 2: Use partial indexes on the category column if queried frequently
-- TIP 3: Pre-aggregate into a summary table before pivoting large datasets
-- TIP 4: In Databricks, use PIVOT with dynamic column lists via Spark SQL
-- TIP 5: For reports, consider pushing pivot logic to the BI layer (Tableau, Metabase)

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Using MAX instead of SUM in CASE WHEN — gives wrong results for multi-row
-- MISTAKE 2: NULL vs 0 — CASE WHEN returns NULL when no match; wrap with COALESCE(x,0)
-- MISTAKE 3: Hardcoding months/categories — breaks when new values are added
-- MISTAKE 4: Forgetting GROUP BY when using conditional aggregation
-- MISTAKE 5: Not ordering UNPIVOT results — produces non-deterministic row order

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: How do you pivot rows to columns in PostgreSQL which lacks PIVOT syntax?
--     A: Use conditional aggregation: SUM(CASE WHEN category = 'X' THEN value END)
--        with GROUP BY on the row identifier column(s).

-- Q2: What is the difference between PIVOT and crosstab in PostgreSQL?
--     A: PIVOT is a conceptual operation; crosstab (via tablefunc extension) is the
--        PostgreSQL implementation that supports dynamic column headers via a second
--        query, whereas CASE WHEN requires hardcoded column names.

-- Q3: When would you choose UNPIVOT over keeping data in wide format?
--     A: Wide format is efficient for dashboards with fixed columns. Long format
--        is better for: analytics (aggregations across flexible dimensions),
--        normalization, and compatibility with tools expecting key-value pairs.

-- Q4: How would you handle NULL values during pivot/unpivot?
--     A: Use COALESCE(value, 0) for numeric columns during pivot.
--        During unpivot, filter WHERE budget IS NOT NULL if nulls indicate
--        absence rather than zero.

-- Q5: Explain the performance impact of pivoting a 100M row table.
--     A: Full scan required; use partition pruning (WHERE year=X), pre-aggregate
--        in a CTE or staging table, and consider materialized views for
--        frequently-accessed pivot results.
