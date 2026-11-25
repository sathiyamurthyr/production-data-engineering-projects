/*
================================================================================
MODULE 37: Indexes & B-Tree / Bitmap Index Optimization
================================================================================
1. EXPLANATION:
Indexes speed up read queries by creating auxiliary search structures on join/where keys.
*/

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales(sale_date);

SELECT * FROM fact_sales WHERE customer_key = 1;
