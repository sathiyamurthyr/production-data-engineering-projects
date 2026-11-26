/*
================================================================================
MODULE 03: Internal, External Stages & Directory Tables
================================================================================

1. EXPLANATION:
Stages in Snowflake represent storage locations for data files. 
- User Stage (`@~`): Tied to a specific Snowflake user.
- Table Stage (`@%table_name`): Tied to a specific table.
- Named Internal Stage: Snowflake-managed cloud storage bucket.
- Named External Stage: External cloud storage (AWS S3, Azure Blob, GCP GCS) integrated via IAM roles.

2. BUSINESS USE CASE:
Create secure cloud storage integration with AWS S3 for continuous streaming file ingestion, 
and enable Directory Tables to query file metadata (file size, MD5 checksum, last modified date).

3. PRODUCTION EXAMPLE:
Create internal and external stages with directory table metadata indexing enabled, list staged files, 
and refresh stage directory indexes.

4. EXPECTED OUTPUT:
Created stage objects and active directory table metadata query results.

5. PERFORMANCE NOTES:
Directory Tables store file metadata in internal tables, enabling instant query access without calling AWS/Cloud APIs.

6. OPTIMIZATION TIPS:
- Always enable directory tables (`DIRECTORY = (ENABLE = TRUE)`) on high-throughput stages.
- Run `ALTER STAGE stage_name REFRESH` when new files arrive externally without explicit COPY INTO triggers.

7. COMMON MISTAKES:
- Storing hardcoded AWS access key ID and secret access key in SQL scripts instead of Storage Integrations.

8. INTERVIEW QUESTIONS:
Q: What is a Storage Integration in Snowflake and why is it preferred over AWS credentials?
A: A Storage Integration is an account-level object that delegates authentication to AWS IAM roles using trust policies, 
   eliminating the need to hardcode secret access keys in stage definitions.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA STAGING;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Named Internal Stage with Directory Table Enabled
CREATE OR REPLACE STAGE RAW_INTERNAL_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Named internal stage for raw staging datasets';

-- Step 2: Simulate External Stage Creation via Storage Integration (S3 Syntax Example)
/*
CREATE OR REPLACE STORAGE INTEGRATION S3_DE_INTEGRATION
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::123456789012:role/snowflake_s3_role'
    STORAGE_ALLOWED_LOCATIONS = ('s3://my-enterprise-data-lake/landing/');
*/

CREATE OR REPLACE STAGE S3_RAW_STAGE
    URL = 's3://my-enterprise-data-lake/landing/'
    -- STORAGE_INTEGRATION = S3_DE_INTEGRATION
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'External S3 stage for landing zone data';

-- Step 3: Manage & List Files in Internal Stages
-- List files in internal stage
LIST @RAW_INTERNAL_STAGE;

-- Step 4: Refresh Directory Table Metadata
ALTER STAGE RAW_INTERNAL_STAGE REFRESH;

-- Step 5: Query Directory Table Metadata using SQL
SELECT 
    RELATIVE_PATH AS file_name,
    SIZE AS file_size_bytes,
    LAST_MODIFIED AS last_modified_timestamp,
    MD5 AS file_checksum
FROM DIRECTORY(@RAW_INTERNAL_STAGE)
WHERE SIZE > 0
ORDER BY LAST_MODIFIED DESC;
