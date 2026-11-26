/*
================================================================================
MODULE 08: Aggregate Functions (COUNT, SUM, AVG, MIN, MAX)
================================================================================
1. EXPLANATION:
Aggregate functions compute summary metrics across multiple rows.
*/

SELECT 
    COUNT(sales_id) AS total_transactions,
    SUM(net_amount) AS total_revenue,
    AVG(net_amount) AS average_order_value,
    MIN(net_amount) AS min_sale,
    MAX(net_amount) AS max_sale
FROM fact_sales
WHERE status = 'COMPLETED';
