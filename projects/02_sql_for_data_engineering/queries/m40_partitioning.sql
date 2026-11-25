/*
================================================================================
MODULE 40: Table Partitioning Strategies
================================================================================
1. EXPLANATION:
Partitioning physically splits large tables into sub-folders/files by date or region to enable partition pruning.
*/

SELECT sale_date, COUNT(*) FROM fact_sales GROUP BY sale_date;
