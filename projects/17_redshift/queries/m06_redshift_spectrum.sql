/*
================================================================================
MODULE 06: REDSHIFT SPECTRUM (EXTERNAL TABLES & DATA LAKES)
================================================================================
Explanation:
  Redshift Spectrum allows you to query data directly from files in Amazon S3
  without loading them into local Redshift tables. It utilizes a separate
  managed serverless compute layer to scan S3 files, perform filters/joins,
  and stream results back to the Redshift cluster.
  
  This script demonstrates:
  - Creating an external database in Glue Catalog.
  - Creating an external schema.
  - Defining a partitioned external table mapping Parquet files in S3.
  - Querying and joining external S3 data with local Redshift tables.

Business Use Case:
  Querying historical sales data stored in an S3 cold-storage bucket (in Parquet format)
  to join with current dimension tables in Redshift core for customer segmentation.

Production Example:
  Creating an external schema mapped to an AWS Glue database and referencing partitioned Parquet files.

Expected Output:
  An external schema defined, an external table structure registered, and partition mapping examples.

Performance Notes:
  - Redshift Spectrum charges per terabyte of data scanned (typically $5/TB).
  - Use columnar formats like Parquet or ORC with compression (GZIP, Snappy) to
    minimize bytes scanned, saving cost and improving execution time.
  - Partition external tables by frequent filter criteria (e.g., date columns).

Optimization Tips:
  - Write queries that push filters (WHERE clauses) and aggregations down to the
    Spectrum layer (known as predicate pushdown).
  - Avoid scanning unpartitioned folders with raw text files.

Common Mistakes:
  - Pointing the external table location to an S3 folder containing mixed file formats
    (e.g., CSV and Parquet in the same prefix).
  - Forgetting to run `ALTER TABLE ADD PARTITION` when new files are written to S3.

Interview Questions:
  1. What is Amazon Redshift Spectrum and how is it priced?
     Answer: Redshift Spectrum is a feature that allows querying data directly in S3
     using SQL without importing it into Redshift. It is priced based on the volume
     of data scanned from S3 (by the Spectrum layer), rounded to the next megabyte,
     with a minimum of 10MB per query.
  2. How do you register new S3 partitions for a Redshift Spectrum table?
     Answer: You can use `ALTER TABLE <external_table> ADD PARTITION` to register them manually,
     or use AWS Glue Crawlers to scan S3 and update the Catalog automatically.
================================================================================
*/

-- 1. Create External Schema linked to AWS Glue Data Catalog
-- Note: Requires a Redshift cluster with an IAM role that can access Glue and S3.
CREATE EXTERNAL SCHEMA IF NOT EXISTS spectrum_schema
FROM DATA CATALOG
DATABASE 'spectrum_db'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3AccessRole'
CREATE EXTERNAL DATABASE IF NOT EXISTS;

-- 2. Create External Table on Partitioned Parquet files in S3
DROP TABLE IF EXISTS spectrum_schema.external_historical_sales;
CREATE EXTERNAL TABLE spectrum_schema.external_historical_sales (
    sales_id INT,
    customer_id INT,
    product_id VARCHAR(50),
    quantity INT,
    unit_price NUMERIC(12, 2)
)
PARTITIONED BY (sale_year VARCHAR(4), sale_month VARCHAR(2))
STORED AS PARQUET
LOCATION 's3://production-data-lake-us-east-1/redshift-etl/unload/sales_parquet_partitioned/';

-- 3. Register Partitions Manually (Simulated example)
-- In production, ETL pipelines execute these commands after saving partition files to S3.
ALTER TABLE spectrum_schema.external_historical_sales 
ADD PARTITION (sale_year='2026', sale_month='07') 
LOCATION 's3://production-data-lake-us-east-1/redshift-etl/unload/sales_parquet_partitioned/sale_year=2026/sale_month=07/';

-- 4. Query External Table and JOIN with Redshift local dimension tables
-- The query planner pushes filtering and partitioning down to the Spectrum engine.
SELECT 
    ext.sale_year,
    ext.sale_month,
    cust.country,
    SUM(ext.quantity * ext.unit_price) AS total_sales_amount
FROM spectrum_schema.external_historical_sales ext
INNER JOIN core.dim_customer cust 
    ON ext.customer_id = cust.customer_id
WHERE ext.sale_year = '2026'
  AND cust.is_active = TRUE
GROUP BY ext.sale_year, ext.sale_month, cust.country
ORDER BY total_sales_amount DESC;
