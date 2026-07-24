-- Window Functions for Data Engineering Analytics
-- Business Use Case: Advanced data analysis without GROUP BY

-- ROW_NUMBER: Assign unique numbers to rows
SELECT 
    customer_id,
    first_name,
    last_name,
    ROW_NUMBER() OVER (PARTITION BY country ORDER BY signup_date DESC) as rn
FROM raw_customers;

-- RANK vs DENSE_RANK: Handle ties differently
SELECT 
    customer_id,
    total_amount,
    RANK() OVER (ORDER BY total_amount DESC) as rank_dense,
    DENSE_RANK() OVER (ORDER BY total_amount DESC) as dense_rank
FROM raw_orders ro
JOIN raw_customers rc ON ro.customer_id = rc.customer_id;

-- LAG/LEAD: Access previous/next row values
SELECT 
    order_id,
    customer_id,
    order_date,
    total_amount,
    LAG(total_amount, 1) OVER (PARTITION BY customer_id ORDER BY order_date) as prev_amount,
    LEAD(total_amount, 1) OVER (PARTITION BY customer_id ORDER BY order_date) as next_amount
FROM raw_orders
ORDER BY customer_id, order_date;

-- FIRST_VALUE/LAST_VALUE: Get first/last value in window
SELECT DISTINCT
    country,
    FIRST_VALUE(city) OVER (PARTITION BY country ORDER BY signup_date) as first_city,
    FIRST_VALUE(signup_date) OVER (PARTITION BY country ORDER BY signup_date) as first_signup
FROM raw_customers;

-- NTILE: Divide rows into buckets
SELECT 
    customer_id,
    total_amount,
    NTILE(4) OVER (ORDER BY total_amount DESC) as quartile
FROM raw_orders;

-- Running Totals: Cumulative sum
SELECT 
    order_date,
    total_amount,
    SUM(total_amount) OVER (ORDER BY order_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as running_total
FROM raw_orders;

-- Moving Average: 7-day rolling average (for time-series)
SELECT 
    order_date,
    total_amount,
    AVG(total_amount) OVER (ORDER BY order_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as moving_avg_7day
FROM (
    SELECT 
        order_date::date as order_date,
        SUM(total_amount) as total_amount
    FROM raw_orders
    GROUP BY order_date::date
) daily_sales;

-- Percentile Rank: Find percentile of each value
SELECT 
    customer_id,
    total_amount,
    PERCENT_RANK() OVER (ORDER BY total_amount) as percentile
FROM raw_orders;

-- Cumulative Count: Running count partitioned by status
SELECT 
    order_id,
    order_status,
    order_date,
    COUNT(*) OVER (PARTITION BY order_status 
        ORDER BY order_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as running_count
FROM raw_orders;