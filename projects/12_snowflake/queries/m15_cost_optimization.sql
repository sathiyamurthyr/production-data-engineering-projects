/*
================================================================================
MODULE 15: Financial Operations (FinOps) & Credit Cost Optimization
================================================================================

1. EXPLANATION:
Snowflake billing is based on compute credit usage (virtual warehouse runtime per second) 
and storage usage (TB per month). FinOps optimization focuses on eliminating idle warehouse runtime, 
right-sizing compute sizes, detecting inefficient queries, and setting resource quota guardrails.

2. BUSINESS USE CASE:
Audit monthly credit consumption across teams, identify runaway long-running queries, 
and configure automatic resource monitors to enforce corporate budget limits.

3. PRODUCTION EXAMPLE:
Query `SNOWFLAKE.ACCOUNT_USAGE` metering and query history views to detect high-cost warehouses, 
spilled queries, and excessive auto-suspend timeouts.

4. EXPECTED OUTPUT:
Cost breakdown report by warehouse and query execution time report.

5. PERFORMANCE NOTES:
Data in `ACCOUNT_USAGE` latency can be 45-120 minutes. For real-time monitoring, use `INFORMATION_SCHEMA`.

6. OPTIMIZATION TIPS:
- Change warehouse `AUTO_SUSPEND` from 300s to 60s for immediate credit savings on bursty ETL workloads.
- Flag queries spilling memory to remote disk storage (`BYTES_SPILLED_TO_REMOTE_STORAGE > 0`) as candidates for scaling UP.

7. COMMON MISTAKES:
- Leaving test/scratch warehouses configured with large sizes (e.g. X-Large) and AUTO_SUSPEND = 0.

8. INTERVIEW QUESTIONS:
Q: What does disk spilling (local vs remote) indicate in Snowflake Query Profile and how do you resolve it?
A: Disk spilling indicates the virtual warehouse memory was exceeded during execution. Local spilling means data spilled to warehouse SSDs (slower). Remote spilling means data spilled to cloud storage S3/GCS (much slower). Resolution: Increase warehouse size (scale up).
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Calculate Monthly Credit Spend by Warehouse
SELECT 
    WAREHOUSE_NAME,
    ROUND(SUM(CREDITS_USED), 2) AS total_credits_consumed,
    ROUND(SUM(CREDITS_USED_COMPUTE), 2) AS compute_credits,
    ROUND(SUM(CREDITS_USED_CLOUD_SERVICES), 2) AS cloud_services_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD('month', -1, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY total_credits_consumed DESC;

-- Step 2: Identify Top 10 Longest Running Queries & Disk Spilling Metrics
SELECT 
    QUERY_ID,
    USER_NAME,
    WAREHOUSE_NAME,
    WAREHOUSE_SIZE,
    ROUND(EXECUTION_TIME / 1000, 2) AS execution_seconds,
    BYTES_SCANNED / (1024*1024) AS mb_scanned,
    BYTES_SPILLED_TO_LOCAL_STORAGE / (1024*1024) AS mb_spilled_local,
    BYTES_SPILLED_TO_REMOTE_STORAGE / (1024*1024) AS mb_spilled_remote,
    SUBSTR(QUERY_TEXT, 1, 100) AS query_snippet
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND EXECUTION_STATUS = 'SUCCESS'
ORDER BY EXECUTION_TIME DESC
LIMIT 10;

-- Step 3: Audit Warehouse Configurations for Auto-Suspend Optimization
SELECT 
    NAME AS warehouse_name,
    SIZE,
    AUTO_SUSPEND,
    AUTO_RESUME,
    MIN_CLUSTER_COUNT,
    MAX_CLUSTER_COUNT,
    SCALING_POLICY
FROM TABLE(INFORMATION_SCHEMA.WAREHOUSES())
WHERE AUTO_SUSPEND > 120 OR AUTO_SUSPEND = 0;

-- Step 4: Enforce Standard FinOps Auto-Suspend (60 seconds) on Compute Warehouses
ALTER WAREHOUSE ETL_WH SET AUTO_SUSPEND = 60;
