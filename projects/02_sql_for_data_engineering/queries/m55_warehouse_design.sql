/*
================================================================================
MODULE 55: Enterprise Data Warehouse Architecture & Modeling
================================================================================
1. EXPLANATION:
Comprehensive warehouse architectural model integrating Star Schema, SCD Type 2, Incremental Loading,
and Data Quality Validation.
*/

SELECT 
    p.category,
    COUNT(DISTINCT s.customer_key) AS unique_buyers,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.net_amount), 2) AS total_revenue
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE c.is_current = 1 AND s.status = 'COMPLETED'
GROUP BY p.category
ORDER BY total_revenue DESC;
