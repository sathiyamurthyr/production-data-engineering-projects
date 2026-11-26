/*
================================================================================
MODULE 04: REDSHIFT COPY COMMAND (S3 BULK INGESTION)
================================================================================
Explanation:
  The `COPY` command is the fastest and most efficient way to load large volumes
  of data into Redshift from Amazon S3, EMR, DynamoDB, or SSH hosts. It reads
  data in parallel from multiple files in S3 by utilizing all compute slices.
  
  This script demonstrates how to copy data from S3 using:
  - CSV files (with headers, custom delimiters)
  - JSON files (with JSONPaths or AUTO mapping)
  - Parquet format (which automatically maps columns by name)
  - Manifest files (to enforce transactional consistency/parallelism)
  - Error handling options like MAXERROR and reviewing STL_LOAD_ERRORS.

Business Use Case:
  Loading raw sales and customer CSV/Parquet files from an enterprise S3 landing
  zone into the Redshift staging schema.

Production Example:
  Executing COPY commands with strict formatting options, IAM authorization, and
  logging configurations.

Expected Output:
  SQL templates for running high-performance COPY operations under different scenarios.

Performance Notes:
  - Split files so that the number of files is a multiple of the number of slices
    in your cluster (e.g., if you have 4 nodes with 2 slices each = 8 slices, split into 8, 16, 24 files).
  - Compress your files using GZIP, LZO, or BZIP2 to reduce S3 transfer times and storage costs.
  - Manifest files prevent the COPY command from loading files that were added
    after the ETL run started or loading duplicate records.

Optimization Tips:
  - Use PARQUET or ORC format for faster COPY times since Redshift can load them
    columnar-wise.
  - Ensure the S3 bucket is in the same AWS region as the Redshift cluster.

Common Mistakes:
  - Loading a single massive 100GB file. Only one slice will process it, creating
    a severe bottleneck and negating the MPP benefits of Redshift.
  - Forgetting to use COMPUPDATE ON for new tables, which computes column compression encodings during load.

Interview Questions:
  1. What is a Redshift Manifest File?
     Answer: A manifest file is a JSON-formatted file that lists the specific files
     to be loaded by a COPY command. It ensures that the COPY command loads only the
     specified files, even if other files are added to the S3 folder, and avoids duplicate loads.
  2. How do you troubleshoot failed COPY commands in Redshift?
     Answer: You query the `stl_load_errors` system table to see the exact reason, line,
     and column name that caused the failure, along with `sys_load_error_detail` or `sys_load_history`
     in newer Redshift environments.
================================================================================
*/

-- ==========================================
-- 1. COPY from CSV (Gzipped, Ignore Header)
-- ==========================================
-- Note: Replace IAM Role and Bucket Name placeholders with actual production values
COPY staging.staging_sales
FROM 's3://production-data-lake-us-east-1/redshift-etl/sales_data.csv.gz'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
CSV
GZIP
IGNOREHEADER 1
DATEFORMAT 'auto'
TIMEFORMAT 'auto'
COMPUPDATE OFF -- Off if encodings are already defined, ON if empty table
MAXERROR 0;    -- Fail immediately if any error occurs

-- ==========================================
-- 2. COPY using a Manifest File (Best Practice)
-- ==========================================
-- A manifest file format example:
-- {
--   "entries": [
--     {"url":"s3://production-data-lake-us-east-1/redshift-etl/sales_part_1.csv", "mandatory":true},
--     {"url":"s3://production-data-lake-us-east-1/redshift-etl/sales_part_2.csv", "mandatory":true}
--   ]
-- }
COPY staging.staging_sales
FROM 's3://production-data-lake-us-east-1/redshift-etl/sales_manifest.json'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
MANIFEST
CSV
IGNOREHEADER 1
DELIMITER ','
REGION 'us-east-1';

-- ==========================================
-- 3. COPY from PARQUET Format (Column-mapped)
-- ==========================================
-- Parquet matches columns by name, so table column names must match Parquet columns.
COPY staging.staging_sales
FROM 's3://production-data-lake-us-east-1/redshift-etl/parquet/sales/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
FORMAT AS PARQUET;

-- ==========================================
-- 4. Error Monitoring Queries
-- ==========================================
-- Querying STL_LOAD_ERRORS to debug issues (e.g., data type mismatches or line length issues)
SELECT 
    query, 
    starttime, 
    filename, 
    line_number, 
    colname, 
    err_code, 
    err_reason
FROM stl_load_errors
ORDER BY starttime DESC
LIMIT 10;
