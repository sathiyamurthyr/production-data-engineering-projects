/*
================================================================================
MODULE 05: REDSHIFT UNLOAD COMMAND (EXPORT TO S3)
================================================================================
Explanation:
  The `UNLOAD` command unloads the results of a SELECT query from a Redshift
  cluster to text, CSV, JSON, or Parquet files on Amazon S3. 
  By default, UNLOAD writes data in parallel to multiple files based on the number
  of slices in the cluster, but it can be configured to write sequentially.

  This module covers:
  - Parallel vs. Sequential UNLOAD
  - Exporting as CSV with Headers
  - Exporting as Partitioned Parquet files
  - Generating Manifest files for down-stream validation.

Business Use Case:
  Exporting aggregated core tables (e.g. monthly sales summaries) to an external S3 bucket
  for consumption by a downstream Machine Learning team or BI tool running Athena.

Production Example:
  Unloading records from core.fact_sales to S3 with partition filters and GZIP compression.

Expected Output:
  SQL templates showing various UNLOAD configurations with explanation of performance behaviors.

Performance Notes:
  - PARALLEL ON: Each slice writes its partition of data to S3. This maximizes throughput
    but generates multiple files (e.g., part-0000_part_00, part-0001_part_00).
  - PARALLEL OFF: Data is serialized and written to a single file. Useful for small datasets,
    but can bottleneck the leader node if used for large datasets.
  - Using partitioning (PARTITION BY) creates nested folders in S3 (e.g., year=2026/month=07/).

Optimization Tips:
  - Always use PARALLEL ON for large datasets.
  - Limit the columns in the SELECT statement to only what is required to reduce S3 outbound payload.
  - Prefer PARQUET format for downstream analytical querying.

Common Mistakes:
  - Forgetting to empty target directories or not using the ALLOWOVERWRITE option,
    which causes the UNLOAD command to fail if files exist.
  - Unloading millions of rows with PARALLEL OFF, leading to out-of-memory or timeout errors.

Interview Questions:
  1. What is the behavior of the UNLOAD command when PARALLEL is set to ON?
     Answer: When PARALLEL ON is set, Redshift unloads data by writing to multiple files
     simultaneously, one or more files per slice. The files are named with prefixes of
     the slices that wrote them, ensuring high-speed data transfer.
  2. How can you ensure downstream processes know exactly which files were written by UNLOAD?
     Answer: By specifying the MANIFEST option in the UNLOAD command. This generates
     a JSON manifest file in S3 listing all the exact file paths that were output.
================================================================================
*/

-- ==========================================
-- 1. Standard Parallel UNLOAD (CSV with GZIP)
-- ==========================================
UNLOAD ('
    SELECT 
        sales_id,
        customer_id,
        product_id,
        quantity,
        unit_price,
        sale_date
    FROM core.fact_sales
')
TO 's3://production-data-lake-us-east-1/redshift-etl/unload/sales_csv/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
CSV
GZIP
MANIFEST
HEADER
ALLOWOVERWRITE; -- Replaces files if they already exist in the target folder

-- ==========================================
-- 2. Sequential UNLOAD (PARALLEL OFF, Single File)
-- ==========================================
-- Suitable only for small lookup data or extracts
UNLOAD ('
    SELECT payment_method_id, payment_method_name, payment_method_type 
    FROM core.dim_payment_method
')
TO 's3://production-data-lake-us-east-1/redshift-etl/unload/payment_methods_single/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
CSV
HEADER
PARALLEL OFF -- Forces a single file output
ALLOWOVERWRITE;

-- ==========================================
-- 3. Partitioned PARQUET UNLOAD (Athena Integration)
-- ==========================================
-- Unloads data partitioned by year and month into folder partitions
UNLOAD ('
    SELECT 
        sales_id,
        customer_id,
        product_id,
        quantity,
        unit_price,
        TO_CHAR(sale_date, \'YYYY\') AS sale_year,
        TO_CHAR(sale_date, \'MM\') AS sale_month
    FROM core.fact_sales
')
TO 's3://production-data-lake-us-east-1/redshift-etl/unload/sales_parquet_partitioned/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
FORMAT AS PARQUET
PARTITION BY (sale_year, sale_month)
ALLOWOVERWRITE;
