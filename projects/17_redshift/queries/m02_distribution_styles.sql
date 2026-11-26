/*
================================================================================
MODULE 02: DISTRIBUTION STYLES (KEY, EVEN, ALL, AUTO)
================================================================================
Explanation:
  This module explains and demonstrates Amazon Redshift distribution styles.
  Distribution styles determine how data is allocated across compute nodes and
  slices in a Redshift cluster. Choosing the right distribution style minimizes
  data redistribution (shuffling) across nodes during joins and aggregations.
  
  Styles:
  - KEY: Rows are distributed based on the hash of a single column.
  - EVEN: Rows are distributed round-robin across slices (default for medium/large tables).
  - ALL: A copy of the entire table is placed on every compute node (ideal for small dimensions).
  - AUTO: Redshift automatically assigns and adjusts the distribution style (starts as ALL, changes to KEY or EVEN).

Business Use Case:
  Designing a star schema for sales transactions where the transaction table
  (sales) is large and joined with a customer table and a small payment methods table.

Production Example:
  We distribute `sales` by customer_id (KEY), `customer` by customer_id (KEY)
  to ensure colocated joins, and `payment_methods` to ALL nodes.

Expected Output:
  Three production tables created in the core schema using different distribution styles.

Performance Notes:
  - KEY distribution colocates matching keys on the same slice. When joining on the
    distribution key, Redshift does not need to send data across the network (DS_DIST_NONE).
  - ALL distribution eliminates network transit during joins with small lookup tables,
    but increases storage footprint and slows down write/load times.

Optimization Tips:
  - Choose a distribution key that has high cardinality and is frequently used in JOINs.
  - Do not choose a distribution key that leads to data skew (e.g., nullable column,
    or column where 80% of values are identical).

Common Mistakes:
  - Setting ALL distribution on a table that is too large (> 3-5M rows). This consumes
    excessive disk space and degrades write speeds (since every node must write every row).
  - Distributing on a key that causes severe data skew, creating hot slices.

Interview Questions:
  1. What is "colocated join" in Amazon Redshift?
     Answer: A colocated join occurs when two tables are joined on their distribution
     keys. Since rows with the same hash key reside on the same compute slice, Redshift
     can perform the join locally on each slice without redistributing data over the
     internal network (avoiding DS_DIST_INNER/DS_DIST_BOTH).
  2. When would you use DISTSTYLE ALL vs DISTSTYLE KEY?
     Answer: Use DISTSTYLE ALL for small, slowly changing dimension tables (typically < 3-5 million rows)
     that are frequently joined with larger fact tables. Use DISTSTYLE KEY for large tables (like facts or
     heavy dimensions) that are joined together on a common high-cardinality key (e.g., customer_id or order_id).
================================================================================
*/

-- 1. Large Fact Table using DISTSTYLE KEY (distributed on customer_id)
DROP TABLE IF EXISTS core.fact_sales;
CREATE TABLE core.fact_sales (
    sales_id INT NOT NULL,
    customer_id INT NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INT,
    unit_price NUMERIC(12, 2),
    discount NUMERIC(5, 2),
    sale_date TIMESTAMP,
    payment_method_id INT
)
DISTSTYLE KEY
DISTKEY(customer_id); -- Hash-distributed on customer_id

-- 2. Large Dimension Table using DISTSTYLE KEY (co-located join key)
DROP TABLE IF EXISTS core.dim_customer;
CREATE TABLE core.dim_customer (
    customer_id INT NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    gender VARCHAR(10),
    country VARCHAR(50),
    signup_date DATE,
    is_active BOOLEAN
)
DISTSTYLE KEY
DISTKEY(customer_id); -- Matches fact_sales distkey for colocated joins

-- 3. Small Lookup Table using DISTSTYLE ALL (copied to every node)
DROP TABLE IF EXISTS core.dim_payment_method;
CREATE TABLE core.dim_payment_method (
    payment_method_id INT NOT NULL,
    payment_method_name VARCHAR(30),
    payment_method_type VARCHAR(20)
)
DISTSTYLE ALL; -- Copied to every compute node

-- 4. Audit Query to check data distribution skew across slices
-- This query provides visibility into how many rows are on each slice for fact_sales.
SELECT 
    slice, 
    col, 
    num_values AS row_count, 
    minwidth, 
    maxwidth 
FROM svv_diskusage 
WHERE name = 'fact_sales' 
ORDER BY slice, col;
