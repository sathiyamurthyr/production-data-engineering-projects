/*
================================================================================
MODULE 06: Declarative Data Pipelines with Dynamic Tables
================================================================================

1. EXPLANATION:
Dynamic Tables are declarative continuous transformation tables managed by Snowflake. 
Instead of writing imperative Streams and Tasks, you define a target query and a target lag 
(e.g., `TARGET_LAG = '5 minutes'`). Snowflake automatically determines incremental refresh graphs and schedules execution.

2. BUSINESS USE CASE:
Build real-time gold reporting layers and customer 360 analytical rollups continuously synchronized 
with raw sales and customer tables.

3. PRODUCTION EXAMPLE:
Create Dynamic Tables `DT_DAILY_CATEGORY_METRICS` and `DT_CUSTOMER_SALES_360` with incremental 
refresh modes and target lags.

4. EXPECTED OUTPUT:
Declarative Dynamic Tables automatically refreshed by Snowflake cloud services based on target lag.

5. PERFORMANCE NOTES:
Snowflake evaluates target query changes and performs incremental refreshes when possible. 
If query includes non-deterministic functions, it falls back to full refresh.

6. OPTIMIZATION TIPS:
- Set `TARGET_LAG = 'DOWNSTREAM'` on intermediate dynamic tables in a chain to allow downstream tables to drive compute schedule.
- Avoid unsupported construct in Dynamic Tables (e.g. non-deterministic functions like `CURRENT_TIMESTAMP()`, `RANDOM()`).

7. COMMON MISTAKES:
- Mixing Streams/Tasks and Dynamic Tables on the same target tables, causing conflicting refresh cycles.

8. INTERVIEW QUESTIONS:
Q: How do Dynamic Tables differ from Materialized Views and Streams & Tasks?
A: Materialized Views are limited to single-table aggregations without complex joins/CTEs. 
   Streams & Tasks require imperative orchestration code. Dynamic Tables support multi-table JOINs, CTEs, and window functions with declarative target lag.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Intermediate Staging Customer Table
CREATE OR REPLACE TABLE DATA_ENG_DB.STAGING.STG_CUSTOMERS (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    signup_date DATE,
    customer_segment VARCHAR(30),
    credit_limit NUMBER(12,2)
);

-- Populate Staging Customers
INSERT INTO DATA_ENG_DB.STAGING.STG_CUSTOMERS VALUES
('CUST001', 'Alexander', 'Wright', 'alex.w@example.com', 'New York', 'NY', 'USA', '2024-01-15', 'ENTERPRISE', 50000.00),
('CUST002', 'Sophia', 'Martinez', 'sophia.m@example.com', 'Los Angeles', 'CA', 'USA', '2024-02-20', 'PREMIUM', 15000.00);

-- Step 2: Create Declarative Dynamic Table for Category Metrics
CREATE OR REPLACE DYNAMIC TABLE DT_DAILY_CATEGORY_METRICS
    TARGET_LAG = '5 minutes'
    WAREHOUSE = ETL_WH
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
AS
    SELECT 
        DATE(transaction_timestamp) AS sales_date,
        category,
        COUNT(DISTINCT transaction_id) AS order_count,
        COUNT(DISTINCT customer_id) AS unique_customers,
        SUM(quantity) AS total_units_sold,
        SUM(total_amount) AS gross_revenue,
        AVG(total_amount) AS avg_order_value
    FROM DATA_ENG_DB.ANALYTICS.FACT_SALES
    GROUP BY 1, 2;

-- Step 3: Create Chained Dynamic Table with TARGET_LAG = 'DOWNSTREAM'
CREATE OR REPLACE DYNAMIC TABLE DT_CUSTOMER_SALES_360
    TARGET_LAG = '10 minutes'
    WAREHOUSE = ETL_WH
    REFRESH_MODE = AUTO
AS
    SELECT 
        c.customer_id,
        c.first_name || ' ' || c.last_name AS full_name,
        c.city,
        c.state,
        c.customer_segment,
        COUNT(f.transaction_id) AS total_orders,
        COALESCE(SUM(f.total_amount), 0) AS lifetime_spend,
        MAX(f.transaction_timestamp) AS last_purchase_timestamp
    FROM DATA_ENG_DB.STAGING.STG_CUSTOMERS c
    LEFT JOIN DATA_ENG_DB.ANALYTICS.FACT_SALES f ON c.customer_id = f.customer_id
    GROUP BY 1, 2, 3, 4, 5;

-- Step 4: Manually Trigger Refresh for Verification
ALTER DYNAMIC TABLE DT_DAILY_CATEGORY_METRICS REFRESH;
ALTER DYNAMIC TABLE DT_CUSTOMER_SALES_360 REFRESH;

-- Step 5: Query Dynamic Table Results
SELECT * FROM DT_DAILY_CATEGORY_METRICS ORDER BY sales_date DESC;

-- Step 6: Inspect Dynamic Table Refresh Graph & Monitoring History
SELECT 
    NAME,
    TARGET_LAG,
    WAREHOUSE,
    REFRESH_MODE,
    SCHEDULING_STATE
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES());
