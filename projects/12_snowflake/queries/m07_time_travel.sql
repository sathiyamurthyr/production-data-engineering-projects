/*
================================================================================
MODULE 07: Data Recovery & Historical Querying with Time Travel
================================================================================

1. EXPLANATION:
Snowflake Time Travel enables accessing historical data (changed or deleted) at any point within 
a defined retention period (0-1 day for Standard Edition, up to 90 days for Enterprise Edition).

2. BUSINESS USE CASE:
Instantly recover accidentally modified or dropped production tables without restoring from backup tapes, 
and audit row-level state changes over time.

3. PRODUCTION EXAMPLE:
Configure retention periods, perform unintended DML updates/deletes, query historical states 
using `AT (TIMESTAMP => ...)` and `BEFORE (STATEMENT => ...)`, and execute `UNDROP TABLE`.

4. EXPECTED OUTPUT:
Historical data successfully retrieved and accidentally dropped tables fully restored.

5. PERFORMANCE NOTES:
Time Travel incurs continuous storage costs for historical micro-partitions modified by DML commands.

6. OPTIMIZATION TIPS:
- Set retention to 1 day for staging/transient tables, and 30-90 days for core production tables.
- Capture the Query ID of mistaken statements from `LAST_QUERY_ID()` to isolate exact point-in-time recovery bounds.

7. COMMON MISTAKES:
- Assuming `DROP TABLE` deletes data instantly; Time Travel retention keeps data until retention + fail-safe expires.

8. INTERVIEW QUESTIONS:
Q: What is the difference between AT and BEFORE clauses in Snowflake Time Travel?
A: AT includes changes made by the specified statement/timestamp; BEFORE includes state immediately preceding the statement/timestamp.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Configure Table Data Retention Period
ALTER TABLE FACT_SALES SET DATA_RETENTION_TIME_IN_DAYS = 7;

-- Step 2: Capture Current Timestamp & Initial Count
SET initial_time = CURRENT_TIMESTAMP()::TIMESTAMP_NTZ;

SELECT COUNT(*) AS count_before_mutation FROM FACT_SALES;

-- Step 3: Simulate Accidental Bulk Delete Operation
DELETE FROM FACT_SALES WHERE category = 'Electronics';

SELECT COUNT(*) AS count_after_accidental_delete FROM FACT_SALES;

-- Step 4: Query Historical Data using AT (TIMESTAMP)
SELECT COUNT(*) AS recovered_count_via_timestamp
FROM FACT_SALES AT(TIMESTAMP => $initial_time);

-- Step 5: Restore Accidentally Deleted Rows using Time Travel & CTE
INSERT INTO FACT_SALES
SELECT * FROM FACT_SALES AT(TIMESTAMP => $initial_time)
WHERE category = 'Electronics';

SELECT COUNT(*) AS count_after_restoration FROM FACT_SALES;

-- Step 6: Simulate Accidental Table Drop and UNDROP Table Recovery
CREATE OR REPLACE TABLE CRITICAL_REPORT_CACHE AS SELECT 1 AS id, 'REPORT_DATA' AS val;

DROP TABLE CRITICAL_REPORT_CACHE;

-- Recover dropped table instantly using UNDROP
UNDROP TABLE CRITICAL_REPORT_CACHE;

SELECT * FROM CRITICAL_REPORT_CACHE;
