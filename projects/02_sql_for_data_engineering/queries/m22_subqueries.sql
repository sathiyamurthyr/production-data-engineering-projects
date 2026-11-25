/*
================================================================================
MODULE 22: Subqueries & Nested Statements
================================================================================
1. EXPLANATION:
Subqueries are queries nested inside another query (in WHERE, FROM, or SELECT clauses).
*/

SELECT 
    transaction_id,
    net_amount
FROM fact_sales
WHERE net_amount > (SELECT AVG(net_amount) FROM fact_sales);
