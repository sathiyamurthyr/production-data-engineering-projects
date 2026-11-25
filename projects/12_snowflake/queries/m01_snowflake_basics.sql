/*
================================================================================
MODULE 01: Snowflake Architecture & Environment Basics
================================================================================

1. EXPLANATION:
Snowflake decouples compute (Virtual Warehouses), storage (Centralized Cloud Storage on S3/Blob/GCS), 
and cloud services (MetaData, Security, Optimizer). Virtual Warehouses can be created, resized, 
paused, resumed, and auto-scaled independently without affecting underlying data storage.

2. BUSINESS USE CASE:
Provision multi-cluster compute environments for data engineering pipelines, ad-hoc BI reporting, 
and machine learning workloads, each isolated to prevent resource contention and optimize costs.

3. PRODUCTION EXAMPLE:
Create dedicated databases (`DEV_DB`, `PROD_DB`), schemas (`STAGING`, `ANALYTICS`), and an auto-scaling 
multi-cluster warehouse (`ETL_WH`) with auto-suspend set to 60 seconds to prevent billing waste.

4. EXPECTED OUTPUT:
Database, schema, resource monitor, and multi-cluster virtual warehouse created and active.

5. PERFORMANCE NOTES:
Warehouse scaling up (e.g. X-Small -> Large) adds CPU/RAM for single query speed. 
Scaling out (multi-cluster min 1 to max 5) adds capacity for concurrent queries without queueing.

6. OPTIMIZATION TIPS:
- Set auto-suspend to 60 seconds for interactive/ETL workloads.
- Use ECONOMY scaling policy for background batch loads, and STANDARD for interactive dashboards.

7. COMMON MISTAKES:
- Keeping warehouses running indefinitely with AUTO_SUSPEND = 0 or high timeouts (e.g., 3600s).
- Running large ETL transformations on shared X-Small warehouses causing disk spilling.

8. INTERVIEW QUESTIONS:
Q: What is the difference between scaling up and scaling out in Snowflake Virtual Warehouses?
A: Scaling up increases warehouse size (e.g., Small to Medium) to give individual queries more CPU/RAM. 
   Scaling out increases cluster count (multi-cluster warehouse) to handle higher query concurrency.
================================================================================
*/

-- Step 1: Create Database & Schemas
CREATE DATABASE IF NOT EXISTS DATA_ENG_DB;
USE DATABASE DATA_ENG_DB;

CREATE SCHEMA IF NOT EXISTS DATA_ENG_DB.STAGING;
CREATE SCHEMA IF NOT EXISTS DATA_ENG_DB.ANALYTICS;
USE SCHEMA DATA_ENG_DB.STAGING;

-- Step 2: Create Resource Monitor for Cost Protection
CREATE OR REPLACE RESOURCE MONITOR DE_COST_LIMIT
    WITH CREDIT_QUOTA = 100
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    ON 80% DO NOTIFY
    ON 90% DO SUSPEND
    ON 100% DO SUSPEND_IMMEDIATE;

-- Step 3: Create Dedicated Multi-Cluster Virtual Warehouse
CREATE OR REPLACE WAREHOUSE ETL_WH
    WITH 
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    MIN_CLUSTERS = 1
    MAX_CLUSTERS = 3
    SCALING_POLICY = 'STANDARD'
    COMMENT = 'Dedicated compute warehouse for production ETL pipelines';

USE WAREHOUSE ETL_WH;

-- Step 4: Inspect Active System Context & Warehouse Metrics
SELECT 
    CURRENT_ACCOUNT() AS active_account,
    CURRENT_USER() AS active_user,
    CURRENT_ROLE() AS active_role,
    CURRENT_DATABASE() AS active_database,
    CURRENT_SCHEMA() AS active_schema,
    CURRENT_WAREHOUSE() AS active_warehouse;

-- Step 5: Check Warehouse Status & Parameters
SELECT SYSTEM$WAREHOUSE_STATUS('ETL_WH');

SHOW WAREHOUSES LIKE 'ETL_WH';
