/*
================================================================================
MODULE 08: Storage Architecture: Fail-Safe, Permanent vs Transient Tables
================================================================================

1. EXPLANATION:
Snowflake Fail-Safe provides a non-configurable 7-day disaster recovery period following Time Travel expiration. 
Data in Fail-Safe can ONLY be recovered by Snowflake Support. 
To avoid Fail-Safe storage costs for ephemeral data, use Transient or Temporary tables.

2. BUSINESS USE CASE:
Optimize cloud storage spending by declaring daily staging tables as `TRANSIENT` (0 Fail-Safe) 
and session transformation scratchpads as `TEMPORARY`, reserving Permanent tables only for production datasets.

3. PRODUCTION EXAMPLE:
Create Permanent, Transient, and Temporary tables, inspect storage metrics in `TABLE_STORAGE_METRICS`, 
and calculate Fail-Safe credit impact.

4. EXPECTED OUTPUT:
Table storage metrics displaying active bytes, time travel bytes, and fail-safe bytes.

5. PERFORMANCE NOTES:
Transient and Temporary tables do NOT incur Fail-Safe storage charges, drastically lowering storage overhead for high-churn ETL staging workloads.

6. OPTIMIZATION TIPS:
- Convert all ETL staging tables to `TRANSIENT` with 0 or 1 day Time Travel.
- Use `TEMPORARY` tables for intermediate script results that exist only for the session duration.

7. COMMON MISTAKES:
- Leaving all tables as default Permanent, accumulating massive 7-day Fail-Safe storage costs on heavy ETL staging tables.

8. INTERVIEW QUESTIONS:
Q: Can a user query or restore data from Fail-Safe directly using SQL?
A: No. Fail-Safe is accessible only by Snowflake Support for catastrophic data recovery requests.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA STAGING;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Permanent Table (Default: Has Time Travel + 7-Day Fail-Safe)
CREATE OR REPLACE TABLE PERMANENT_SALES_HISTORY (
    id INT,
    amount NUMBER(10,2),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Step 2: Create Transient Table (Has Time Travel 0-1 Day, NO Fail-Safe)
CREATE OR REPLACE TRANSIENT TABLE STG_TRANSIENT_LOAD (
    batch_id VARCHAR(50),
    raw_payload VARIANT,
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) DATA_RETENTION_TIME_IN_DAYS = 1;

-- Step 3: Create Temporary Table (Session-only Lifetime, NO Fail-Safe)
CREATE OR REPLACE TEMPORARY TABLE TEMP_SCRATCH_CALCULATIONS (
    metric_id INT,
    metric_value FLOAT
);

-- Insert Sample Rows into each table type
INSERT INTO PERMANENT_SALES_HISTORY VALUES (1, 100.00, CURRENT_TIMESTAMP());
INSERT INTO STG_TRANSIENT_LOAD VALUES ('BATCH_001', PARSE_JSON('{"event": "click"}'), CURRENT_TIMESTAMP());
INSERT INTO TEMP_SCRATCH_CALCULATIONS VALUES (1, 99.5);

-- Step 4: Query Table Storage Metrics (Active, Time Travel, Fail-Safe Bytes)
SELECT 
    TABLE_NAME,
    TABLE_SCHEMA,
    IS_TRANSIENT,
    ACTIVE_BYTES,
    TIME_TRAVEL_BYTES,
    FAILSAFE_BYTES,
    ROUND((ACTIVE_BYTES + TIME_TRAVEL_BYTES + FAILSAFE_BYTES) / (1024*1024), 4) AS total_mb
FROM DATA_ENG_DB.INFORMATION_SCHEMA.TABLE_STORAGE_METRICS
WHERE TABLE_SCHEMA IN ('STAGING', 'ANALYTICS')
ORDER BY FAILSAFE_BYTES DESC;

-- Step 5: Account-Level Storage Usage Overview
SELECT 
    USAGE_DATE,
    AVERAGE_DATABASE_BYTES / (1024*1024*1024) AS database_storage_gb,
    AVERAGE_FAILSAFE_BYTES / (1024*1024*1024) AS failsafe_storage_gb
FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
ORDER BY USAGE_DATE DESC
LIMIT 7;
