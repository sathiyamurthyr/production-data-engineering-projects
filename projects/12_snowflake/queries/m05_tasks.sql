/*
================================================================================
MODULE 05: Automated Task Scheduling & Directed Acyclic Graphs (DAGs)
================================================================================

1. EXPLANATION:
Snowflake Tasks execute single SQL statements or Stored Procedures on a schedule or in response 
to upstream task completions (DAGs). Tasks can run using dedicated Virtual Warehouses or Serverless compute.

2. BUSINESS USE CASE:
Automate hourly ingestion of landing data, incremental stream processing, and downstream reporting 
table refreshes in a multi-stage data pipeline without external schedulers like Airflow.

3. PRODUCTION EXAMPLE:
Create a root task scheduled every 10 minutes conditional on `SYSTEM$STREAM_HAS_DATA`, 
followed by a downstream child task that computes hourly sales aggregates.

4. EXPECTED OUTPUT:
Tasks scheduled and enabled. Successful executions logged in `TASK_HISTORY()`.

5. PERFORMANCE NOTES:
Serverless tasks automatically scale compute based on statement complexity and consume minimal credits.

6. OPTIMIZATION TIPS:
- Wrap task executions with `WHEN SYSTEM$STREAM_HAS_DATA('stream_name')` to avoid starting warehouses when no delta data exists.
- Remember to resume child tasks before resuming root tasks, as root task execution fails if children are suspended.

7. COMMON MISTAKES:
- Forgetting that newly created Tasks are in `SUSPENDED` state by default.
- Setting overly frequent intervals (e.g. every 1 minute) on non-serverless tasks without stream guards.

8. INTERVIEW QUESTIONS:
Q: In a Snowflake Task DAG, in what order must tasks be resumed?
A: Child tasks must be resumed FIRST before resuming the parent/root task. Suspending follows the reverse order.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA STAGING;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Summary Aggregation Table for Task Target
CREATE OR REPLACE TABLE DATA_ENG_DB.ANALYTICS.HOURLY_SALES_SUMMARY (
    summary_hour TIMESTAMP_NTZ PRIMARY KEY,
    category VARCHAR(50),
    total_sales NUMBER(12,2),
    total_transactions INT,
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Step 2: Create Root Task (Warehouse-Based with Stream Condition)
CREATE OR REPLACE TASK PROCESS_SALES_STREAM_TASK
    WAREHOUSE = ETL_WH
    SCHEDULE = 'USING CRON */10 * * * * UTC'
    WHEN SYSTEM$STREAM_HAS_DATA('DATA_ENG_DB.STAGING.STG_SALES_STREAM')
AS
    MERGE INTO DATA_ENG_DB.ANALYTICS.FACT_SALES AS target
    USING DATA_ENG_DB.STAGING.STG_SALES_STREAM AS stream
    ON target.transaction_id = stream.transaction_id
    WHEN NOT MATCHED AND stream.METADATA$ACTION = 'INSERT' THEN
        INSERT (
            transaction_id, customer_id, product_id, category, quantity, unit_price, total_amount, payment_method, store_id, transaction_timestamp
        ) VALUES (
            stream.transaction_id, stream.customer_id, stream.product_id, stream.category, stream.quantity, stream.unit_price, stream.total_amount, stream.payment_method, stream.store_id, stream.transaction_timestamp
        );

-- Step 3: Create Child Task in DAG (Triggered AFTER Root Task Completes)
CREATE OR REPLACE TASK REFRESH_HOURLY_SALES_SUMMARY_TASK
    WAREHOUSE = ETL_WH
    AFTER PROCESS_SALES_STREAM_TASK
AS
    MERGE INTO DATA_ENG_DB.ANALYTICS.HOURLY_SALES_SUMMARY AS target
    USING (
        SELECT 
            DATE_TRUNC('HOUR', transaction_timestamp) AS summary_hour,
            category,
            SUM(total_amount) AS total_sales,
            COUNT(transaction_id) AS total_transactions
        FROM DATA_ENG_DB.ANALYTICS.FACT_SALES
        GROUP BY 1, 2
    ) AS src
    ON target.summary_hour = src.summary_hour AND target.category = src.category
    WHEN MATCHED THEN
        UPDATE SET target.total_sales = src.total_sales, target.total_transactions = src.total_transactions, target.last_updated = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (summary_hour, category, total_sales, total_transactions, last_updated)
        VALUES (src.summary_hour, src.category, src.total_sales, src.total_transactions, CURRENT_TIMESTAMP());

-- Step 4: Resume Task DAG (Child FIRST, then Root)
ALTER TASK REFRESH_HOURLY_SALES_SUMMARY_TASK RESUME;
ALTER TASK PROCESS_SALES_STREAM_TASK RESUME;

-- Step 5: Execute Root Task Manually for Testing
EXECUTE TASK PROCESS_SALES_STREAM_TASK;

-- Step 6: Monitor Task Execution History
SELECT 
    NAME,
    STATE,
    SCHEDULED_TIME,
    COMPLETED_TIME,
    RUN_ID,
    RETURN_VALUE
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
))
ORDER BY SCHEDULED_TIME DESC;
