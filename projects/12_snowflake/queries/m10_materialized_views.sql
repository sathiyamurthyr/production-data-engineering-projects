/*
================================================================================
MODULE 10: Query Acceleration with Materialized Views
================================================================================

1. EXPLANATION:
Snowflake Materialized Views (MVs) pre-compute and store the results of a single-table SELECT query 
for performance acceleration. Snowflake automatically maintains MV updates in the background 
using serverless cloud services.

2. BUSINESS USE CASE:
Accelerate repeated heavy aggregation queries on multi-billion row fact tables (e.g., daily revenue summaries) 
frequently requested by BI dashboards.

3. PRODUCTION EXAMPLE:
Create Materialized Views on single fact tables, query them directly or let the Snowflake Query Optimizer 
automatically rewrite standard queries to leverage MVs, and monitor background maintenance costs.

4. EXPECTED OUTPUT:
Pre-aggregated materialized view results returned with sub-second query performance.

5. PERFORMANCE NOTES:
Snowflake Query Optimizer automatically rewrites base table queries to read from Materialized Views if faster.

6. LIMITATIONS & OPTIMIZATION TIPS:
- Materialized Views in Snowflake support ONLY single table queries (no JOINs, no Window functions, no GROUP BY GROUPING SETS).
- For multi-table JOIN aggregations, use Dynamic Tables instead.

7. COMMON MISTAKES:
- Creating Materialized Views on high-DML turnover tables (thousands of inserts/updates per second), which creates excessive cloud service maintenance costs.

8. INTERVIEW QUESTIONS:
Q: What are the key limitations of Materialized Views in Snowflake compared to traditional RDBMS?
A: Snowflake MVs must be based on a single base table (no JOINs, UDFs, CTEs, or window functions) and are automatically maintained by background serverless compute.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Materialized View on Base Fact Table
CREATE OR REPLACE MATERIALIZED VIEW MV_DAILY_CATEGORY_AGGREGATES
    COMMENT = 'Materialized View pre-aggregating daily category sales metrics'
AS
    SELECT 
        DATE(transaction_timestamp) AS sale_date,
        category,
        payment_method,
        COUNT(*) AS transaction_count,
        SUM(quantity) AS total_units,
        SUM(total_amount) AS total_revenue,
        AVG(total_amount) AS avg_revenue
    FROM DATA_ENG_DB.ANALYTICS.FACT_SALES
    GROUP BY 1, 2, 3;

-- Step 2: Query Materialized View Directly
SELECT 
    sale_date,
    category,
    total_revenue
FROM MV_DAILY_CATEGORY_AGGREGATES
WHERE category = 'Electronics'
ORDER BY sale_date DESC;

-- Step 3: Inspect Materialized View Maintenance Billing & History
SELECT 
    TABLE_NAME,
    CREDITS_USED,
    NUM_BYTES_RECLUSTERED
FROM TABLE(INFORMATION_SCHEMA.MATERIALIZED_VIEW_REFRESH_HISTORY(
    DATE_RANGE_START => DATEADD('day', -7, CURRENT_TIMESTAMP())
));
