/*
================================================================================
MODULE 54: Production ETL SQL Query Patterns
================================================================================
1. EXPLANATION:
Combines CTEs, Window Functions, and Null handling into a production-grade analytical data pipeline query.
*/

WITH valid_sales AS (
    SELECT 
        customer_key,
        product_key,
        net_amount,
        sale_date
    FROM fact_sales
    WHERE status = 'COMPLETED' AND net_amount > 0
),
customer_metrics AS (
    SELECT 
        customer_key,
        SUM(net_amount) AS total_spent,
        COUNT(*) AS order_count,
        MAX(sale_date) AS last_order_date
    FROM valid_sales
    GROUP BY customer_key
)
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    cm.total_spent,
    cm.order_count,
    cm.last_order_date
FROM customer_metrics cm
JOIN dim_customers c ON cm.customer_key = c.customer_key
ORDER BY cm.total_spent DESC;
