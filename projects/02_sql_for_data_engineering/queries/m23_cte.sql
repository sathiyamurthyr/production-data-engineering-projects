/*
================================================================================
MODULE 23: Common Table Expressions (CTEs)
================================================================================
1. EXPLANATION:
CTEs (`WITH cte AS (...)`) define temporary named result sets, improving readability over deeply nested subqueries.
*/

WITH customer_summary AS (
    SELECT 
        customer_key,
        SUM(net_amount) AS total_spend,
        COUNT(sales_id) AS total_txns
    FROM fact_sales
    GROUP BY customer_key
)
SELECT 
    c.customer_id,
    cs.total_spend,
    cs.total_txns
FROM customer_summary AS cs
JOIN dim_customers AS c ON cs.customer_key = c.customer_key;
