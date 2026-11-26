/*
================================================================================
MODULE 25: Window Functions & Analytic Over Clauses
================================================================================
1. EXPLANATION:
Window functions perform calculations across a set of table rows related to the current row without collapsing rows.
*/

SELECT 
    sales_id,
    customer_key,
    sale_date,
    net_amount,
    SUM(net_amount) OVER (PARTITION BY customer_key ORDER BY sale_date) AS running_customer_total
FROM fact_sales;
