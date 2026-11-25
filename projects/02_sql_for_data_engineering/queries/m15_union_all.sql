/*
================================================================================
MODULE 15: UNION ALL & High-Performance Concatenation
================================================================================
1. EXPLANATION:
UNION ALL concatenates datasets without deduplication. Considerably faster than UNION because no sorting/distinct phase occurs.
*/

SELECT transaction_id, net_amount, 'SALES' AS source_type FROM fact_sales
UNION ALL
SELECT order_number, total_amount, 'ORDER' AS source_type FROM fact_orders;
