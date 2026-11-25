/*
================================================================================
MODULE 09: Instant Environment Provisioning with Zero-Copy Cloning
================================================================================

1. EXPLANATION:
Zero-Copy Cloning duplicates database objects (Tables, Schemas, Databases) instantly by copying only metadata pointers to existing micro-partitions without copying underlying storage data.

2. BUSINESS USE CASE:
Create instant, isolated Development and Staging database clones from Production datasets for testing code releases or bug fixes with zero initial storage cost.

3. PRODUCTION EXAMPLE:
Clone a production database to `DEV_DATA_ENG_DB`, modify cloned records independently, 
and clone historical states using Time Travel syntax (`CLONE AT (TIMESTAMP => ...)`).

4. EXPECTED OUTPUT:
Cloned tables/schemas created instantly with identical schema structures and zero initial storage overhead.

5. PERFORMANCE NOTES:
Cloning takes seconds regardless of data size (gigabytes or petabytes) because no physical storage blocks are copied.

6. OPTIMIZATION TIPS:
- Clone production environments into disposable dev environments for integration testing and drop them after test execution.
- Use Time Travel cloning (`CLONE AT`) to recreate production states at the exact timestamp an error occurred.

7. COMMON MISTAKES:
- Assuming cloned tables share state: Any DML modification to a cloned table allocates new micro-partitions independently.

8. INTERVIEW QUESTIONS:
Q: Does Zero-Copy Cloning consume storage credits immediately upon creation?
A: No. Initial storage cost is zero. Storage costs are only incurred when rows in either the source or cloned table are modified/updated.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Table Clone (Zero-Copy)
CREATE OR REPLACE TABLE FACT_SALES_DEV_CLONE
    CLONE FACT_SALES;

-- Verify Cloned Data Availability
SELECT COUNT(*) AS clone_row_count FROM FACT_SALES_DEV_CLONE;

-- Step 2: Mutate Cloned Table (Does not affect original source table)
UPDATE FACT_SALES_DEV_CLONE
SET total_amount = total_amount * 0.90
WHERE category = 'Apparel';

-- Step 3: Compare Source and Cloned Table Data (Independent partition evolution)
SELECT 'SOURCE' AS env, AVG(total_amount) AS avg_rev FROM FACT_SALES WHERE category = 'Apparel'
UNION ALL
SELECT 'CLONE_DEV' AS env, AVG(total_amount) AS avg_rev FROM FACT_SALES_DEV_CLONE WHERE category = 'Apparel';

-- Step 4: Clone Database at Historical Point in Time (Time Travel Clone)
-- Useful for debugging issues as of 1 hour ago
CREATE OR REPLACE DATABASE DEV_RESTORED_DB
    CLONE DATA_ENG_DB AT(OFFSET => -3600);

-- Step 5: Clean up disposable clone test database
DROP DATABASE IF EXISTS DEV_RESTORED_DB;
