/*
================================================================================
MODULE 01: AMAZON REDSHIFT BASICS, TABLE CREATION & COLUMN COMPRESSION
================================================================================
Explanation:
  This module demonstrates the fundamentals of table creation in Amazon Redshift,
  focusing on schema management, data types, primary/foreign key constraints
  (which are informational/not enforced by Redshift but used by the planner),
  and column encoding/compression.
  Redshift is a columnar database; selecting the correct compression encoding
  (e.g., AZ64, ZSTD, LZO, Runlength) reduces I/O and improves query speed.

Business Use Case:
  Designing a foundational schema for an E-commerce retail analytics warehouse.
  Storing transactional and customer dimension tables with optimal storage footprint
  and fast scan rates.

Production Example:
  We create a 'staging' schema for raw ingestion and a 'core' schema for our
  dimensional data warehouse. We then define the staging_sales table with ZSTD
  encoding for maximum flexibility.

Expected Output:
  Two schemas created (staging, core) and one staging table created with ZSTD/AZ64 encodings.

Performance Notes:
  - Redshift doesn't enforce primary/foreign key constraints. They are used by
    the query planner for query rewriting and join optimization. Ensuring your
    ETL guarantees uniqueness is critical.
  - AZ64 is a proprietary compression algorithm designed by Amazon that is
    highly effective for numeric, date, and time data types, providing both
    high compression and fast query performance.
  - ZSTD is excellent for string/varchar columns.

Optimization Tips:
  - Run `ANALYZE COMPRESSION <table_name>` to let Redshift recommend the
    most efficient encodings for your existing data.
  - Avoid using raw compression (ENCODING raw) except for the first column
    of a compound sort key.

Common Mistakes:
  - Assuming Redshift will throw an error on duplicate primary keys. It will not,
    which can lead to double-counting/incorrect aggregations.
  - Compressing the first column of a compound sort key (which degrades performance).

Interview Questions:
  1. Are primary key constraints enforced in Amazon Redshift?
     Answer: No. Redshift does not enforce primary, foreign, or unique key constraints
     during insert/update operations. They are informational and used by the query
     planner to optimize execution plans.
  2. What is the difference between ZSTD and AZ64 compression?
     Answer: AZ64 is Amazon's proprietary compression algorithm designed to compress
     numeric and date/time data types faster and tighter than LZO/ZSTD, while maintaining
     high query performance. ZSTD is a general-purpose algorithm that excels at
     compressing string/varchar data types.
================================================================================
*/

-- 1. Create Target Schemas
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

-- 2. Drop table if exists to ensure clean execution
DROP TABLE IF EXISTS staging.staging_sales;

-- 3. Create Table with Explicit Compression/Encoding
CREATE TABLE staging.staging_sales (
    sales_id INT ENCODING az64,
    customer_id INT ENCODING az64,
    product_id VARCHAR(50) ENCODING zstd,
    quantity INT ENCODING az64,
    unit_price NUMERIC(12, 2) ENCODING az64,
    discount NUMERIC(5, 2) ENCODING az64,
    sale_date TIMESTAMP ENCODING az64,
    payment_method VARCHAR(30) ENCODING zstd,
    ingest_timestamp TIMESTAMP DEFAULT GETDATE() ENCODING az64,
    
    -- Informational Constraints (Not Enforced)
    CONSTRAINT pk_staging_sales PRIMARY KEY (sales_id)
)
BACKUP YES; -- Indicates the table should be included in cluster snapshots

-- 4. Check Table Storage Encoding recommendations (Simulated execution)
-- In a live environment, you would run:
-- ANALYZE COMPRESSION staging.staging_sales;
