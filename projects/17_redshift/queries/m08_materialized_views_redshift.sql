/*
================================================================================
MODULE 08: MATERIALIZED VIEWS IN REDSHIFT
================================================================================
Explanation:
  Materialized views precompute and store the results of a query on disk.
  This allows subsequent queries to retrieve data much faster because they don't
  need to execute the underlying joins and aggregations.
  Redshift supports automatic incremental updates (when base tables only undergo simple changes)
  and automated query rewriting (where Redshift reroutes queries on base tables to the MV).

  This module covers:
  - Creating a Materialized View with Auto Refresh
  - Executing Refresh commands manually
  - Checking MV status and refresh history
  - Understanding query rewriting.

Business Use Case:
  Powering a executive executive dashboard that updates daily, displaying sales performance
  by customer country and product category. Executing this aggregation on base tables
  every time a user logs in is highly wasteful.

Production Example:
  We create core.mv_customer_sales_summary to cache aggregated metrics.

Expected Output:
  Materialized View schema defined and system audit query provided.

Performance Notes:
  - If a materialized view can be incrementally refreshed, Redshift only processes the delta
    (new data added to the base tables since the last refresh), which is extremely fast.
  - If it is not eligible for incremental refresh, Redshift performs a full refresh,
    re-running the query.

Optimization Tips:
  - Set `AUTO REFRESH YES` to let Redshift automatically refresh the view as soon as base
    tables change.
  - Design materialized views such that they are eligible for incremental refresh (avoid
    unsupported functions like window functions, outer joins, or non-deterministic functions
    like GETDATE() inside the MV query).

Common Mistakes:
  - Defining an MV with non-deterministic expressions (like CURRENT_DATE), which disables
    incremental refresh and auto-rewriting.
  - Relying on auto-refresh for highly volatile staging tables, causing constant system overhead.

Interview Questions:
  1. What is the difference between a standard View and a Materialized View?
     Answer: A standard view runs its query every time it is referenced, acting as a shortcut.
     A materialized view computes the results and saves them to disk. Queries on an MV
     read from disk, similar to a physical table, making them much faster.
  2. What is Query Rewriting in Redshift Materialized Views?
     Answer: Query rewriting is a feature where the query planner automatically rewrites
     a query written against the base tables to run against a materialized view instead,
     if it detects that the materialized view has the precomputed data.
================================================================================
*/

-- 1. Create Materialized View with Auto Refresh enabled
-- This MV aggregates sales data by country and year/month.
CREATE MATERIALIZED VIEW core.mv_customer_sales_summary
BACKUP YES
DISTSTYLE KEY
DISTKEY(customer_id)
SORTKEY(sale_year, sale_month)
AUTO REFRESH YES -- Let AWS automatically manage the refresh cycle
AS
SELECT 
    c.customer_id,
    c.country,
    TO_CHAR(s.sale_date, 'YYYY') AS sale_year,
    TO_CHAR(s.sale_date, 'MM') AS sale_month,
    SUM(s.quantity) AS total_quantity,
    SUM(s.quantity * s.unit_price) AS total_revenue,
    COUNT(s.sales_id) AS total_transactions
FROM core.fact_sales s
INNER JOIN core.dim_customer c 
    ON s.customer_id = c.customer_id
GROUP BY 
    c.customer_id,
    c.country,
    TO_CHAR(s.sale_date, 'YYYY'),
    TO_CHAR(s.sale_date, 'MM');

-- 2. Querying the Materialized View directly
-- (Extremely fast scan as it is pre-aggregated and sorted on disk)
SELECT country, sale_year, SUM(total_revenue) AS total_sales
FROM core.mv_customer_sales_summary
WHERE country = 'USA'
GROUP BY country, sale_year;

-- 3. Manual Refresh of the Materialized View
-- Forces Redshift to update the materialized view immediately
REFRESH MATERIALIZED VIEW core.mv_customer_sales_summary;

-- 4. Audit Query to check Materialized View status and refresh type
-- Querying SVV_MV_INFO to see if MV is incremental, active, or state is stale.
SELECT 
    db_name,
    schema_name,
    name AS mv_name,
    is_stale,
    state, -- 1 = active, 0 = inactive
    autorefresh,
    refresh_type -- Incremental vs Manual/Full
FROM svv_mv_info
WHERE name = 'mv_customer_sales_summary';
