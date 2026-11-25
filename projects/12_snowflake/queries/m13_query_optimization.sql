/*
================================================================================
MODULE 13: Query Performance, Clustering & Micro-Partitions
================================================================================

1. EXPLANATION:
Snowflake stores data in contiguous 50MB-150MB compressed Micro-Partitions. 
When executing queries, Snowflake uses micro-partition metadata (min/max values per column) to prune unneeded micro-partitions. 
Clustering Keys organise micro-partitions along specific columns to maximize pruning efficiency.

2. BUSINESS USE CASE:
Optimize query scanning speed and lower compute credit cost on petabyte-scale fact tables filtered by date range and customer ID.

3. PRODUCTION EXAMPLE:
Define clustering keys on `FACT_SALES`, inspect clustering depth using `SYSTEM$CLUSTERING_INFORMATION`, 
and enable Search Optimization Service for point lookup acceleration.

4. EXPECTED OUTPUT:
Clustering information JSON output showing low average depth and high pruning efficiency.

5. PERFORMANCE NOTES:
Clustering reduces micro-partitions scanned from 100% to < 1% for filtered queries.

6. OPTIMIZATION TIPS:
- Order clustering key columns from lowest cardinality to highest cardinality (e.g. `CLUSTER BY (DATE(transaction_timestamp), category)`).
- Use Search Optimization Service (`SEARCH OPTIMIZATION`) for point lookup equality queries (e.g. `WHERE transaction_id = 'TXN10001'`).

7. COMMON MISTAKES:
- Over-clustering small tables (< 100GB), incurring automatic re-clustering maintenance costs without performance benefit.

8. INTERVIEW QUESTIONS:
Q: What is micro-partition pruning in Snowflake and how does clustering improve it?
A: Pruning skips reading micro-partitions whose metadata min/max range does not match query filters. 
   Clustering aligns data so min/max ranges across micro-partitions do not overlap, maximizing pruned partitions.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Define Explicit Clustering Key on Production Fact Table
ALTER TABLE FACT_SALES CLUSTER BY (DATE(transaction_timestamp), category);

-- Step 2: Check Micro-Partition Clustering Health & Depth
SELECT SYSTEM$CLUSTERING_INFORMATION('FACT_SALES');

-- Step 3: Enable Search Optimization Service for Selective Point Lookups
-- Accelerates equality filters like WHERE transaction_id = '...' or customer_id = '...'
ALTER TABLE FACT_SALES ADD SEARCH OPTIMIZATION
    ON EQUALITY(transaction_id, customer_id);

-- Step 4: Verify Search Optimization Status
SHOW SEARCH OPTIMIZATION FOR TABLE FACT_SALES;

-- Step 5: High-Performance Pruned Query Example
SELECT 
    category,
    SUM(total_amount) AS revenue
FROM FACT_SALES
WHERE transaction_timestamp >= '2026-07-01' AND transaction_timestamp < '2026-07-05'
  AND category = 'Electronics'
GROUP BY 1;
