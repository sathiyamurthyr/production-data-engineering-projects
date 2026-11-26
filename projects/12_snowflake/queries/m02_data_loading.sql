/*
================================================================================
MODULE 02: Bulk Data Loading with COPY INTO & File Formats
================================================================================

1. EXPLANATION:
Snowflake loads data efficiently using the `COPY INTO` command from internal or external stages. 
File Formats define structural parsing rules for CSV, JSON, Parquet, Avro, and ORC files.

2. BUSINESS USE CASE:
Ingest daily sales records and customer profiles from CSV and JSON landing zones into staging tables 
with automatic error handling, schema column matching, and file purging.

3. PRODUCTION EXAMPLE:
Create explicit CSV and JSON file formats, validate data files before loading using `VALIDATION_MODE`, 
and run `COPY INTO` with `ON_ERROR = CONTINUE` and `MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE`.

4. EXPECTED OUTPUT:
Loaded target tables (`STG_SALES`, `STG_CUSTOMERS`) populated with parsed data and load summary status.

5. PERFORMANCE NOTES:
Snowflake automatically splits large files for parallel loading. Ideal file size is 100MB-250MB compressed.

6. OPTIMIZATION TIPS:
- Pre-compress files (gzip/snappy) before uploading.
- Use `MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE` to allow column ordering independence between source and table.

7. COMMON MISTAKES:
- Loading uncompressed single multi-gigabyte files which prevents parallel loading worker threads.
- Not using `VALIDATION_MODE` prior to executing batch ingestion on critical pipelines.

8. INTERVIEW QUESTIONS:
Q: What does ON_ERROR = CONTINUE do during a COPY INTO operation?
A: It instructs Snowflake to skip corrupted or invalid records and continue loading valid records, returning load details for bad rows.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA STAGING;
USE WAREHOUSE ETL_WH;

-- Step 1: Create File Formats
CREATE OR REPLACE FILE FORMAT CSV_HEADER_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL = TRUE
    COMPRESSION = 'AUTO';

CREATE OR REPLACE FILE FORMAT JSON_STRIP_ARRAY_FORMAT
    TYPE = 'JSON'
    COMPRESSION = 'AUTO'
    STRIP_OUTER_ARRAY = TRUE
    IGNORE_UTF8_ERRORS = FALSE;

-- Step 2: Create Target Staging Table
CREATE OR REPLACE TABLE STG_SALES (
    transaction_id VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(50),
    quantity INT,
    unit_price NUMBER(10,2),
    total_amount NUMBER(10,2),
    payment_method VARCHAR(30),
    store_id VARCHAR(50),
    transaction_timestamp TIMESTAMP_NTZ
);

-- Step 3: Validate Staged Files Before Loading (Dry Run)
-- VALIDATION_MODE = RETURN_ERRORS checks staged files without inserting data
COPY INTO STG_SALES
FROM @DATA_ENG_DB.STAGING.RAW_INTERNAL_STAGE
FILE_FORMAT = (FORMAT_NAME = 'CSV_HEADER_FORMAT')
PATTERN = '.*sales.*\\.csv.*'
VALIDATION_MODE = 'RETURN_ERRORS';

-- Step 4: Execute High-Performance Bulk Load
COPY INTO STG_SALES
FROM @DATA_ENG_DB.STAGING.RAW_INTERNAL_STAGE
FILE_FORMAT = (FORMAT_NAME = 'CSV_HEADER_FORMAT')
PATTERN = '.*sales_data.*\\.csv.*'
ON_ERROR = 'CONTINUE'
PURGE = FALSE
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;

-- Step 5: Verify Ingested Records & Ingestion Metadata
SELECT 
    COUNT(*) AS total_loaded_rows,
    MIN(transaction_timestamp) AS earliest_transaction,
    MAX(transaction_timestamp) AS latest_transaction
FROM STG_SALES;
