/*
================================================================================
MODULE 52: Source to Target Data Reconciliation
================================================================================
1. EXPLANATION:
Reconciliation audits record counts and monetary sums between source transactional DB and Target Data Warehouse.
*/

SELECT 
    'fact_sales' AS target_table,
    COUNT(*) AS target_record_count,
    SUM(net_amount) AS target_total_revenue
FROM fact_sales;
