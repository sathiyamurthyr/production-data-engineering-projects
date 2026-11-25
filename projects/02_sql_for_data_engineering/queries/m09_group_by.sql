/*
================================================================================
MODULE 09: GROUP BY Aggregation
================================================================================
1. EXPLANATION:
GROUP BY groups rows sharing common criteria to perform vector aggregations.
*/

SELECT 
    p.category,
    COUNT(s.sales_id) AS total_orders,
    SUM(s.net_amount) AS category_revenue
FROM fact_sales AS s
JOIN dim_products AS p ON s.product_key = p.product_key
GROUP BY p.category;
