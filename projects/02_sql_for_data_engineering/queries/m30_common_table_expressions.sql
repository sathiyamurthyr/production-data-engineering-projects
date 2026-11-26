/*
================================================================================
MODULE 30: Multi-Step CTE Pipelines
================================================================================
1. EXPLANATION:
Multiple CTEs chained together build clear modular ETL data transformation pipelines.
*/

WITH raw_sales AS (
    SELECT customer_key, net_amount FROM fact_sales WHERE status = 'COMPLETED'
),
customer_totals AS (
    SELECT customer_key, SUM(net_amount) AS total_spend FROM raw_sales GROUP BY customer_key
)
SELECT 
    c.customer_id,
    ct.total_spend
FROM customer_totals ct
JOIN dim_customers c ON ct.customer_key = c.customer_key;
