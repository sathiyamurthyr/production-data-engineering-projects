/*
================================================================================
MODULE 11: REDSHIFT DATA SHARING
================================================================================
Explanation:
  Redshift Data Sharing allows you to share live, transactionally consistent
  data across different Redshift clusters in the same or different AWS accounts/regions,
  without the overhead of copying or moving data. 
  
  The Producer cluster owns the data and shares read-only access.
  The Consumer cluster mounts the datashare and queries the tables directly,
  utilizing its own compute resources (no impact on Producer cluster compute).

  This module covers:
  - Producer configuration: Creating datashare, adding schemas/tables, and granting access.
  - Consumer configuration: Creating a database from the datashare, and running queries.

Business Use Case:
  An enterprise central data engineering team manages the core warehouse (Producer).
  A separate marketing analytics team has their own Redshift cluster (Consumer)
  and needs real-time access to the dim_customer and fact_sales tables for reporting
  without interrupting the central team's ETL.

Production Example:
  SQL command templates for setting up producer-consumer data sharing relationships.

Expected Output:
  SQL templates showing the complete data sharing setup lifecycle.

Performance Notes:
  - Sharing data has zero performance impact on the producer cluster because the
    consumer cluster queries read directly from S3 (via the producer's managed storage layer)
    using the consumer's compute nodes.
  - Queries on shared tables utilize the consumer cluster's query queues and WLM rules.

Optimization Tips:
  - Ensure the consumer cluster has sufficient size and network bandwidth to scan the shared tables.
  - Use datasharing instead of building complex unload/copy pipelines between internal clusters.

Common Mistakes:
  - Forgetting to grant usage permissions on the schema level before granting usage on the tables.
  - Attempting to perform write operations (INSERT/UPDATE/DELETE) on shared tables
    from the consumer cluster (shared tables are strictly read-only).

Interview Questions:
  1. Does querying a shared table in Redshift consume CPU on the producer cluster?
     Answer: No. Querying shared data consumes compute resources (CPU/Memory) ONLY on the
     consumer cluster. The producer cluster only hosts the metadata; data is read from the
     shared storage layer directly.
  2. Can you share data across different AWS accounts using Redshift Data Sharing?
     Answer: Yes, cross-account data sharing is supported. It requires authorizing the
     datashare for the consumer's AWS account ID and accepting the share on the consumer side.
================================================================================
*/

-- =======================================================================
-- PRODUCER CLUSTER COMMANDS (Executed on Central Core Warehouse)
-- =======================================================================

-- 1. Create the Datashare object
CREATE DATASHARE core_warehouse_share;

-- 2. Add the schema to the datashare (Schema permission is required first)
ALTER DATASHARE core_warehouse_share ADD SCHEMA core;

-- 3. Add specific tables to the datashare
ALTER DATASHARE core_warehouse_share ADD TABLE core.dim_customer;
ALTER DATASHARE core_warehouse_share ADD TABLE core.fact_sales;
ALTER DATASHARE core_warehouse_share ADD TABLE core.mv_customer_sales_summary;

-- 4. Grant usage on the datashare to the Consumer cluster namespace
-- Note: Replace '12345678-abcd-1234-abcd-1234567890ab' with the actual consumer cluster namespace GUID.
GRANT USAGE ON DATASHARE core_warehouse_share TO NAMESPACE '12345678-abcd-1234-abcd-1234567890ab';


-- =======================================================================
-- CONSUMER CLUSTER COMMANDS (Executed on Marketing Analytics Cluster)
-- =======================================================================

-- 5. Create a local database reference pointing to the datashare
-- Note: '87654321-dcba-4321-dcba-ba0987654321' is the producer cluster namespace GUID.
CREATE DATABASE marketing_shared_db 
FROM DATASHARE core_warehouse_share 
OF NAMESPACE '87654321-dcba-4321-dcba-ba0987654321';

-- 6. Query the shared tables using the external reference
SELECT 
    country,
    SUM(total_revenue) AS total_regional_sales
FROM marketing_shared_db.core.mv_customer_sales_summary
GROUP BY country
ORDER BY total_regional_sales DESC;

-- =======================================================================
-- DATA SHARE MONITORING & METADATA AUDITING
-- =======================================================================
-- Query outbound shares on the Producer
SELECT * FROM svv_datashares;

-- Query inbound shares on the Consumer
SELECT * FROM svv_datashare_consumers;

-- View specific shared objects
SELECT * FROM svv_datashare_objects;
