/*
================================================================================
MODULE 51: Duplicate Detection & Window De-duplication
================================================================================
1. EXPLANATION:
`ROW_NUMBER() OVER (PARTITION BY business_key ORDER BY updated_at DESC)` identifies duplicate records.
*/

WITH ranked_sales AS (
    SELECT 
        sales_id,
        transaction_id,
        ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY sales_id ASC) AS dup_rank
    FROM fact_sales
)
SELECT * FROM ranked_sales WHERE dup_rank > 1;
