/*
================================================================================
MODULE 42: Denormalization for Analytical Warehouses
================================================================================
1. EXPLANATION:
Denormalization combines normalized tables into wide fact/dimension schemas to optimize read throughput.
*/

SELECT 
    s.transaction_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    p.product_name,
    p.category,
    s.net_amount
FROM fact_sales s
JOIN dim_customers c ON s.customer_key = c.customer_key
JOIN dim_products p ON s.product_key = p.product_key;
