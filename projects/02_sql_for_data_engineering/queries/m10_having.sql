/*
================================================================================
MODULE 10: HAVING Clause & Group Filtering
================================================================================
1. EXPLANATION:
HAVING filters aggregated groups AFTER `GROUP BY` completes. Contrast with `WHERE` which filters rows before aggregation.
*/

SELECT 
    customer_key,
    SUM(net_amount) AS total_spend
FROM fact_sales
GROUP BY customer_key
HAVING SUM(net_amount) > 2000.00;
