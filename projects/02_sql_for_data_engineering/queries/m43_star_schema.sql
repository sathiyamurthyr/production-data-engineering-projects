/*
================================================================================
MODULE 43: Star Schema Architecture
================================================================================
1. EXPLANATION:
Star Schema centers quantitative Fact tables surrounded by denormalized Dimension tables.
*/

SELECT 
    c.city,
    p.category,
    SUM(s.net_amount) AS total_sales
FROM fact_sales s
JOIN dim_customers c ON s.customer_key = c.customer_key
JOIN dim_products p ON s.product_key = p.product_key
GROUP BY c.city, p.category;
