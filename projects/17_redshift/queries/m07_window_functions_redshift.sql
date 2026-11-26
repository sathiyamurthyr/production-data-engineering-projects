/*
================================================================================
MODULE 07: WINDOW FUNCTIONS & OLAP ANALYTICS
================================================================================
Explanation:
  Window functions compute aggregate values over a group of rows (called a window)
  that are related to the current row. Unlike normal aggregates, window functions
  do not group the output rows into a single row; each row retains its identity.
  Redshift supports rich window analytical functions (ranking, offsets, rolling frames).

  This module covers:
  - Ranking: ROW_NUMBER, RANK, DENSE_RANK
  - Offsets: LAG, LEAD
  - Running/Cumulative Totals with explicit window framing (ROWS/RANGE clauses)
  - FIRST_VALUE & LAST_VALUE

Business Use Case:
  Analyzing sales patterns to rank customers by their total spending, finding
  days between consecutive purchases for each customer, and calculating
  rolling 3-day average sales.

Production Example:
  We query the fact_sales and dim_customer tables to build complex analytics.

Expected Output:
  Analytics query templates ready to execute for analytical reporting.

Performance Notes:
  - Window functions require sorting the partition columns. If the columns in
    PARTITION BY and ORDER BY do not match the table's distribution and sort keys,
    Redshift must redistribute and sort the data on the fly, which can be expensive.
  - Keep frame clauses precise. `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
    is highly optimized in Redshift.

Optimization Tips:
  - Try to partition window queries on the distribution key of the table (or a colocated key)
    to prevent data from being reshuffled across slices during query execution.
  - Limit the number of distinct PARTITION BY structures in a single query block to prevent
    multiple physical sorting runs in temp space.

Common Mistakes:
  - Using `ORDER BY` in window functions without partition keys on large unindexed tables,
    forcing a global sort of all data on a single slice.
  - Using range frame clauses (RANGE) when row-based frame clauses (ROWS) would suffice,
    as ROWS is generally faster.

Interview Questions:
  1. What is the difference between RANK() and DENSE_RANK()?
     Answer: If there is a tie, `RANK()` skips ranks (e.g., 1, 2, 2, 4), whereas
     `DENSE_RANK()` does not skip ranks (e.g., 1, 2, 2, 3).
  2. How can you optimize a query with window functions in Redshift?
     Answer: Make sure the partition column matches the table's distribution key.
     If the data is already sorted by the columns in the ORDER BY clause of the window
     function (using the sort key), it reduces the sorting overhead.
================================================================================
*/

-- 1. Ranking Customers by Daily Purchase Amounts
SELECT 
    customer_id,
    DATE(sale_date) AS purchase_date,
    SUM(quantity * unit_price) AS daily_spend,
    
    -- Row numbering: unique row ID within the customer's partition
    ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY SUM(quantity * unit_price) DESC) AS rank_row_num,
    
    -- Rank: has gaps if there are duplicate daily spends
    RANK() OVER(PARTITION BY customer_id ORDER BY SUM(quantity * unit_price) DESC) AS rank_standard,
    
    -- Dense Rank: no gaps
    DENSE_RANK() OVER(PARTITION BY customer_id ORDER BY SUM(quantity * unit_price) DESC) AS rank_dense
FROM core.fact_sales
GROUP BY customer_id, DATE(sale_date)
ORDER BY customer_id, daily_spend DESC;

-- 2. Calculating Days & Difference Between Purchases (LAG/LEAD)
SELECT 
    sales_id,
    customer_id,
    sale_date,
    (quantity * unit_price) AS sale_amount,
    
    -- Retrieve the amount of the previous sale
    LAG(quantity * unit_price, 1, 0.0) OVER(PARTITION BY customer_id ORDER BY sale_date) AS prev_sale_amount,
    
    -- Retrieve the date of the next sale
    LEAD(sale_date, 1) OVER(PARTITION BY customer_id ORDER BY sale_date) AS next_sale_date,
    
    -- Duration between current and previous sale
    DATEDIFF('day', LAG(sale_date, 1) OVER(PARTITION BY customer_id ORDER BY sale_date), sale_date) AS days_since_last_sale
FROM core.fact_sales
ORDER BY customer_id, sale_date;

-- 3. Rolling Cumulative Totals & Moving Averages (Window Frame Clauses)
SELECT 
    DATE(sale_date) AS sale_day,
    SUM(quantity * unit_price) AS daily_revenue,
    
    -- Cumulative sum from start of time to current row
    SUM(SUM(quantity * unit_price)) OVER(
        ORDER BY DATE(sale_date) 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,
    
    -- Rolling 3-day average revenue (current day and previous 2 days)
    AVG(SUM(quantity * unit_price)) OVER(
        ORDER BY DATE(sale_date) 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3_day_avg
FROM core.fact_sales
GROUP BY DATE(sale_date)
ORDER BY sale_day;
