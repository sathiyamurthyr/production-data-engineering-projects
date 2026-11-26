/*
================================================================================
MODULE 31: Relational Views & Logical Abstraction
================================================================================
1. EXPLANATION:
Views save query definitions as virtual tables for security and abstraction.
*/

CREATE VIEW IF NOT EXISTS vw_daily_sales_summary AS
SELECT 
    sale_date,
    COUNT(sales_id) AS total_transactions,
    SUM(net_amount) AS total_revenue
FROM fact_sales
WHERE status = 'COMPLETED'
GROUP BY sale_date;

SELECT * FROM vw_daily_sales_summary;
