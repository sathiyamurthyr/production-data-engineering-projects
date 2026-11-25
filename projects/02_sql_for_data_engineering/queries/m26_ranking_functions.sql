/*
================================================================================
MODULE 26: Ranking Functions (ROW_NUMBER, RANK, DENSE_RANK, NTILE)
================================================================================
1. EXPLANATION:
- ROW_NUMBER(): Unique incremental rank per row (no ties).
- RANK(): Equal values get identical rank, with gap numbers skipped.
- DENSE_RANK(): Equal values get identical rank, with no gaps skipped.
- NTILE(N): Divide partition into N buckets.
*/

SELECT 
    product_key,
    category,
    unit_price,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY unit_price DESC) AS row_num,
    RANK() OVER (PARTITION BY category ORDER BY unit_price DESC) AS rank_num,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY unit_price DESC) AS dense_rank_num,
    NTILE(2) OVER (ORDER BY unit_price DESC) AS price_quartile
FROM dim_products;
