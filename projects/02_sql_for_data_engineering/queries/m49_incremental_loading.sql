/*
================================================================================
MODULE 49: Incremental ETL Loading & MERGE / UPSERT Patterns
================================================================================
1. EXPLANATION:
Incremental loading processes only new/modified records since the last watermark timestamp.
*/

-- Simulated Upsert Pattern
INSERT INTO fact_sales (transaction_id, customer_key, product_key, sale_date, quantity, gross_amount, discount_amount, net_amount, status)
SELECT 
    stg.transaction_id,
    1 AS customer_key,
    3 AS product_key,
    stg.sale_date,
    stg.quantity,
    stg.amount,
    0.0,
    stg.amount,
    stg.status
FROM stg_sales_incremental stg
WHERE stg.transaction_id NOT IN (SELECT transaction_id FROM fact_sales);

SELECT * FROM fact_sales WHERE transaction_id = 'TXN1006';
