/*
================================================================================
MODULE 11: Cross-Account Governance & Secure Data Sharing
================================================================================

1. EXPLANATION:
Snowflake Secure Data Sharing enables live, zero-copy sharing of tables, secure views, and secure UDFs 
with other Snowflake accounts (or non-Snowflake customers via Reader Accounts) without FTP, APIs, or copying data files.

2. BUSINESS USE CASE:
Share real-time sales performance metrics and inventory status with external B2B partners, suppliers, 
or vendor accounts securely without data duplication.

3. PRODUCTION EXAMPLE:
Create a Secure View hiding PII (Personally Identifiable Information), define an Outbound Share object (`SALES_PARTNER_SHARE`), 
grant database/schema/view privileges, and attach consumer account IDs.

4. EXPECTED OUTPUT:
Share object created and configured for external consumer access.

5. PERFORMANCE NOTES:
Data sharing incurs ZERO storage cost for consumers. Compute costs are borne by the consumer running queries on their warehouse.

6. OPTIMIZATION TIPS:
- Always use `SECURE VIEW` when sharing data to prevent consumers from optimizing query plans to expose hidden column values.
- Use Reader Accounts (Managed Accounts) if external partners do not have their own Snowflake account.

7. COMMON MISTAKES:
- Granting privileges on standard views instead of `SECURE VIEW`, exposing internal query optimization execution trees.

8. INTERVIEW QUESTIONS:
Q: What is a Secure View in Snowflake and why must it be used in Data Sharing?
A: Secure Views prevent Snowflake's query optimizer from using optimizations that could leak hidden data or expose internal filter logic to unauthorized consumers.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Secure View masking PII data for external sharing
CREATE OR REPLACE SECURE VIEW SECURE_PARTNER_SALES_VW AS
SELECT 
    transaction_id,
    SHA2(customer_id, 256) AS masked_customer_hash,
    product_id,
    category,
    quantity,
    total_amount,
    store_id,
    transaction_timestamp
FROM DATA_ENG_DB.ANALYTICS.FACT_SALES;

-- Step 2: Create Outbound Share Object (Provider Account)
CREATE OR REPLACE SHARE SALES_PARTNER_SHARE
    COMMENT = 'Outbound secure share for B2B analytics partners';

-- Step 3: Grant Database, Schema, and View Privileges to Share
GRANT USAGE ON DATABASE DATA_ENG_DB TO SHARE SALES_PARTNER_SHARE;
GRANT USAGE ON SCHEMA DATA_ENG_DB.ANALYTICS TO SHARE SALES_PARTNER_SHARE;
GRANT SELECT ON VIEW DATA_ENG_DB.ANALYTICS.SECURE_PARTNER_SALES_VW TO SHARE SALES_PARTNER_SHARE;

-- Step 4: Add Consumer Account ID to Share
-- ALTER SHARE SALES_PARTNER_SHARE ADD ACCOUNTS = xy98765;

-- Step 5: Verify Share Privileges & Included Objects
SHOW SHARES LIKE 'SALES_PARTNER_SHARE';
DESCRIBE SHARE SALES_PARTNER_SHARE;
