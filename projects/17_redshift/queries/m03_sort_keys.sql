/*
================================================================================
MODULE 03: SORT KEYS (COMPOUND VS INTERLEAVED)
================================================================================
Explanation:
  Sort keys define the physical storage order of data rows on disk slices.
  Using sort keys allows Redshift to skip entire blocks of data during scans
  by leveraging zone maps (which store min/max values for each 1MB block).
  
  Types:
  - COMPOUND Sort Keys: Columns are sorted in the order defined (e.g., col1, then col2).
    Excellent for queries filtering by the first column, or sorting/grouping by those columns.
  - INTERLEAVED Sort Keys: Gives equal weight to every column in the sort key.
    Useful when queries filter on different columns in different combinations,
    but comes with significant vacuum and load overhead.

Business Use Case:
  An analytics dashboard that queries sales transactions. Some reports filter
  mostly by date (Compound Sort Key). Other reports search randomly by date, customer, or product
  (Interleaved Sort Key candidate).

Production Example:
  We create a table with a Compound Sort Key (sale_date, product_id) and another table
  with an Interleaved Sort Key (customer_id, product_id) for comparison.

Expected Output:
  Two tables demonstrating COMPOUND and INTERLEAVED sort key definitions.

Performance Notes:
  - For COMPOUND sort keys, the order of columns is critical. The primary filter
    column must come first. If you filter on the second column without the first,
    the sort key is much less effective.
  - INTERLEAVED sort keys work well on high-cardinality columns. However, loading
    data into interleaved tables requires more CPU and regular `VACUUM REINDEX`.

Optimization Tips:
  - Keep the number of columns in a sort key low (normally 1-4 columns).
  - The first column of a COMPOUND sort key should NOT be compressed (RAW encoding).
    This allows the zone maps to work efficiently without decompression overhead.

Common Mistakes:
  - Creating a compound sort key on (product_id, sale_date) when 90% of queries
    filter on `sale_date` only. The sort key will not be used.
  - Using interleaved sort keys on monotonically increasing values (like timestamps or auto-increment IDs).

Interview Questions:
  1. What is the difference between Compound and Interleaved sort keys?
     Answer: Compound sort keys sort data hierarchically (col1 first, then col2, etc.).
     They are best for prefix filters, joins, and group by operations. Interleaved sort
     keys give equal weight to all columns, making them suitable when queries filter on
     various columns in different patterns, but they are expensive to maintain.
  2. How do Zone Maps work with Sort Keys in Redshift?
     Answer: Redshift stores data in 1MB blocks. Zone maps contain the minimum and
     maximum values of each column for every block. When a query filters using a sorted
     column, the leader node uses the zone maps to identify which blocks can be skipped,
     greatly reducing I/O.
================================================================================
*/

-- 1. Table with COMPOUND Sort Key (Default)
-- Note: The first sort key column (sale_date) should ideally be RAW encoding,
-- though Redshift can handle compressed sort keys, RAW is standard best practice for the first column.
DROP TABLE IF EXISTS core.sales_compound_sort;
CREATE TABLE core.sales_compound_sort (
    sales_id INT ENCODING az64,
    customer_id INT ENCODING az64,
    product_id VARCHAR(50) ENCODING zstd,
    quantity INT ENCODING az64,
    unit_price NUMERIC(12, 2) ENCODING az64,
    discount NUMERIC(5, 2) ENCODING az64,
    sale_date TIMESTAMP ENCODING raw, -- Raw encoding for first sort column
    payment_method VARCHAR(30) ENCODING zstd
)
DISTSTYLE KEY
DISTKEY(customer_id)
COMPOUND SORTKEY(sale_date, product_id); -- Hierarchical sorting: sale_date first, then product_id

-- 2. Table with INTERLEAVED Sort Key
DROP TABLE IF EXISTS core.sales_interleaved_sort;
CREATE TABLE core.sales_interleaved_sort (
    sales_id INT ENCODING az64,
    customer_id INT ENCODING raw, -- Raw for sort columns is recommended
    product_id VARCHAR(50) ENCODING raw,
    quantity INT ENCODING az64,
    unit_price NUMERIC(12, 2) ENCODING az64,
    discount NUMERIC(5, 2) ENCODING az64,
    sale_date TIMESTAMP ENCODING az64,
    payment_method VARCHAR(30) ENCODING zstd
)
DISTSTYLE KEY
DISTKEY(customer_id)
INTERLEAVED SORTKEY(customer_id, product_id); -- Equal weight to customer_id and product_id

-- 3. Query system tables to inspect sort key and distribution performance
SELECT 
    schemaname,
    tablename,
    "size" AS size_in_mb,
    tbl_rows AS row_count,
    unsorted AS pct_unsorted,
    stats_off AS pct_stats_out_of_date
FROM svv_table_info
WHERE tablename IN ('sales_compound_sort', 'sales_interleaved_sort');
