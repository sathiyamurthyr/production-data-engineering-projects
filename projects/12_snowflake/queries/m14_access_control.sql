/*
================================================================================
MODULE 14: Enterprise Governance: Role-Based Access Control (RBAC), Masking & Row Access Policies
================================================================================

1. EXPLANATION:
Snowflake enforces security through Role-Based Access Control (RBAC). Privileges are granted to Roles, 
and Roles are granted to Users or other Roles in a strict hierarchy. Column-level Dynamic Data Masking 
and Row Access Policies enforce fine-grained column/row governance.

2. BUSINESS USE CASE:
Mask sensitive customer email addresses and restrict financial records so analysts can only see 
rows matching their assigned regional store location role.

3. PRODUCTION EXAMPLE:
Build access roles (`DATA_ENGINEER_ROLE`, `BI_ANALYST_ROLE`), create Dynamic Data Masking policy 
for email addresses, and attach Row Access Policy to filter records by user role context.

4. EXPECTED OUTPUT:
Dynamic data masking and row level security active, obfuscating email addresses for non-authorized roles.

5. PERFORMANCE NOTES:
Masking and Row Access Policies are evaluated inline by Snowflake Cloud Services with minimal query overhead.

6. OPTIMIZATION TIPS:
- Separate Access Roles (object privileges) from Functional Roles (business job functions) for clean role hierarchies.
- Never run production daily ETL tasks under `ACCOUNTADMIN` role.

7. COMMON MISTAKES:
- Granting `ACCOUNTADMIN` role to data engineers or automated service users.

8. INTERVIEW QUESTIONS:
Q: What is the difference between Functional Roles and Access Roles in Snowflake RBAC design?
A: Access Roles contain object-level privileges (e.g. SELECT on table X). Functional Roles reflect job duties (e.g. Data Scientist) and inherit multiple Access Roles.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create RBAC Custom Role Hierarchy
USE ROLE USERADMIN;

CREATE ROLE IF NOT EXISTS AR_DATA_ENG_READWRITE;
CREATE ROLE IF NOT EXISTS AR_BI_ANALYST_READONLY;
CREATE ROLE IF NOT EXISTS FR_SENIOR_DATA_ENGINEER;

-- Build Role Hierarchy: Access Role -> Functional Role -> SYSADMIN
GRANT ROLE AR_DATA_ENG_READWRITE TO ROLE FR_SENIOR_DATA_ENGINEER;
GRANT ROLE FR_SENIOR_DATA_ENGINEER TO ROLE SYSADMIN;

-- Step 2: Grant Object Privileges to Access Roles
USE ROLE SECURITYADMIN;

GRANT USAGE ON DATABASE DATA_ENG_DB TO ROLE AR_DATA_ENG_READWRITE;
GRANT USAGE ON SCHEMA DATA_ENG_DB.ANALYTICS TO ROLE AR_DATA_ENG_READWRITE;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA DATA_ENG_DB.ANALYTICS TO ROLE AR_DATA_ENG_READWRITE;

-- Step 3: Create Dynamic Data Masking Policy for PII Email Addresses
USE ROLE ACCOUNTADMIN;
USE SCHEMA DATA_ENG_DB.ANALYTICS;

CREATE OR REPLACE MASKING POLICY EMAIL_MASK_POLICY AS (val string) 
RETURNS string ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'FR_SENIOR_DATA_ENGINEER') THEN val
        ELSE REGEXP_REPLACE(val, '(^[^@]{2})([^@]+)(@.*$)', '\\1***\\3')
    END;

-- Apply Masking Policy to Staging Customers Email Column
ALTER TABLE DATA_ENG_DB.STAGING.STG_CUSTOMERS 
    MODIFY COLUMN email SET MASKING POLICY EMAIL_MASK_POLICY;

-- Step 4: Create Row Access Policy for Regional Store Governance
CREATE OR REPLACE ROW ACCESS POLICY REGIONAL_STORE_POLICY AS (store_id string)
RETURNS boolean ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'FR_SENIOR_DATA_ENGINEER') THEN TRUE
        WHEN CURRENT_ROLE() = 'AR_BI_ANALYST_READONLY' AND store_id = 'STORE_NY_01' THEN TRUE
        ELSE FALSE
    END;

-- Apply Row Access Policy to Production Fact Sales Table
ALTER TABLE DATA_ENG_DB.ANALYTICS.FACT_SALES 
    ADD ROW ACCESS POLICY REGIONAL_STORE_POLICY ON (store_id);

-- Step 5: Test Governance Policies
SELECT customer_id, first_name, email FROM DATA_ENG_DB.STAGING.STG_CUSTOMERS LIMIT 5;
